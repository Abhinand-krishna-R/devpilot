"""Tests for the MCP server layer: tool registration and error handling."""

from __future__ import annotations

import asyncio
import json

from devpilot.mcp_server import mcp


def test_all_four_tools_are_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {"review_code", "security_audit", "architecture_analysis", "full_analysis"}


def test_bad_path_returns_structured_error_not_a_crash():
    """Regression test: calling a tool with a nonexistent path must return a
    parseable {"error": ...} result, not raise an UnexpectedToolError with a
    raw Python traceback (see mcp_server._safe_run)."""
    result = asyncio.run(
        mcp.call_tool(
            "review_code", {"project_path": "/definitely/not/a/real/path", "use_llm": False}
        )
    )
    assert result.is_error is False  # the *tool call* succeeded; the failure is in the payload
    payload = json.loads(result.content[0].text)
    assert "error" in payload
    assert "does not exist" in payload["error"]


def test_valid_path_returns_findings_no_llm(vulnerable_project):
    result = asyncio.run(
        mcp.call_tool("security_audit", {"project_path": str(vulnerable_project), "use_llm": False})
    )
    payload = json.loads(result.content[0].text)
    assert payload["skill"] == "security_audit"
    assert payload["findings"]["total_issues"] >= 1


def test_full_analysis_tool_runs_all_three(clean_project):
    result = asyncio.run(
        mcp.call_tool("full_analysis", {"project_path": str(clean_project), "use_llm": False})
    )
    payload = json.loads(result.content[0].text)
    assert set(payload.keys()) >= {"code_review", "security_audit", "architecture_analysis"}
