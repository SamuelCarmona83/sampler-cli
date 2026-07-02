from pathlib import Path

from sampler.db import Database


def test_db_schema_and_project_crud(tmp_path: Path) -> None:
    db_path = tmp_path / "sampler.db"
    db = Database(db_path)
    db.init_schema()

    project_id = db.add_project("p1", "/tmp/p1", "python")
    assert project_id > 0

    project = db.get_project("p1")
    assert project is not None
    assert project["name"] == "p1"

    projects = db.list_projects()
    assert len(projects) == 1

    db.remove_project("p1")
    assert db.get_project("p1") is None


def test_project_language_breakdown_for_auto(tmp_path: Path) -> None:
    db_path = tmp_path / "sampler.db"
    db = Database(db_path)
    db.init_schema()

    pid = db.add_project("autoproj", "/tmp/ap", "auto")

    # Simulate files discovered+indexed under different langs (as builder does for auto)
    db.upsert_file(pid, "/tmp/ap/a.ts", "typescript", "h1")
    db.upsert_file(pid, "/tmp/ap/b.ts", "typescript", "h2")
    db.upsert_file(pid, "/tmp/ap/c.js", "javascript", "h3")
    db.upsert_file(pid, "/tmp/ap/d.vue", "vue", "h4")
    db.upsert_file(pid, "/tmp/ap/e.py", "python", "h5")

    breakdown = db.get_project_language_breakdown("autoproj")
    assert breakdown["typescript"] == 2
    assert breakdown["javascript"] == 1
    assert breakdown["vue"] == 1
    assert breakdown["python"] == 1

    total = sum(breakdown.values())
    assert total == 5
