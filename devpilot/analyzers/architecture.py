"""
Architecture analyzer.

Builds a lightweight picture of a Python project's structure: module/file
inventory, an import dependency graph resolved to precise dotted module
paths (not just top-level package names), module coupling (fan-in/fan-out),
and circular-import detection.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
from typing import Any

IGNORED_DIRS = {"venv", ".venv", "node_modules", ".git", "build", "dist", "__pycache__"}


def _iter_python_files(project_path: str):
    root = Path(project_path).resolve()
    for path in root.rglob("*.py"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        yield path


def _module_name(file_path: Path, root: Path) -> str:
    rel = file_path.relative_to(root).with_suffix("")
    parts = [p for p in rel.parts if p != "__init__"]
    return ".".join(parts) if parts else file_path.stem


def _extract_imports(tree: ast.AST) -> list[str]:
    """Extract full dotted import paths (not just the top-level package name).

    'import pkg.b' -> 'pkg.b'.
    'from pkg.utils import x' -> both 'pkg.utils' and 'pkg.utils.x', since x
    might be a submodule ('from pkg.models import order' where order.py is a
    real file) or just a name inside pkg/utils/__init__.py — _resolve_import
    tries the more specific one first and falls back to the package itself.
    """
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
                for alias in node.names:
                    imports.append(f"{node.module}.{alias.name}")
    return imports


def _resolve_import(imp: str, local_modules: set[str]) -> str | None:
    """Resolve an imported dotted path to the most specific matching local module.

    Tries the full path first, then progressively shorter prefixes, so
    'pkg.utils.helpers' matches a local module 'pkg.utils' even if
    'pkg.utils.helpers' itself isn't one of the project's files. Returns
    None if no prefix of the import matches any local module (i.e. it's
    an external dependency).
    """
    parts = imp.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in local_modules:
            return candidate
    return None


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Detect simple cycles via DFS. Good enough for a project-scale report."""
    cycles = []
    visited = set()

    def dfs(node: str, path: list[str], on_path: set[str]) -> None:
        """DFS that records a cycle whenever it revisits a node already on the current path."""
        if node in on_path:
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            if len(cycle) > 2 and cycle not in cycles:
                cycles.append(cycle)
            return
        if node in visited:
            return
        visited.add(node)
        on_path.add(node)
        path.append(node)
        for neighbor in graph.get(node, ()):
            dfs(neighbor, path, on_path)
        path.pop()
        on_path.discard(node)

    for start_node in list(graph):
        dfs(start_node, [], set())

    return cycles[:10]


def _find_nested_root_hints(external_deps: set[str], local_modules: set[str]) -> list[str]:
    """Detect the "pointed at the wrong directory level" failure mode.

    If an import's top-level name (e.g. 'app') never resolves to a local
    module, but that same name DOES appear as a non-leading segment of some
    local module's dotted path (e.g. a file lives at 'sample_test_project.
    app.services.pricing'), that's a strong signal the project has an extra
    level of nesting than the imports expect — commonly caused by extracting
    a zip into a folder with the same name as the zip, doubling the nesting.
    Silently mis-bucketing those imports as "external dependencies" (which is
    what happens without this check) produces a plausible-looking but wrong
    architecture report with no error at all, which is worse than crashing.
    """
    local_top_level = {m.split(".")[0] for m in local_modules}
    segment_owners: dict[str, set[str]] = defaultdict(set)
    for mod in local_modules:
        for part in mod.split(".")[1:]:
            segment_owners[part].add(mod)

    warnings = []
    for name in sorted(external_deps):
        if name in local_top_level:
            continue
        owners = segment_owners.get(name)
        if owners:
            example = sorted(owners)[0]
            warnings.append(
                f"Import '{name}' didn't match any local module, but '{name}' appears "
                f"as a nested folder inside this project (e.g. in module '{example}'). "
                "This usually means DevPilot was pointed at a parent directory with an "
                "extra level of nesting — a common result of extracting a zip into a "
                "folder with the same name as the zip. Try running DevPilot against "
                "the inner folder instead, and re-check the results."
            )
    return warnings


def analyze(project_path: str) -> dict[str, Any]:
    """Build a structural overview of the project."""
    root = Path(project_path).resolve()
    files = list(_iter_python_files(project_path))

    if not files:
        return {"error": "No Python files found", "files_analyzed": 0}

    local_modules = {_module_name(f, root) for f in files}

    import_graph: dict[str, set[str]] = defaultdict(set)
    external_deps: set[str] = set()
    file_sizes = []

    for file_path in files:
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            continue

        mod_name = _module_name(file_path, root)
        file_sizes.append(
            {"file": str(file_path), "module": mod_name, "lines": source.count("\n") + 1}
        )

        for imp in _extract_imports(tree):
            if imp == "__future__":
                continue
            resolved = _resolve_import(imp, local_modules)
            if resolved is not None:
                if resolved != mod_name:  # ignore a module "importing itself" via __init__ quirks
                    import_graph[mod_name].add(resolved)
            else:
                external_deps.add(imp.split(".")[0])

    # Fan-out = how many local modules this module depends on.
    # Fan-in = how many local modules depend on this module.
    fan_out = {m: len(deps) for m, deps in import_graph.items()}
    fan_in: dict[str, int] = defaultdict(int)
    for deps in import_graph.values():
        for d in deps:
            fan_in[d] += 1

    most_depended_on = sorted(fan_in.items(), key=lambda x: x[1], reverse=True)[:10]
    most_coupled = sorted(fan_out.items(), key=lambda x: x[1], reverse=True)[:10]
    cycles = _find_cycles(import_graph)
    largest_files = sorted(file_sizes, key=lambda f: f["lines"], reverse=True)[:10]
    warnings = _find_nested_root_hints(external_deps, local_modules)

    return {
        "files_analyzed": len(files),
        "total_modules": len(local_modules),
        "external_dependencies": sorted(external_deps),
        "external_dependency_count": len(external_deps),
        "most_depended_on_modules": most_depended_on,
        "most_coupled_modules": most_coupled,
        "circular_imports": cycles,
        "largest_files": largest_files,
        "warnings": warnings,
    }
