from __future__ import annotations

import xml.etree.ElementTree as element_tree
import zipfile
from pathlib import Path

from metatool.models import SanitizationOptions
from metatool.sanitizers.ooxml import OOXMLSanitizer

CORE_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
DCTERMS_NAMESPACE = "http://purl.org/dc/terms/"
EXTENDED_NAMESPACE = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"


def test_privacy_profile_removes_tool_and_history_metadata(tmp_path: Path) -> None:
    source_path = tmp_path / "report.docx"
    destination_path = tmp_path / "report-clean.docx"
    core_properties = f"""<cp:coreProperties xmlns:cp="{CORE_NAMESPACE}"
      xmlns:dc="{DC_NAMESPACE}" xmlns:dcterms="{DCTERMS_NAMESPACE}">
      <dc:title>Quarterly report</dc:title>
      <dc:subject>Finance</dc:subject>
      <dc:keywords>finance</dc:keywords>
      <dc:creator>Alice</dc:creator>
      <cp:lastModifiedBy>Bob</cp:lastModifiedBy>
      <cp:revision>19</cp:revision>
      <dcterms:created>2013-12-23T23:15:00Z</dcterms:created>
      <dcterms:modified>2026-09-21T10:11:00Z</dcterms:modified>
    </cp:coreProperties>"""
    extended_properties = f"""<Properties xmlns="{EXTENDED_NAMESPACE}">
      <Application>Microsoft Office Word</Application>
      <Template>Normal.dotm</Template>
      <TotalTime>364</TotalTime>
      <Pages>38</Pages>
      <Words>3271</Words>
    </Properties>"""
    with zipfile.ZipFile(source_path, "w") as package_archive:
        package_archive.writestr("[Content_Types].xml", "<Types />")
        package_archive.writestr("docProps/core.xml", core_properties)
        package_archive.writestr("docProps/app.xml", extended_properties)

    OOXMLSanitizer().sanitize(source_path, destination_path, SanitizationOptions(profile="privacy"))

    with zipfile.ZipFile(destination_path) as package_archive:
        core_root = element_tree.fromstring(package_archive.read("docProps/core.xml"))
        extended_root = element_tree.fromstring(package_archive.read("docProps/app.xml"))
    assert core_root.find(f"{{{DC_NAMESPACE}}}title") is not None
    assert core_root.find(f"{{{DC_NAMESPACE}}}subject") is not None
    assert core_root.find(f"{{{DC_NAMESPACE}}}keywords") is not None
    for namespace, property_name in (
        (DC_NAMESPACE, "creator"),
        (CORE_NAMESPACE, "lastModifiedBy"),
        (CORE_NAMESPACE, "revision"),
        (DCTERMS_NAMESPACE, "created"),
        (DCTERMS_NAMESPACE, "modified"),
    ):
        assert core_root.find(f"{{{namespace}}}{property_name}") is None
    for property_name in ("Application", "Template", "TotalTime", "Pages", "Words"):
        assert extended_root.find(f"{{{EXTENDED_NAMESPACE}}}{property_name}") is None
