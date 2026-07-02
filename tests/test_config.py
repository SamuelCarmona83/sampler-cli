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


def test_embeddings_config_defaults_and_update(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    manager = ConfigManager(config_path=config_path)

    # Defaults on first load (new GlobalConfig)
    emb = manager.get_embeddings_config()
    assert emb.provider == "bge-small"
    assert emb.model is None
    assert emb.base_url is None

    # Partial update
    updated = manager.update_embeddings(provider="ollama", model="nomic-embed-text")
    assert updated.provider == "ollama"
    assert updated.model == "nomic-embed-text"

    # Reload reflects
    emb2 = manager.get_embeddings_config()
    assert emb2.provider == "ollama"
    assert emb2.model == "nomic-embed-text"

    # Another partial (base_url)
    updated3 = manager.update_embeddings(base_url="http://localhost:11434")
    assert updated3.base_url == "http://localhost:11434"
    assert updated3.provider == "ollama"  # unchanged

    # Set back to hash for offline
    manager.update_embeddings(provider="hash")
    assert manager.get_embeddings_config().provider == "hash"
