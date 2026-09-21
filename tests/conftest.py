"""Shared pytest fixtures for DevPilot tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    """A directory that exists but has no Python files in it."""
    (tmp_path / "readme.txt").write_text("not python")
    return tmp_path


@pytest.fixture
def clean_project(tmp_path: Path) -> Path:
    """A small, well-formed project with no issues an analyzer should flag."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "math_utils.py").write_text(
        '''"""Simple, well-documented math helpers."""


def add(a: int, b: int) -> int:
    """Return the sum of a and b."""
    return a + b


def multiply(a: int, b: int) -> int:
    """Return the product of a and b."""
    return a * b
'''
    )
    return tmp_path


@pytest.fixture
def vulnerable_project(tmp_path: Path) -> Path:
    """A project with a known, deliberate set of issues for each analyzer to catch."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "utils.py").write_text(
        """import os
import subprocess

PASSWORD = "hardcoded_secret_123"


def run_command(user_input):
    os.system("echo " + user_input)
    subprocess.call(user_input, shell=True)


def complex_function(a, b, c, d, e, f, g, h):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            if g:
                                if h:
                                    return 1
                                return 2
                            return 3
                        return 4
                    return 5
                return 6
            return 7
        return 8
    return 9
"""
    )
    (pkg / "models.py").write_text(
        "from pkg.utils import run_command\n\n\n"
        "class UserModel:\n"
        "    def process(self, data):\n"
        "        return run_command(data)\n"
    )
    return tmp_path


@pytest.fixture
def syntax_error_project(tmp_path: Path) -> Path:
    """A project containing one file with invalid Python syntax."""
    (tmp_path / "broken.py").write_text("def broken(:\n    pass\n")
    (tmp_path / "fine.py").write_text(
        '"""Fine module."""\n\n\ndef ok():\n    """Do nothing."""\n    return None\n'
    )
    return tmp_path
