from pathlib import Path

from typer.testing import CliRunner

from sampler.cli.main import app


def test_project_add_list_remove(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()

    project_dir = tmp_path / "proj"
    project_dir.mkdir()

    add_result = runner.invoke(app, ["project", "add", "proj", str(project_dir), "--language", "python"])
    assert add_result.exit_code == 0

    list_result = runner.invoke(app, ["project", "list"])
    assert list_result.exit_code == 0
    assert "proj" in list_result.stdout

    rm_result = runner.invoke(app, ["project", "remove", "proj"])
    assert rm_result.exit_code == 0


def test_stale_code_command(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()

    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "app.py").write_text(
        """
def stale_target(x):
    return x
""",
        encoding="utf-8",
    )
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text(
        """
from app import stale_target

def test_stale_target():
    assert stale_target(1) == 1
""",
        encoding="utf-8",
    )

    assert runner.invoke(app, ["project", "add", "proj", str(project_dir), "--language", "python"]).exit_code == 0
    assert runner.invoke(app, ["index", "proj"]).exit_code == 0

    stale = runner.invoke(app, ["stale-code", "proj"])
    assert stale.exit_code == 0
    assert "stale_target" in stale.stdout


def test_config_embeddings_commands(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()

    # show before any explicit set
    res = runner.invoke(app, ["config", "show"])
    assert res.exit_code == 0
    assert "embeddings" in res.stdout or "bge-small" in res.stdout.lower()

    # set via command
    res2 = runner.invoke(app, ["config", "embeddings", "--provider", "hash"])
    assert res2.exit_code == 0
    assert "hash" in res2.stdout

    res3 = runner.invoke(app, ["config", "embeddings", "--provider", "ollama", "--model", "nomic-embed-text"])
    assert res3.exit_code == 0
    assert "ollama" in res3.stdout
    assert "nomic-embed-text" in res3.stdout


def test_global_version_option() -> None:
    runner = CliRunner()
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "sampler" in res.stdout


def test_embed_runtime_error_is_clean(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()

    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "app.py").write_text(
        """
def foo():
    return 1
""",
        encoding="utf-8",
    )

    assert runner.invoke(app, ["project", "add", "proj", str(project_dir), "--language", "python"]).exit_code == 0
    assert runner.invoke(app, ["index", "proj"]).exit_code == 0
    assert runner.invoke(app, ["config", "embeddings", "--provider", "hash"]).exit_code == 0

    import sampler.indexer.embedder as embedder_mod

    def _boom(self, db, project_name, batch_size=32, on_progress=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(embedder_mod.Embedder, "embed_project", _boom)

    res = runner.invoke(app, ["embed", "proj"])
    assert res.exit_code == 1
    assert "boom" in res.stdout
    assert "Invalid value" not in res.stdout
    assert "Usage: sampler embed" not in res.stdout
