from __future__ import annotations

import xml.etree.ElementTree as element_tree
import zipfile
from pathlib import Path

from docx import Document

from metatool.models import SanitizationOptions
from metatool.sanitizers.ooxml import OOXMLSanitizer


def test_sanitized_real_docx_with_custom_properties_reopens(tmp_path: Path) -> None:
    source_path = tmp_path / "source-custom.docx"
    destination_path = tmp_path / "clean-custom.docx"
    document = Document()
    document.add_paragraph("Custom metadata round trip")
    document.save(source_path)

    with zipfile.ZipFile(source_path) as source_archive:
        package_parts = {name: source_archive.read(name) for name in source_archive.namelist()}
    relationships_namespace = "http://schemas.openxmlformats.org/package/2006/relationships"
    content_types_namespace = "http://schemas.openxmlformats.org/package/2006/content-types"
    element_tree.register_namespace("", relationships_namespace)
    relationships = element_tree.fromstring(package_parts["_rels/.rels"])
    element_tree.SubElement(
        relationships,
        f"{{{relationships_namespace}}}Relationship",
        {
            "Id": "rIdCustom",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/metadata/custom-properties",
            "Target": "docProps/custom.xml",
        },
    )
    package_parts["_rels/.rels"] = element_tree.tostring(
        relationships, encoding="utf-8", xml_declaration=True
    )
    element_tree.register_namespace("", content_types_namespace)
    content_types = element_tree.fromstring(package_parts["[Content_Types].xml"])
    element_tree.SubElement(
        content_types,
        f"{{{content_types_namespace}}}Override",
        {
            "PartName": "/docProps/custom.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.custom-properties+xml",
        },
    )
    package_parts["[Content_Types].xml"] = element_tree.tostring(
        content_types, encoding="utf-8", xml_declaration=True
    )
    custom_properties = (
        b'<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
        b'custom-properties" />'
    )
    package_parts["docProps/custom.xml"] = custom_properties
    with zipfile.ZipFile(source_path, "w", zipfile.ZIP_DEFLATED) as destination_archive:
        for name, data in package_parts.items():
            destination_archive.writestr(name, data)

    OOXMLSanitizer().sanitize(source_path, destination_path, SanitizationOptions(profile="privacy"))

    reopened = Document(destination_path)
    assert reopened.paragraphs[0].text == "Custom metadata round trip"
