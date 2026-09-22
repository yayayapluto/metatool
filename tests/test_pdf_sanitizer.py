from __future__ import annotations

from pathlib import Path

import pikepdf

from metatool.models import SanitizationOptions
from metatool.sanitizers.pdf import PDFSanitizer
from metatool.validators.pdf import PDFValidator


def _write_pdf_with_metadata(document_path: Path) -> None:
    with pikepdf.new() as pdf_document:
        pdf_document.add_blank_page()
        pdf_document.docinfo["/Author"] = "Alice"
        pdf_document.docinfo["/Creator"] = "python-docx"
        pdf_document.docinfo["/Producer"] = "Example Producer"
        pdf_document.Root.Metadata = pdf_document.make_stream(
            b"<x:xmpmeta xmlns:x='adobe:ns:meta/' />"
        )
        pdf_document.save(document_path)


def test_privacy_sanitization_removes_pdf_document_info_and_xmp(tmp_path: Path) -> None:
    source_path = tmp_path / "report.pdf"
    destination_path = tmp_path / "report-clean.pdf"
    _write_pdf_with_metadata(source_path)

    sanitization_result = PDFSanitizer().sanitize(
        source_path, destination_path, SanitizationOptions(profile="privacy")
    )

    assert sanitization_result.changes
    with pikepdf.open(destination_path) as sanitized_document:
        assert len(sanitized_document.docinfo) == 0
        assert "/Metadata" not in sanitized_document.Root


def test_author_profile_replaces_pdf_author_without_fabricating_other_fields(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "report.pdf"
    destination_path = tmp_path / "report-clean.pdf"
    _write_pdf_with_metadata(source_path)

    PDFSanitizer().sanitize(
        source_path,
        destination_path,
        SanitizationOptions(profile="author", author="Jane Doe"),
    )

    with pikepdf.open(destination_path) as sanitized_document:
        assert str(sanitized_document.docinfo["/Author"]) == "Jane Doe"
        assert len(sanitized_document.docinfo) == 1


def test_sanitized_pdf_passes_validation(tmp_path: Path) -> None:
    source_path = tmp_path / "report.pdf"
    destination_path = tmp_path / "report-clean.pdf"
    _write_pdf_with_metadata(source_path)

    PDFSanitizer().sanitize(source_path, destination_path, SanitizationOptions(profile="minimal"))

    validation_result = PDFValidator().validate(destination_path)
    assert validation_result.is_valid
