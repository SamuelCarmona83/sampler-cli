from pathlib import Path

import yaml
from pydantic import BaseModel, Field


def default_data_dir() -> Path:
    return Path.home() / ".sampler"


class ProjectConfig(BaseModel):
    name: str
    path: str
    language: str
    enabled: bool = True


class GlobalConfig(BaseModel):
    version: int = 1
    cache_dir: str = str(default_data_dir())
    projects: dict[str, ProjectConfig] = Field(default_factory=dict)


class ConfigManager:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or (default_data_dir() / "config.yaml")

    def load(self) -> GlobalConfig:
        if not self.config_path.exists():
            config = GlobalConfig()
            self.save(config)
            return config

        with self.config_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        config = GlobalConfig.model_validate(raw)

        if config.version != 1:
            config.version = 1
            self.save(config)

        return config

    def save(self, config: GlobalConfig) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = config.model_dump(mode="python")
        with self.config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, sort_keys=False)

    def add_project(self, name: str, path: str, language: str, enabled: bool = True) -> ProjectConfig:
        config = self.load()
        if name in config.projects:
            raise ValueError(f"Project '{name}' already exists")

        project_path = str(Path(path).expanduser().resolve())
        if not Path(project_path).exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        project = ProjectConfig(name=name, path=project_path, language=language, enabled=enabled)
        config.projects[name] = project
        self.save(config)
        return project

    def remove_project(self, name: str) -> None:
        config = self.load()
        if name not in config.projects:
            raise ValueError(f"Project '{name}' does not exist")
        del config.projects[name]
        self.save(config)

    def get_project(self, name: str) -> ProjectConfig | None:
        config = self.load()
        return config.projects.get(name)

    def list_projects(self) -> list[ProjectConfig]:
        config = self.load()
        return list(config.projects.values())
