"""
LLM summarization layer.

Static analyzers (bandit, radon, AST checks) produce raw, noisy data.
This module sends that data to Claude to produce a short, prioritized,
human-readable set of recommendations. Requires ANTHROPIC_API_KEY to be set.
"""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a senior staff engineer performing a code review \
based on static analysis output (not raw source code). You will be given \
JSON findings from one of: a security scan (bandit), a code quality scan \
(radon complexity/maintainability + style checks), or an architecture scan \
(import graph, coupling, circular imports).

Write a concise, prioritized summary for a developer. Rules:
- Group findings by severity/impact, worst first.
- Be specific: cite file names and line numbers from the data given.
- Do not invent issues that aren't in the data.
- Give concrete, actionable fixes, not generic advice.
- Keep it under 400 words.
- End with a short "Top 3 priorities" list.
"""


def _get_client() -> anthropic.Anthropic | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def summarize(analysis_type: str, findings: dict[str, Any]) -> str:
    """Send findings to Claude and return a prioritized natural-language summary.

    Falls back to a note explaining how to enable this if no API key is set,
    so the rest of DevPilot still works without it.
    """
    client = _get_client()
    if client is None:
        return (
            "[LLM summary skipped: set the ANTHROPIC_API_KEY environment variable "
            "to enable AI-generated recommendations. Raw findings are shown above.]"
        )

    payload = json.dumps(findings, indent=2, default=str)
    # Guard against oversized payloads blowing the context window.
    if len(payload) > 60_000:
        payload = payload[:60_000] + "\n... [truncated]"

    message = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (f"Analysis type: {analysis_type}\n\n" f"Findings JSON:\n{payload}"),
            }
        ],
    )

    return "".join(block.text for block in message.content if block.type == "text")
