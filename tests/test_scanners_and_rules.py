from __future__ import annotations

import zipfile
from pathlib import Path

import pikepdf
import pytest

from metatool.exceptions import InvalidDocumentError, UnsupportedFormatError
from metatool.rules.ooxml import OOXMLMetadataRules
from metatool.scanners.ooxml import OOXMLScanner
from metatool.scanners.pdf import PDFScanner


def _write_ooxml_document(document_path: Path, creator: str = "Alice") -> None:
    core_properties = f"""<cp:coreProperties
      xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
      xmlns:dc="http://purl.org/dc/elements/1.1/">
      <dc:creator>{creator}</dc:creator><cp:lastModifiedBy>Bob</cp:lastModifiedBy>
    </cp:coreProperties>"""
    extended_properties = """<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
      <Application>Microsoft Word</Application><Company>Example Corp</Company>
    </Properties>"""
    with zipfile.ZipFile(document_path, "w") as package_archive:
        package_archive.writestr("[Content_Types].xml", "<Types />")
        package_archive.writestr("docProps/core.xml", core_properties)
        package_archive.writestr("docProps/app.xml", extended_properties)


def _write_pdf_document(document_path: Path, creator: str = "Microsoft Word") -> None:
    with pikepdf.new() as pdf_document:
        pdf_document.add_blank_page()
        pdf_document.docinfo["/Creator"] = creator
        pdf_document.docinfo["/Author"] = "Alice"
        pdf_document.save(document_path)


def test_ooxml_scanner_extracts_normalized_metadata(tmp_path: Path) -> None:
    document_path = tmp_path / "report.docx"
    _write_ooxml_document(document_path)

    inspection_result = OOXMLScanner().inspect(document_path)

    assert inspection_result.file_format == "docx"
    assert inspection_result.metadata["creator"] == "Alice"
    assert inspection_result.metadata["company"] == "Example Corp"


def test_ooxml_rules_describe_tool_metadata_as_evidence_not_proof(tmp_path: Path) -> None:
    document_path = tmp_path / "report.docx"
    _write_ooxml_document(document_path, creator="python-docx")

    inspection_result = OOXMLScanner().inspect(document_path)
    findings = OOXMLMetadataRules().evaluate(inspection_result.metadata)

    assert findings[0].rule_id == "OOXML_CREATOR_PRESENT"
    assert "does not prove" in findings[0].interpretation.lower()


def test_ooxml_scanner_rejects_malformed_xml(tmp_path: Path) -> None:
    document_path = tmp_path / "invalid.docx"
    with zipfile.ZipFile(document_path, "w") as package_archive:
        package_archive.writestr("[Content_Types].xml", "<Types />")
        package_archive.writestr("docProps/core.xml", "<broken")

    with pytest.raises(InvalidDocumentError, match="invalid XML"):
        OOXMLScanner().inspect(document_path)


def test_pdf_scanner_extracts_document_information(tmp_path: Path) -> None:
    document_path = tmp_path / "report.pdf"
    _write_pdf_document(document_path)

    inspection_result = PDFScanner().inspect(document_path)

    assert inspection_result.file_format == "pdf"
    assert inspection_result.metadata["creator"] == "Microsoft Word"


def test_scanners_reject_unsupported_paths(tmp_path: Path) -> None:
    document_path = tmp_path / "report.txt"
    document_path.write_text("not a document")

    with pytest.raises(UnsupportedFormatError):
        OOXMLScanner().inspect(document_path)
    with pytest.raises(UnsupportedFormatError):
        PDFScanner().inspect(document_path)
