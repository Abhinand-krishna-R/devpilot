from __future__ import annotations

from devpilot.analyzers import security


def test_no_python_files_returns_zero_issues(empty_project):
    result = security.audit(str(empty_project))
    assert result["total_issues"] == 0
    assert result["top_findings"] == []


def test_clean_project_has_no_high_severity_issues(clean_project):
    result = security.audit(str(clean_project))
    assert result["by_severity"].get("HIGH", 0) == 0


def test_detects_shell_injection_and_hardcoded_secret(vulnerable_project):
    result = security.audit(str(vulnerable_project))
    assert result["total_issues"] >= 3

    test_ids = {f["test_id"] for f in result["all_findings"]}
    # B602/B605: shell=True / os.system injection risk. B105: hardcoded password.
    assert "B602" in test_ids or "B605" in test_ids
    assert "B105" in test_ids

    assert result["by_severity"].get("HIGH", 0) >= 1


def test_nonexistent_path_reports_error():
    result = security.audit("/path/does/not/exist/at/all")
    assert result["total_issues"] == 0
    assert "error" in result
