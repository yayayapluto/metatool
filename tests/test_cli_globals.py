from typer.testing import CliRunner

from metatool.cli.app import app

runner = CliRunner()


def test_version_option_reports_package_version() -> None:
    command_result = runner.invoke(app, ["--version"])

    assert command_result.exit_code == 0
    assert "0.5.0" in command_result.stdout
