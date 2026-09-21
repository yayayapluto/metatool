from __future__ import annotations

import xml.etree.ElementTree as element_tree
import zipfile
from pathlib import Path

from metatool.models import SanitizationOptions
from metatool.sanitizers.ooxml import OOXMLSanitizer
from metatool.validators.ooxml import OOXMLValidator

CORE_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"


def _write_document_with_metadata(document_path: Path) -> None:
    core_properties = f'''<?xml version="1.0" encoding="UTF-8"?>
    <cp:coreProperties xmlns:cp="{CORE_NAMESPACE}" xmlns:dc="{DC_NAMESPACE}">
      <dc:title>Quarterly report</dc:title><dc:creator>Alice</dc:creator>
      <cp:lastModifiedBy>Bob</cp:lastModifiedBy><cp:keywords>finance</cp:keywords>
    </cp:coreProperties>'''
    extended_properties = """<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
      <Application>Microsoft Word</Application><Company>Example Corp</Company><Manager>Pat</Manager>
    </Properties>"""
    relationships = """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/metadata/custom-properties" Target="docProps/custom.xml" />
    </Relationships>"""
    content_types = """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
      <Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml" />
    </Types>"""
    with zipfile.ZipFile(document_path, "w") as package_archive:
        package_archive.writestr("[Content_Types].xml", content_types)
        package_archive.writestr("_rels/.rels", relationships)
        package_archive.writestr("docProps/core.xml", core_properties)
        package_archive.writestr("docProps/app.xml", extended_properties)
        package_archive.writestr("docProps/custom.xml", "<Properties />")
        package_archive.writestr("word/document.xml", "<w:document xmlns:w='urn:test' />")


def _read_core_property(document_path: Path, namespace: str, property_name: str) -> str | None:
    with zipfile.ZipFile(document_path) as package_archive:
        core_properties = element_tree.fromstring(package_archive.read("docProps/core.xml"))
    property_element = core_properties.find(f"{{{namespace}}}{property_name}")
    return None if property_element is None else property_element.text


def test_privacy_sanitization_preserves_descriptive_core_properties(tmp_path: Path) -> None:
    source_path = tmp_path / "report.docx"
    destination_path = tmp_path / "report-clean.docx"
    _write_document_with_metadata(source_path)

    sanitization_result = OOXMLSanitizer().sanitize(
        source_path, destination_path, SanitizationOptions(profile="privacy")
    )

    assert sanitization_result.destination == str(destination_path)
    assert _read_core_property(destination_path, DC_NAMESPACE, "title") == "Quarterly report"
    assert _read_core_property(destination_path, CORE_NAMESPACE, "keywords") == "finance"
    assert _read_core_property(destination_path, DC_NAMESPACE, "creator") is None
    assert _read_core_property(destination_path, CORE_NAMESPACE, "lastModifiedBy") is None


def test_privacy_sanitization_removes_custom_part_and_package_references(tmp_path: Path) -> None:
    source_path = tmp_path / "report.docx"
    destination_path = tmp_path / "report-clean.docx"
    _write_document_with_metadata(source_path)

    OOXMLSanitizer().sanitize(source_path, destination_path, SanitizationOptions(profile="privacy"))

    with zipfile.ZipFile(destination_path) as package_archive:
        assert "docProps/custom.xml" not in package_archive.namelist()
        assert b"custom.xml" not in package_archive.read("_rels/.rels")
        assert b"custom.xml" not in package_archive.read("[Content_Types].xml")


def test_privacy_sanitization_is_deterministic_and_preserves_source(tmp_path: Path) -> None:
    source_path = tmp_path / "report.docx"
    first_destination_path = tmp_path / "first.docx"
    second_destination_path = tmp_path / "second.docx"
    _write_document_with_metadata(source_path)
    source_bytes = source_path.read_bytes()

    sanitizer = OOXMLSanitizer()
    options = SanitizationOptions(profile="privacy")
    sanitizer.sanitize(source_path, first_destination_path, options)
    sanitizer.sanitize(source_path, second_destination_path, options)

    assert source_path.read_bytes() == source_bytes
    with (
        zipfile.ZipFile(first_destination_path) as first_archive,
        zipfile.ZipFile(second_destination_path) as second_archive,
    ):
        assert first_archive.read("docProps/core.xml") == second_archive.read("docProps/core.xml")
        assert first_archive.read("docProps/app.xml") == second_archive.read("docProps/app.xml")


def test_sanitized_document_passes_ooxml_validation(tmp_path: Path) -> None:
    source_path = tmp_path / "report.docx"
    destination_path = tmp_path / "report-clean.docx"
    _write_document_with_metadata(source_path)

    OOXMLSanitizer().sanitize(source_path, destination_path, SanitizationOptions(profile="privacy"))

    validation_result = OOXMLValidator().validate(destination_path)
    assert validation_result.is_valid
    assert validation_result.errors == []
