from pathlib import Path

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
