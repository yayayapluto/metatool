from __future__ import annotations

import xml.etree.ElementTree as element_tree
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from metatool.cli.app import app

CORE_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"

runner = CliRunner()


def test_author_option_selects_author_profile_without_profile_flag(tmp_path: Path) -> None:
    source_path = tmp_path / "report.docx"
    with zipfile.ZipFile(source_path, "w") as package_archive:
        package_archive.writestr("[Content_Types].xml", "<Types />")
        package_archive.writestr(
            "docProps/core.xml",
            f"""<cp:coreProperties xmlns:cp="{CORE_NAMESPACE}" xmlns:dc="{DC_NAMESPACE}">
              <dc:creator>Alice</dc:creator>
            </cp:coreProperties>""",
        )

    command_result = runner.invoke(app, ["sanitize", str(source_path), "--author", "Jane Doe"])

    assert command_result.exit_code == 0
    destination_path = tmp_path / "report-clean.docx"
    with zipfile.ZipFile(destination_path) as package_archive:
        core_root = element_tree.fromstring(package_archive.read("docProps/core.xml"))
    creator = core_root.find(f"{{{DC_NAMESPACE}}}creator")
    assert creator is not None
    assert creator.text == "Jane Doe"
