from __future__ import annotations

import zipfile
from pathlib import Path

from metatool.models import SanitizationOptions
from metatool.sanitizers.ooxml import OOXMLSanitizer
from metatool.validators.ooxml import OOXMLValidator


def _write_document_with_nested_relationship(document_path: Path, relationship_target: str) -> None:
    content_types = """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
      <Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml" />
    </Types>"""
    nested_relationships = f"""<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="urn:test" Target="{relationship_target}" />
    </Relationships>"""
    with zipfile.ZipFile(document_path, "w") as package_archive:
        package_archive.writestr("[Content_Types].xml", content_types)
        package_archive.writestr("docProps/core.xml", "<coreProperties />")
        package_archive.writestr("docProps/custom.xml", "<Properties />")
        package_archive.writestr("word/document.xml", "<document />")
        package_archive.writestr("word/_rels/document.xml.rels", nested_relationships)


def test_privacy_sanitization_removes_nested_relationship_to_custom_properties(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "report.docx"
    destination_path = tmp_path / "report-clean.docx"
    _write_document_with_nested_relationship(source_path, "../docProps/custom.xml")

    OOXMLSanitizer().sanitize(source_path, destination_path, SanitizationOptions(profile="privacy"))

    with zipfile.ZipFile(destination_path) as package_archive:
        relationship_bytes = package_archive.read("word/_rels/document.xml.rels")
    assert b"custom.xml" not in relationship_bytes


def test_validator_rejects_dangling_nested_relationship(tmp_path: Path) -> None:
    document_path = tmp_path / "invalid.docx"
    _write_document_with_nested_relationship(document_path, "missing.xml")

    validation_result = OOXMLValidator().validate(document_path)

    assert not validation_result.is_valid
    assert "word/missing.xml" in validation_result.errors[0]
