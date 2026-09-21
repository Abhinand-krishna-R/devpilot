"""
Code review analyzer.

Uses Radon for cyclomatic complexity and maintainability index, plus a few
lightweight AST-based checks (long functions, too many arguments, missing
docstrings) to build a structured "code review" data set.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from radon.complexity import cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze as radon_raw_analyze

IGNORED_DIRS = {"venv", ".venv", "node_modules", ".git", "build", "dist", "__pycache__"}

# Complexity grade thresholds (radon convention: A best, F worst)
COMPLEXITY_GRADES = [
    (5, "A"),
    (10, "B"),
    (20, "C"),
    (30, "D"),
    (40, "E"),
    (float("inf"), "F"),
]


def _grade(score: float) -> str:
    for threshold, grade in COMPLEXITY_GRADES:
        if score <= threshold:
            return grade
    return "F"


def _iter_python_files(project_path: str):
    root = Path(project_path).resolve()
    for path in root.rglob("*.py"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        yield path


def _check_function_length_and_args(tree: ast.AST, file_path: str) -> list[dict[str, Any]]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            start = node.lineno
            end = max(
                (getattr(child, "lineno", start) for child in ast.walk(node)),
                default=start,
            )
            length = end - start + 1
            n_args = len(node.args.args)
            has_docstring = ast.get_docstring(node) is not None

            if length > 60:
                issues.append(
                    {
                        "file": file_path,
                        "line": start,
                        "type": "long_function",
                        "detail": (
                            f"Function '{node.name}' is {length} lines long "
                            "(consider splitting)."
                        ),
                    }
                )
            if n_args > 6:
                issues.append(
                    {
                        "file": file_path,
                        "line": start,
                        "type": "too_many_arguments",
                        "detail": (
                            f"Function '{node.name}' takes {n_args} arguments "
                            "(consider a config object)."
                        ),
                    }
                )
            if not has_docstring and not node.name.startswith("_"):
                issues.append(
                    {
                        "file": file_path,
                        "line": start,
                        "type": "missing_docstring",
                        "detail": f"Public function '{node.name}' has no docstring.",
                    }
                )
    return issues


def _analyze_single_file(file_path: Path) -> dict[str, Any] | None:
    """Run all per-file checks on one file. Returns None if the file can't be read."""
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return {"skipped": True, "file": str(file_path), "reason": f"read error: {exc}"}

    rel_path = str(file_path)
    result: dict[str, Any] = {
        "skipped": False,
        "file": rel_path,
        "complexity": [],
        "maintainability": None,
        "raw": None,
        "style": [],
    }

    try:
        for block in cc_visit(source):
            result["complexity"].append(
                {
                    "file": rel_path,
                    "line": block.lineno,
                    "name": block.name,
                    "complexity": block.complexity,
                    "grade": _grade(block.complexity),
                }
            )
    except SyntaxError as exc:
        return {"skipped": True, "file": rel_path, "reason": f"syntax error: {exc}"}

    try:
        mi_score = round(mi_visit(source, multi=True), 1)
        result["maintainability"] = {"file": rel_path, "score": mi_score}
    except (SyntaxError, ValueError) as exc:
        # Radon's MI calculation can fail on unusual files (e.g. all-comment
        # files); this is non-fatal, just means no MI score for this file.
        result["maintainability_error"] = str(exc)

    try:
        raw = radon_raw_analyze(source)
        result["raw"] = {
            "loc": raw.loc,
            "sloc": raw.sloc,
            "comments": raw.comments,
            "blank": raw.blank,
        }
    except (SyntaxError, ValueError) as exc:
        result["raw_error"] = str(exc)

    try:
        tree = ast.parse(source)
        result["style"] = _check_function_length_and_args(tree, rel_path)
    except SyntaxError as exc:
        result["skipped"] = True
        result["reason"] = f"syntax error during style check: {exc}"

    return result


def review(project_path: str) -> dict[str, Any]:
    """Run the full code review pass over a project directory.

    Returns a dict with aggregated complexity, maintainability, raw line
    stats, and style findings across every Python file found. Files that
    can't be read or parsed are recorded under "skipped_files" rather than
    silently dropped.
    """
    files = list(_iter_python_files(project_path))

    if not files:
        return {"error": "No Python files found", "files_analyzed": 0}

    complexity_findings = []
    style_findings = []
    raw_stats = {"loc": 0, "sloc": 0, "comments": 0, "blank": 0}
    mi_scores = []
    skipped_files = []

    for file_path in files:
        file_result = _analyze_single_file(file_path)
        if file_result is None:
            continue
        if file_result["skipped"]:
            skipped_files.append({"file": file_result["file"], "reason": file_result["reason"]})
            continue

        complexity_findings.extend(file_result["complexity"])
        style_findings.extend(file_result["style"])
        if file_result["maintainability"]:
            mi_scores.append(file_result["maintainability"])
        if file_result["raw"]:
            for key in raw_stats:
                raw_stats[key] += file_result["raw"][key]

    complexity_findings.sort(key=lambda f: f["complexity"], reverse=True)
    mi_scores.sort(key=lambda m: m["score"])

    return {
        "files_analyzed": len(files),
        "files_skipped": len(skipped_files),
        "skipped_files": skipped_files[:10],
        "raw_stats": raw_stats,
        "top_complex_functions": complexity_findings[:20],
        "lowest_maintainability_files": mi_scores[:10],
        "style_issues": style_findings[:40],
        "style_issue_count": len(style_findings),
    }
