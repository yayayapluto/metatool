from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from metatool.exceptions import InvalidDocumentError
from metatool.scanners import ooxml as ooxml_scanner_module
from metatool.scanners.ooxml import OOXMLScanner


def test_ooxml_scanner_rejects_excessive_custom_property_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document_path = tmp_path / "properties.docx"
    custom_properties = """<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties">
      <property name="one" /><property name="two" />
    </Properties>"""
    with zipfile.ZipFile(document_path, "w") as package_archive:
        package_archive.writestr("[Content_Types].xml", "<Types />")
        package_archive.writestr("docProps/custom.xml", custom_properties)
    monkeypatch.setattr(ooxml_scanner_module, "MAX_CUSTOM_PROPERTIES", 1)

    with pytest.raises(InvalidDocumentError, match="custom property count"):
        OOXMLScanner().inspect(document_path)
