"""
DevPilot CLI.

Usage:
    devpilot review <path>          Run code review skill
    devpilot security <path>        Run security audit skill
    devpilot architecture <path>    Run architecture analysis skill
    devpilot full <path>            Run all three skills

Add --no-llm to skip the Claude-generated summary and just see raw findings
(useful if you don't have ANTHROPIC_API_KEY set).
Add --json to print raw JSON instead of a formatted report (for piping).
"""

from __future__ import annotations

import json
import sys

import click

from devpilot import core
from devpilot.validation import InvalidProjectPath


def _run_skill(skill_func, path, no_llm, as_json, title):
    """Shared error handling wrapper: validate path, run the skill, report clearly on failure."""
    try:
        result = skill_func(path, use_llm=not no_llm)
    except InvalidProjectPath as exc:
        click.secho(f"Error: {exc}", fg="red", err=True)
        sys.exit(1)
    _print_report(title, result, as_json)


def _print_report(title: str, result: dict, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
        return

    click.secho(f"\n{'=' * 60}", fg="cyan")
    click.secho(f" {title}", fg="cyan", bold=True)
    click.secho(f"{'=' * 60}", fg="cyan")

    findings = result.get("findings", result)
    warnings = findings.get("warnings") if isinstance(findings, dict) else None
    if warnings:
        click.secho(
            "\n⚠ DevPilot noticed something that may affect these results:",
            fg="yellow",
            bold=True,
        )
        for w in warnings:
            click.secho(f"  - {w}", fg="yellow")

    if "summary" in result:
        click.echo(result["summary"])
        click.secho("\n--- raw findings summary ---", dim=True)

    click.echo(json.dumps(findings, indent=2, default=str)[:4000])


@click.group()
def main():
    """DevPilot — AI developer assistant for code review, security, and architecture."""
    pass


@main.command()
@click.argument("path")
@click.option("--no-llm", is_flag=True, help="Skip AI summary, show raw findings only.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def review(path, no_llm, as_json):
    """Run the full-codebase code review skill."""
    _run_skill(core.run_code_review, path, no_llm, as_json, "CODE REVIEW")


@main.command()
@click.argument("path")
@click.option("--no-llm", is_flag=True, help="Skip AI summary, show raw findings only.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def security(path, no_llm, as_json):
    """Run the security auditing skill."""
    _run_skill(core.run_security_audit, path, no_llm, as_json, "SECURITY AUDIT")


@main.command()
@click.argument("path")
@click.option("--no-llm", is_flag=True, help="Skip AI summary, show raw findings only.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def architecture(path, no_llm, as_json):
    """Run the architecture analysis skill."""
    _run_skill(core.run_architecture_analysis, path, no_llm, as_json, "ARCHITECTURE ANALYSIS")


@main.command()
@click.argument("path")
@click.option("--no-llm", is_flag=True, help="Skip AI summary, show raw findings only.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def full(path, no_llm, as_json):
    """Run all three skills and print a combined report."""
    try:
        result = core.run_full_analysis(path, use_llm=not no_llm)
    except InvalidProjectPath as exc:
        click.secho(f"Error: {exc}", fg="red", err=True)
        sys.exit(1)
    if as_json:
        click.echo(json.dumps(result, indent=2, default=str))
        return
    for key, title in [
        ("code_review", "CODE REVIEW"),
        ("security_audit", "SECURITY AUDIT"),
        ("architecture_analysis", "ARCHITECTURE ANALYSIS"),
    ]:
        _print_report(title, result[key], as_json=False)


if __name__ == "__main__":
    main()
