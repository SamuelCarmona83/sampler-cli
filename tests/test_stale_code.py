from pathlib import Path

import pytest

from sampler.db import Database
from sampler.indexer.builder import IndexBuilder
from sampler.query.engine import QueryEngine


def test_stale_code_detects_test_only_called_function(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    (project_dir / "app.py").write_text(
        """
def stale_target(x):
    return x


def active_target(y):
    return y


def normal_caller(z):
    return active_target(z)
""",
        encoding="utf-8",
    )

    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text(
        """
from app import stale_target, active_target


def test_stale_target():
    assert stale_target(1) == 1


def test_active_target():
    assert active_target(2) == 2
""",
        encoding="utf-8",
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()
    builder = IndexBuilder(db=db)
    builder.index_project(project_name="demo", project_path=str(project_dir), language="python")

    engine = QueryEngine(db=db)
    stale = engine.stale_code_candidates("demo")

    names = {row["qualified_name"] or row["name"] for row in stale}
    assert "stale_target" in names
    assert "active_target" not in names


def test_stale_code_ignores_test_file_helpers(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_integration.py").write_text(
        """
class TestIntegration:
    def _create_instance(self):
        return 1

    def test_flow(self):
        assert self._create_instance() == 1
""",
        encoding="utf-8",
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()
    builder = IndexBuilder(db=db)
    builder.index_project(project_name="demo", project_path=str(project_dir), language="python")

    engine = QueryEngine(db=db)
    stale = engine.stale_code_candidates("demo")

    names = {row["qualified_name"] or row["name"] for row in stale}
    assert "_create_instance" not in names
    assert "TestIntegration._create_instance" not in names


def test_stale_code_empty_when_no_edges(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "app.py").write_text(
        """
def lonely_function(a):
    return a
""",
        encoding="utf-8",
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()
    builder = IndexBuilder(db=db)
    builder.index_project(project_name="demo", project_path=str(project_dir), language="python")

    engine = QueryEngine(db=db)
    assert engine.stale_code_candidates("demo") == []


def test_is_test_path_supports_multilanguage_patterns() -> None:
    assert QueryEngine._is_test_path("tests/test_app.py")
    assert QueryEngine._is_test_path("pkg/handler_test.go")
    assert QueryEngine._is_test_path("web/Button.test.tsx")
    assert QueryEngine._is_test_path("web/Button.spec.ts")
    assert QueryEngine._is_test_path("src/__tests__/helpers.js")
    assert QueryEngine._is_test_path("src/spec/api.test.mjs")
    assert not QueryEngine._is_test_path("src/app/main.go")
    assert not QueryEngine._is_test_path("src/components/Button.tsx")


def test_stale_code_ignores_go_test_file_helpers(tmp_path: Path) -> None:
    pytest.importorskip("tree_sitter_go")

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "main_test.go").write_text(
        """
package main

func createClient() int {
    return 1
}

func TestFlow() int {
    return createClient()
}
""",
        encoding="utf-8",
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()
    builder = IndexBuilder(db=db)
    builder.index_project(project_name="demo", project_path=str(project_dir), language="go")

    engine = QueryEngine(db=db)
    stale = engine.stale_code_candidates("demo")

    names = {row["qualified_name"] or row["name"] for row in stale}
    assert "createClient" not in names


def test_stale_code_ignores_typescript_test_file_helpers(tmp_path: Path) -> None:
    pytest.importorskip("tree_sitter_typescript")

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "button.test.ts").write_text(
        """
function createHarness() {
    return 1
}

function testFlow() {
    return createHarness()
}
""",
        encoding="utf-8",
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()
    builder = IndexBuilder(db=db)
    builder.index_project(project_name="demo", project_path=str(project_dir), language="typescript")

    engine = QueryEngine(db=db)
    stale = engine.stale_code_candidates("demo")

    names = {row["qualified_name"] or row["name"] for row in stale}
    assert "createHarness" not in names
