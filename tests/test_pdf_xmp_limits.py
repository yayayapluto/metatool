from __future__ import annotations

from pathlib import Path

import pikepdf
import pytest

from metatool.exceptions import InvalidDocumentError
from metatool.scanners import pdf as pdf_scanner_module
from metatool.scanners.pdf import PDFScanner


def _write_pdf_with_xmp(document_path: Path) -> None:
    with pikepdf.new() as pdf_document:
        pdf_document.add_blank_page()
        pdf_document.Root.Metadata = pikepdf.Stream(pdf_document, b"<xmp>metadata</xmp>")
        pdf_document.save(document_path)


def test_pdf_scanner_rejects_oversized_xmp_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document_path = tmp_path / "xmp.pdf"
    _write_pdf_with_xmp(document_path)
    monkeypatch.setattr(pdf_scanner_module, "MAX_XMP_STREAM_SIZE", 1)

    with pytest.raises(InvalidDocumentError, match="XMP metadata exceeds"):
        PDFScanner().inspect(document_path)
