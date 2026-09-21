from __future__ import annotations

from devpilot.analyzers import code_review


def test_no_python_files_returns_error(empty_project):
    result = code_review.review(str(empty_project))
    assert result["error"] == "No Python files found"
    assert result["files_analyzed"] == 0


def test_clean_project_has_no_style_issues(clean_project):
    result = code_review.review(str(clean_project))
    assert result["files_analyzed"] == 2  # __init__.py + math_utils.py
    assert result["style_issue_count"] == 0
    assert result["files_skipped"] == 0


def test_flags_long_deeply_nested_function_and_missing_docstrings(vulnerable_project):
    result = code_review.review(str(vulnerable_project))

    complex_names = {c["name"] for c in result["top_complex_functions"]}
    assert "complex_function" in complex_names

    style_types = {s["type"] for s in result["style_issues"]}
    assert "too_many_arguments" in style_types
    assert "missing_docstring" in style_types


def test_syntax_error_file_is_skipped_not_crashed(syntax_error_project):
    result = code_review.review(str(syntax_error_project))
    # Should not raise, and the broken file should be recorded as skipped
    # while the valid file is still analyzed.
    assert result["files_analyzed"] == 2
    assert result["files_skipped"] == 1
    assert any("broken.py" in s["file"] for s in result["skipped_files"])
