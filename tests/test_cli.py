from __future__ import annotations

from click.testing import CliRunner

from devpilot.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "review" in result.output
    assert "security" in result.output


def test_cli_review_json_on_valid_project(vulnerable_project):
    runner = CliRunner()
    result = runner.invoke(main, ["review", str(vulnerable_project), "--no-llm", "--json"])
    assert result.exit_code == 0
    assert '"skill": "code_review"' in result.output


def test_cli_exits_nonzero_on_bad_path():
    runner = CliRunner()
    result = runner.invoke(main, ["security", "/no/such/path", "--no-llm"])
    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_cli_full_runs_all_three_skills(vulnerable_project):
    runner = CliRunner()
    result = runner.invoke(main, ["full", str(vulnerable_project), "--no-llm", "--json"])
    assert result.exit_code == 0
    assert "code_review" in result.output
    assert "security_audit" in result.output
    assert "architecture_analysis" in result.output


def test_cli_surfaces_nesting_warning_prominently_in_human_readable_mode(tmp_path):
    """Regression test: the human-readable (non --json) CLI output must call
    out architecture warnings (e.g. the double-nesting hint) up front, not
    just bury them inside the JSON dump where they're easy to miss."""
    outer = tmp_path / "outer"
    inner = outer / "outer"
    app = inner / "app"
    app.mkdir(parents=True)
    (app / "__init__.py").write_text("")
    (app / "core.py").write_text("def f():\n    return 1\n")
    (app / "consumer.py").write_text("from app import core\n\ndef g():\n    return core.f()\n")

    runner = CliRunner()
    result = runner.invoke(main, ["architecture", str(outer), "--no-llm"])
    assert result.exit_code == 0
    assert "DevPilot noticed something" in result.output
    assert "extra level of nesting" in result.output
