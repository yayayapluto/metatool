import json
from pathlib import Path

from typer.testing import CliRunner

from metatool.cli.app import app

runner = CliRunner()


def test_inspect_json_keeps_stdout_machine_readable_for_parse_errors(tmp_path: Path) -> None:
    invalid_document_path = tmp_path / "invalid.docx"
    invalid_document_path.write_bytes(b"not an OOXML archive")

    command_result = runner.invoke(app, ["inspect", str(invalid_document_path), "--format", "json"])

    assert command_result.exit_code == 3
    assert json.loads(command_result.stdout) == []
