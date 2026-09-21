from __future__ import annotations

from pathlib import Path

import pikepdf
import pytest

from metatool.exceptions import InvalidDocumentError, SanitizationError
from metatool.models import SanitizationOptions
from metatool.sanitizers import pdf as pdf_sanitizer_module
from metatool.sanitizers.pdf import PDFSanitizer
from metatool.scanners import pdf as pdf_scanner_module
from metatool.scanners.pdf import PDFScanner


def _write_pdf(document_path: Path) -> None:
    with pikepdf.new() as pdf_document:
        pdf_document.add_blank_page()
        pdf_document.save(document_path)


def test_pdf_scanner_rejects_input_over_configured_size_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document_path = tmp_path / "large.pdf"
    _write_pdf(document_path)
    monkeypatch.setattr(pdf_scanner_module, "MAX_PDF_FILE_SIZE", 1)

    with pytest.raises(InvalidDocumentError, match="size limit"):
        PDFScanner().inspect(document_path)


def test_pdf_sanitizer_rejects_input_over_configured_size_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_path = tmp_path / "large.pdf"
    destination_path = tmp_path / "clean.pdf"
    _write_pdf(source_path)
    monkeypatch.setattr(pdf_sanitizer_module, "MAX_PDF_FILE_SIZE", 1)

    with pytest.raises(SanitizationError, match="size limit"):
        PDFSanitizer().sanitize(
            source_path, destination_path, SanitizationOptions(profile="privacy")
        )
