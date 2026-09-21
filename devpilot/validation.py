"""Small shared helpers used by both the CLI and the MCP server."""

from __future__ import annotations

from pathlib import Path


class InvalidProjectPath(ValueError):
    """Raised when a project path doesn't exist or isn't a directory."""


def validate_project_path(project_path: str) -> Path:
    """Resolve and validate a project path, raising a clear error if it's unusable.

    Centralizing this means every skill (and every entry point calling into
    them) gives the same clear error instead of each analyzer failing in a
    slightly different way partway through its own logic.
    """
    path = Path(project_path).expanduser().resolve()
    if not path.exists():
        raise InvalidProjectPath(f"Path does not exist: {project_path}")
    if not path.is_dir():
        raise InvalidProjectPath(f"Path is not a directory: {project_path}")
    return path
