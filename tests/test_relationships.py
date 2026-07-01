from pathlib import Path

from sampler.db import Database
from sampler.indexer.builder import IndexBuilder
from sampler.query.engine import QueryEngine


def _index_demo_project(tmp_path: Path) -> tuple[Database, QueryEngine]:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "app.py").write_text(
        """
def add(a, b):
    return a + b


def run(value):
    return add(value, 2)


class Calculator:
    def total(self, a, b):
        return add(a, b)
""",
        encoding="utf-8",
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()

    builder = IndexBuilder(db=db)
    builder.index_project(project_name="demo", project_path=str(project_dir), language="python")

    return db, QueryEngine(db=db)


def test_callers_returns_functions_that_call_target(tmp_path: Path) -> None:
    _, engine = _index_demo_project(tmp_path)

    matches, callers = engine.callers("add", project_name="demo")

    assert len(matches) == 1
    caller_names = {row["qualified_name"] or row["name"] for row in callers}
    assert "run" in caller_names
    assert "Calculator.total" in caller_names


def test_usages_returns_any_relationship_type(tmp_path: Path) -> None:
    _, engine = _index_demo_project(tmp_path)

    matches, usages = engine.usages("add", project_name="demo")

    assert len(matches) == 1
    assert len(usages) >= 2
    assert all(row["relation_type"] == "CALLS" for row in usages)


def test_related_returns_contains_relationships(tmp_path: Path) -> None:
    _, engine = _index_demo_project(tmp_path)

    matches, related = engine.related("Calculator", project_name="demo")

    assert len(matches) == 1
    assert any(row["relation"] == "child" and (row["qualified_name"] or row["name"]) == "Calculator.total" for row in related)


def test_resolve_symbol_reports_ambiguity(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "a.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    (project_dir / "b.py").write_text("def helper():\n    return 2\n", encoding="utf-8")

    db = Database(tmp_path / "graph.db")
    db.init_schema()
    builder = IndexBuilder(db=db)
    builder.index_project(project_name="demo", project_path=str(project_dir), language="python")

    engine = QueryEngine(db=db)
    matches, callers = engine.callers("helper", project_name="demo")

    assert len(matches) == 2
    assert callers == []


def test_callers_no_match_returns_empty(tmp_path: Path) -> None:
    _, engine = _index_demo_project(tmp_path)

    matches, callers = engine.callers("does_not_exist", project_name="demo")

    assert matches == []
    assert callers == []
