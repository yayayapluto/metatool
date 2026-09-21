from __future__ import annotations

import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from metatool.cli.app import app

runner = CliRunner()


def _write_cli_document(document_path: Path) -> None:
    core_properties = """<cp:coreProperties
      xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
      xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Report</dc:title>
      <dc:creator>Alice</dc:creator></cp:coreProperties>"""
    with zipfile.ZipFile(document_path, "w") as package_archive:
        package_archive.writestr("[Content_Types].xml", "<Types />")
        package_archive.writestr("docProps/core.xml", core_properties)


def test_inspect_json_output_is_machine_readable(tmp_path: Path) -> None:
    document_path = tmp_path / "report.docx"
    _write_cli_document(document_path)

    command_result = runner.invoke(app, ["inspect", str(document_path), "--format", "json"])

    assert command_result.exit_code == 0
    serialized_results = json.loads(command_result.stdout)
    assert serialized_results[0]["schema_version"] == 1
    assert serialized_results[0]["metadata"]["creator"] == "Alice"


def test_inspect_human_output_uses_metadata_labels(tmp_path: Path) -> None:
    document_path = tmp_path / "report.docx"
    _write_cli_document(document_path)

    command_result = runner.invoke(app, ["inspect", str(document_path)])

    assert command_result.exit_code == 0
    assert "Creator" in command_result.stdout
    assert "Alice" in command_result.stdout


def test_sanitize_dry_run_does_not_write_destination(tmp_path: Path) -> None:
    document_path = tmp_path / "report.docx"
    destination_path = tmp_path / "report-clean.docx"
    _write_cli_document(document_path)

    command_result = runner.invoke(
        app,
        ["sanitize", str(document_path), "--output", str(destination_path), "--dry-run"],
    )

    assert command_result.exit_code == 0
    assert "Sanitization Preview" in command_result.stdout
    assert not destination_path.exists()


def test_validate_returns_parsing_failure_exit_code_for_invalid_document(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.docx"
    invalid_path.write_bytes(b"not a zip archive")

    command_result = runner.invoke(app, ["validate", str(invalid_path)])

    assert command_result.exit_code == 5
    assert "invalid" in command_result.stdout.lower()
