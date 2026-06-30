from pathlib import Path

from sampler.db import Database
from sampler.indexer.builder import IndexBuilder
from sampler.query.engine import QueryEngine


def test_index_and_search_flow(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    file_path = project_dir / "app.py"
    file_path.write_text(
        """
def add(a, b):
    return a + b


def run(value):
    return add(value, 2)
""",
        encoding="utf-8",
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()

    builder = IndexBuilder(db=db)
    stats = builder.index_project(
        project_name="demo",
        project_path=str(project_dir),
        language="python",
    )

    assert stats["discovered"] == 1
    assert stats["indexed"] == 1

    engine = QueryEngine(db=db)
    results = engine.search("add", project_name="demo")
    assert any((row["qualified_name"] == "add") for row in results)

    overview = engine.overview(str(file_path.resolve()), project_name="demo")
    assert len(overview) >= 2
