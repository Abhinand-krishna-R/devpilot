"""
Security auditing analyzer.

Runs Bandit (static security analysis for Python) across a project directory
and returns a normalized list of findings that the rest of DevPilot can use.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 -- used only to invoke bandit itself with fixed args, no shell
import sys
from pathlib import Path
from typing import Any


def run_bandit(project_path: str) -> dict[str, Any]:
    """Run bandit recursively over project_path and return parsed JSON results.

    Falls back to a structured error dict if bandit fails to run (e.g. no
    Python files found, or bandit itself errors out).
    """
    path = Path(project_path).resolve()
    if not path.exists():
        return {"error": f"Path does not exist: {project_path}", "results": []}

    cmd = [
        sys.executable,
        "-m",
        "bandit",
        "-r",
        str(path),
        "-f",
        "json",
        # Skip common noisy/irrelevant directories.
        "-x",
        ",".join(
            [
                "*/venv/*",
                "*/.venv/*",
                "*/node_modules/*",
                "*/.git/*",
                "*/build/*",
                "*/dist/*",
                "*/__pycache__/*",
            ]
        ),
    ]

    try:
        proc = subprocess.run(  # nosec B603 -- fixed args, no shell, project_path is a directory the caller already trusted enough to run analysis on
            cmd, capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        return {
            "error": "Bandit scan timed out after 120s (project may be very large)",
            "results": [],
        }
    except OSError as exc:
        return {"error": f"Could not run bandit: {exc}", "results": []}

    # Bandit exits non-zero when it finds issues, so don't treat that as failure.
    stdout = proc.stdout.strip()
    if not stdout:
        return {"error": proc.stderr.strip() or "No output from bandit", "results": []}

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {"error": "Could not parse bandit output", "results": []}

    return data


SEVERITY_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNDEFINED": 0}


def summarize_security(bandit_output: dict[str, Any]) -> dict[str, Any]:
    """Turn raw bandit JSON into a compact, LLM- and human-friendly summary."""
    if "error" in bandit_output and not bandit_output.get("results"):
        return {
            "total_issues": 0,
            "by_severity": {},
            "top_findings": [],
            "error": bandit_output["error"],
        }

    results = bandit_output.get("results", [])

    by_severity: dict[str, int] = {}
    findings = []
    for r in results:
        sev = r.get("issue_severity", "UNDEFINED")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        findings.append(
            {
                "file": r.get("filename"),
                "line": r.get("line_number"),
                "severity": sev,
                "confidence": r.get("issue_confidence"),
                "test_id": r.get("test_id"),
                "issue": r.get("issue_text"),
                "code": r.get("code", "").strip(),
            }
        )

    # Sort worst-first for the top findings shown in reports.
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f["severity"], 0), reverse=True)

    return {
        "total_issues": len(results),
        "by_severity": by_severity,
        "top_findings": findings[:25],
        "all_findings": findings,
    }


def audit(project_path: str) -> dict[str, Any]:
    """Public entry point: run bandit and return a summarized result."""
    raw = run_bandit(project_path)
    return summarize_security(raw)
