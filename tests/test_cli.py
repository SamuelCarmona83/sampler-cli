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
