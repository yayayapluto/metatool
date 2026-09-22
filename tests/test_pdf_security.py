from __future__ import annotations

from pathlib import Path

import pikepdf
import pytest

from metatool.exceptions import InvalidDocumentError, SanitizationError
from metatool.models import SanitizationOptions
from metatool.sanitizers.pdf import PDFSanitizer
from metatool.scanners.pdf import PDFScanner


def _write_encrypted_pdf(document_path: Path) -> None:
    with pikepdf.new() as pdf_document:
        pdf_document.add_blank_page()
        pdf_document.save(
            document_path,
            encryption=pikepdf.Encryption(owner="owner-password", user="user-password", R=4),
        )


def test_pdf_scanner_reports_encrypted_documents_as_controlled_errors(tmp_path: Path) -> None:
    encrypted_path = tmp_path / "encrypted.pdf"
    _write_encrypted_pdf(encrypted_path)

    with pytest.raises(InvalidDocumentError, match="encrypted"):
        PDFScanner().inspect(encrypted_path)


def test_pdf_sanitizer_reports_encrypted_documents_as_controlled_errors(tmp_path: Path) -> None:
    encrypted_path = tmp_path / "encrypted.pdf"
    destination_path = tmp_path / "clean.pdf"
    _write_encrypted_pdf(encrypted_path)

    with pytest.raises(SanitizationError, match="could not sanitize PDF"):
        PDFSanitizer().sanitize(
            encrypted_path, destination_path, SanitizationOptions(profile="privacy")
        )
