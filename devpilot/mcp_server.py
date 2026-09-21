"""
DevPilot MCP server.

Exposes three tools over the Model Context Protocol so that Claude Desktop,
Claude Code, or any other MCP client can invoke them directly:

    - review_code(project_path)
    - security_audit(project_path)
    - architecture_analysis(project_path)
    - full_analysis(project_path)

Run directly for local stdio use (e.g. from a Claude Desktop config):
    python -m devpilot.mcp_server

Requires ANTHROPIC_API_KEY in the environment for the AI-generated summary;
without it, tools still return raw static-analysis findings.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from devpilot import core
from devpilot.validation import InvalidProjectPath

mcp = MCPServer(
    name="devpilot",
    title="DevPilot",
    description=(
        "AI developer assistant: full-codebase code review, security auditing, "
        "and architecture analysis via reusable skills."
    ),
)


def _safe_run(skill_func, project_path: str, use_llm: bool) -> dict:
    """Run a skill and convert any failure into a structured error dict.

    Without this, an invalid path raises inside the tool call and the MCP
    framework surfaces it as an opaque UnexpectedToolError with a full Python
    traceback — not something a calling model or client can act on. Returning
    {"error": ...} instead means a bad path is just a normal, parseable result.
    """
    try:
        return skill_func(project_path, use_llm=use_llm)
    except InvalidProjectPath as exc:
        return {"error": str(exc)}
    except Exception as exc:  # last resort: never let a raw traceback leak to the client
        return {"error": f"Unexpected error running analysis: {exc}"}


@mcp.tool(
    description="Run a full-codebase code review: complexity, maintainability, and style issues."
)
def review_code(project_path: str, use_llm: bool = True) -> dict:
    """
    Args:
        project_path: Absolute or relative path to the project directory to review.
        use_llm: Whether to include an AI-generated prioritized summary (default True).
    """
    return _safe_run(core.run_code_review, project_path, use_llm)


@mcp.tool(description="Run a security audit on a project using static analysis (Bandit).")
def security_audit(project_path: str, use_llm: bool = True) -> dict:
    """
    Args:
        project_path: Absolute or relative path to the project directory to scan.
        use_llm: Whether to include an AI-generated prioritized summary (default True).
    """
    return _safe_run(core.run_security_audit, project_path, use_llm)


@mcp.tool(
    description="Analyze a project's architecture: module coupling, dependencies, circular imports."
)
def architecture_analysis(project_path: str, use_llm: bool = True) -> dict:
    """
    Args:
        project_path: Absolute or relative path to the project directory to analyze.
        use_llm: Whether to include an AI-generated prioritized summary (default True).
    """
    return _safe_run(core.run_architecture_analysis, project_path, use_llm)


@mcp.tool(description="Run code review, security audit, and architecture analysis together.")
def full_analysis(project_path: str, use_llm: bool = True) -> dict:
    """
    Args:
        project_path: Absolute or relative path to the project directory to analyze.
        use_llm: Whether to include AI-generated prioritized summaries (default True).
    """
    return _safe_run(core.run_full_analysis, project_path, use_llm)


def main() -> None:
    """Entry point for `python -m devpilot.mcp_server`: runs the server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
