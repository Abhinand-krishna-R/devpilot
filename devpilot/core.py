"""
DevPilot core: the three "skills" shared by both the CLI and the MCP server.

Each skill runs static analysis first (fast, deterministic, free) and then
optionally asks Claude to turn the raw findings into a prioritized,
human-readable summary.
"""

from __future__ import annotations

from typing import Any

from devpilot.analyzers import architecture, code_review, security
from devpilot.utils import llm_summary
from devpilot.validation import validate_project_path


def run_code_review(project_path: str, use_llm: bool = True) -> dict[str, Any]:
    """Run the code review skill (complexity, maintainability, style) on project_path."""
    validate_project_path(project_path)
    findings = code_review.review(project_path)
    result: dict[str, Any] = {"skill": "code_review", "path": project_path, "findings": findings}
    if use_llm:
        result["summary"] = llm_summary.summarize("code_review", findings)
    return result


def run_security_audit(project_path: str, use_llm: bool = True) -> dict[str, Any]:
    """Run the security audit skill (Bandit) on project_path."""
    validate_project_path(project_path)
    findings = security.audit(project_path)
    result: dict[str, Any] = {"skill": "security_audit", "path": project_path, "findings": findings}
    if use_llm:
        result["summary"] = llm_summary.summarize("security_audit", findings)
    return result


def run_architecture_analysis(project_path: str, use_llm: bool = True) -> dict[str, Any]:
    """Run the architecture analysis skill (import graph, coupling) on project_path."""
    validate_project_path(project_path)
    findings = architecture.analyze(project_path)
    result: dict[str, Any] = {
        "skill": "architecture_analysis",
        "path": project_path,
        "findings": findings,
    }
    if use_llm:
        result["summary"] = llm_summary.summarize("architecture_analysis", findings)
    return result


def run_full_analysis(project_path: str, use_llm: bool = True) -> dict[str, Any]:
    """Run all three skills and return a combined report."""
    return {
        "path": project_path,
        "code_review": run_code_review(project_path, use_llm),
        "security_audit": run_security_audit(project_path, use_llm),
        "architecture_analysis": run_architecture_analysis(project_path, use_llm),
    }
