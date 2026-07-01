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
