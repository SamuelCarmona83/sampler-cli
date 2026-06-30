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
