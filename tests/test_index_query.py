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


def test_index_project_auto_mode_routes_per_file_language(tmp_path: Path) -> None:
    project_dir = tmp_path / "monorepo"
    project_dir.mkdir()
    (project_dir / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (project_dir / "main.go").write_text(
        "package main\n\nfunc helper(x int) int {\n    return x\n}\n", encoding="utf-8"
    )
    (project_dir / "app.ts").write_text(
        "export function greet(name: string): string {\n    return name;\n}\n", encoding="utf-8"
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()

    builder = IndexBuilder(db=db)
    stats = builder.index_project(project_name="mono", project_path=str(project_dir), language="auto")

    assert stats["discovered"] == 3
    assert stats["indexed"] == 3
    assert stats["failed"] == 0

    engine = QueryEngine(db=db)
    names = {row["qualified_name"] for row in engine.list_symbols(project_name="mono")}
    assert "add" in names
    assert "helper" in names
    assert "greet" in names


def test_cross_project_dependency_detected_via_imports(tmp_path: Path) -> None:
    shared_dir = tmp_path / "shared_utils"
    shared_dir.mkdir()
    (shared_dir / "core.py").write_text("def helper():\n    return 1\n", encoding="utf-8")

    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "main.py").write_text("import shared_utils.core\n\ndef run():\n    return 1\n", encoding="utf-8")

    db = Database(tmp_path / "graph.db")
    db.init_schema()
    builder = IndexBuilder(db=db)

    # shared_utils must be indexed first so it's a known/resolvable project.
    builder.index_project(project_name="shared_utils", project_path=str(shared_dir), language="python")
    builder.index_project(project_name="app", project_path=str(app_dir), language="python")

    deps = db.get_project_dependencies("app")
    assert any(
        d["source_project"] == "app" and d["target_project"] == "shared_utils" and d["type"] == "IMPORTS"
        for d in deps
    )


def test_cross_file_dotted_call_resolves_to_unique_leaf_symbol(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "helpers.py").write_text(
        """
def format_kda(k, d, a):
    return f"{k}/{d}/{a}"
""",
        encoding="utf-8",
    )
    (project_dir / "service.py").write_text(
        """
import helpers

def run(k, d, a):
    return helpers.format_kda(k, d, a)
""",
        encoding="utf-8",
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()
    builder = IndexBuilder(db=db)
    builder.index_project(project_name="demo", project_path=str(project_dir), language="python")

    engine = QueryEngine(db=db)
    matches, callers = engine.callers("format_kda", project_name="demo")

    assert len(matches) == 1
    caller_names = {c["qualified_name"] or c["name"] for c in callers}
    assert "run" in caller_names
