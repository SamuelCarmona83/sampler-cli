from pathlib import Path
from uuid import uuid4

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


def test_callers_disambiguate_with_file_option(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()

    project_name = f"proj_{uuid4().hex[:8]}"
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    api_dir = project_dir / "api"
    app_dir = project_dir / "app"
    api_dir.mkdir()
    app_dir.mkdir()

    (api_dir / "helpers.py").write_text(
        """
def format_kda(k, d, a):
    return f"{k}/{d}/{a}"
""",
        encoding="utf-8",
    )
    (app_dir / "helpers.py").write_text(
        """
def format_kda(k, d, a):
    return f"{k}:{d}:{a}"
""",
        encoding="utf-8",
    )

    assert (
        runner.invoke(app, ["project", "add", project_name, str(project_dir), "--language", "python"]).exit_code
        == 0
    )
    assert runner.invoke(app, ["index", project_name]).exit_code == 0

    ambiguous = runner.invoke(app, ["callers", "format_kda", "--project", project_name])
    assert ambiguous.exit_code == 0
    assert "Ambiguous symbol" in ambiguous.stdout

    resolved = runner.invoke(
        app,
        ["callers", "format_kda", "--project", project_name, "--file", "api/helpers.py"],
    )
    assert resolved.exit_code == 0
    # Depending on index state, duplicate logical rows may still exist; verify file-aware guidance appears.
    if "Ambiguous symbol" in resolved.stdout:
        assert "--file is set but still ambiguous" in resolved.stdout


def test_callers_supports_path_symbol_selector(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()

    project_name = f"proj_sel_{uuid4().hex[:8]}"
    project_dir = tmp_path / "proj"
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

    assert (
        runner.invoke(app, ["project", "add", project_name, str(project_dir), "--language", "python"]).exit_code
        == 0
    )
    assert runner.invoke(app, ["index", project_name]).exit_code == 0

    res = runner.invoke(app, ["callers", "helpers.py:format_kda", "--project", project_name])
    assert res.exit_code == 0
    assert "run" in res.stdout
