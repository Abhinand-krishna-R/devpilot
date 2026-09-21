from __future__ import annotations

import pytest

from devpilot import core
from devpilot.validation import InvalidProjectPath, validate_project_path


def test_validate_project_path_rejects_nonexistent():
    with pytest.raises(InvalidProjectPath, match="does not exist"):
        validate_project_path("/definitely/not/a/real/path")


def test_validate_project_path_rejects_file(vulnerable_project):
    file_path = vulnerable_project / "pkg" / "utils.py"
    with pytest.raises(InvalidProjectPath, match="not a directory"):
        validate_project_path(str(file_path))


def test_validate_project_path_accepts_directory(clean_project):
    result = validate_project_path(str(clean_project))
    assert result.is_dir()


def test_run_code_review_raises_on_bad_path():
    with pytest.raises(InvalidProjectPath):
        core.run_code_review("/nope", use_llm=False)


def test_run_full_analysis_no_llm_returns_all_three_skills(vulnerable_project):
    result = core.run_full_analysis(str(vulnerable_project), use_llm=False)
    assert set(result.keys()) == {"path", "code_review", "security_audit", "architecture_analysis"}
    for skill_key in ("code_review", "security_audit", "architecture_analysis"):
        assert "summary" not in result[skill_key]  # use_llm=False means no summary key at all
        assert "findings" in result[skill_key]
