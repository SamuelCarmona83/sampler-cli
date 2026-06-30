from typer.testing import CliRunner

from sampler.cli.main import app


def test_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "sampler" in result.stdout.lower()
