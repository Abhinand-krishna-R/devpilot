from __future__ import annotations

from devpilot.analyzers import architecture


def test_no_python_files_returns_error(empty_project):
    result = architecture.analyze(str(empty_project))
    assert result["error"] == "No Python files found"


def test_clean_project_structure(clean_project):
    result = architecture.analyze(str(clean_project))
    assert result["files_analyzed"] == 2
    assert result["circular_imports"] == []


def test_detects_local_dependency_and_external_deps(vulnerable_project):
    result = architecture.analyze(str(vulnerable_project))
    assert "os" in result["external_dependencies"]
    assert "subprocess" in result["external_dependencies"]
    # models.py imports from pkg.utils, so pkg.models should be coupled to something.
    coupled_modules = {name for name, _ in result["most_coupled_modules"]}
    assert "pkg.models" in coupled_modules


def test_no_circular_imports_in_simple_project(vulnerable_project):
    result = architecture.analyze(str(vulnerable_project))
    assert result["circular_imports"] == []


def test_detects_circular_import(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text("import pkg.b\n")
    (pkg / "b.py").write_text("import pkg.a\n")

    result = architecture.analyze(str(tmp_path))
    assert len(result["circular_imports"]) >= 1


def test_detects_circular_import_via_from_import_submodule(tmp_path):
    """Regression test: 'from pkg import submodule' must resolve to the
    submodule itself (pkg.submodule), not just the parent package (pkg).
    Before this was fixed, 'from app.models import order' only recorded a
    dependency on 'app.models' (the package), so a genuine cycle between
    two submodules imported this way was invisible to cycle detection."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "user.py").write_text("from pkg import order\n\ndef f():\n    return order.g()\n")
    (pkg / "order.py").write_text("from pkg import user\n\ndef g():\n    return user.f\n")

    result = architecture.analyze(str(tmp_path))
    flat_cycles = {name for cycle in result["circular_imports"] for name in cycle}
    assert "pkg.user" in flat_cycles
    assert "pkg.order" in flat_cycles


def test_from_import_of_submodule_resolves_to_submodule_not_just_package(tmp_path):
    """'from pkg.models import order' should create a dependency edge on
    'pkg.models.order' specifically, not only on 'pkg.models'."""
    pkg = tmp_path / "pkg" / "models"
    pkg.mkdir(parents=True)
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "order.py").write_text("def g():\n    return 1\n")
    (pkg / "user.py").write_text("from pkg.models import order\n\ndef f():\n    return order.g()\n")

    result = architecture.analyze(str(tmp_path))
    coupled = dict(result["most_coupled_modules"])
    depended_on = {name for name, _ in result["most_depended_on_modules"]}
    assert coupled.get("pkg.models.user", 0) >= 1
    assert "pkg.models.order" in depended_on


def test_no_nesting_warning_for_correctly_structured_project(vulnerable_project):
    """A normally-structured project (imports match the actual directory
    layout) should produce zero warnings — this guards against false
    positives from the nested-root heuristic below."""
    result = architecture.analyze(str(vulnerable_project))
    assert result["warnings"] == []


def test_warns_when_project_has_extra_level_of_nesting(tmp_path):
    """Regression test for a real-world failure mode: extracting a zip into
    a folder with the same name as the zip doubles the nesting (e.g.
    'sample_test_project/sample_test_project/app/...'). Before this check,
    DevPilot would silently mis-bucket every 'app.*' import as an external
    dependency called 'app' and report zero coupling/cycles with no error
    at all — a wrong-but-plausible-looking result. Now it should surface a
    warning naming the mismatched import."""
    # Simulate double nesting: outer/outer/app/... instead of outer/app/...
    outer = tmp_path / "outer"
    inner = outer / "outer"
    app = inner / "app"
    app.mkdir(parents=True)
    (app / "__init__.py").write_text("")
    (app / "core.py").write_text("def f():\n    return 1\n")
    (app / "consumer.py").write_text("from app import core\n\ndef g():\n    return core.f()\n")

    # Analyze from the OUTER outer/ directory -> wrong root, extra nesting.
    result = architecture.analyze(str(outer))
    assert "app" in result["external_dependencies"]
    assert len(result["warnings"]) == 1
    assert "app" in result["warnings"][0]
    assert "extra level of nesting" in result["warnings"][0]

    # Analyzing from the correct inner root should be clean.
    correct_result = architecture.analyze(str(inner))
    assert correct_result["warnings"] == []
    assert "app" not in correct_result["external_dependencies"]
