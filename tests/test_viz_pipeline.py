from pathlib import Path

from sampler.db import Database
from sampler.embeddings import HashProvider
from sampler.indexer.embedder import Embedder
from sampler.viz.pipeline import run_index_pipeline


class _ProjectCfg:
    def __init__(self, name: str, path: str, language: str) -> None:
        self.name = name
        self.path = path
        self.language = language


def test_run_index_pipeline_plain(tmp_path: Path) -> None:
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "main.py").write_text(
        "def alpha():\n    return beta()\n\ndef beta():\n    return 1\n",
        encoding="utf-8",
    )

    db = Database(tmp_path / "graph.db")
    db.init_schema()
    db.add_project(name="proj", path=str(project_dir), language="python")

    stats = run_index_pipeline(
        db=db,
        project_cfg=_ProjectCfg("proj", str(project_dir), "python"),
        embedder=Embedder(provider=HashProvider()),
        plain=True,
    )

    assert stats["indexed"] == 1
    assert stats["embed_count"] == 2
    assert stats["symbols"] == 2