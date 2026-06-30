from pathlib import Path

from sampler.config import ConfigManager


def test_config_manager_add_and_remove_project(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    manager = ConfigManager(config_path=config_path)
    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    added = manager.add_project("proj", str(project_dir), "python")
    assert added.name == "proj"

    listed = manager.list_projects()
    assert len(listed) == 1
    assert listed[0].name == "proj"

    manager.remove_project("proj")
    assert manager.list_projects() == []
