"""PDF metadata inspection."""

from pathlib import Path

import pikepdf

from metatool.constants import PDF_EXTENSION
from metatool.exceptions import InvalidDocumentError, UnsupportedFormatError
from metatool.models import InspectionResult, MetadataValue
from metatool.pdf_limits import MAX_PDF_FILE_SIZE, MAX_XMP_STREAM_SIZE
from metatool.rules.pdf import PDFMetadataRules


class PDFScanner:
    """Extract document information and XMP-presence metadata from PDFs."""

    def supports(self, document_path: Path) -> bool:
        """Return whether a document has a PDF extension."""
        return document_path.suffix.lower() == PDF_EXTENSION

    def inspect(self, document_path: Path) -> InspectionResult:
        """Inspect PDF metadata without modifying the input document."""
        if not self.supports(document_path):
            raise UnsupportedFormatError(f"unsupported PDF format: {document_path.suffix}")
        if document_path.stat().st_size > MAX_PDF_FILE_SIZE:
            raise InvalidDocumentError("PDF input exceeds the configured size limit")
        metadata = self._extract_metadata(document_path)
        return InspectionResult(
            path=str(document_path),
            file_format="pdf",
            metadata=metadata,
            findings=PDFMetadataRules().evaluate(metadata),
        )

    def _extract_metadata(self, document_path: Path) -> dict[str, MetadataValue]:
        try:
            with pikepdf.open(document_path) as pdf_document:
                has_xmp_metadata = "/Metadata" in pdf_document.Root
                self._validate_xmp_stream_size(pdf_document, has_xmp_metadata)
                metadata = {
                    "author": _read_document_info(pdf_document, "/Author"),
                    "creator": _read_document_info(pdf_document, "/Creator"),
                    "producer": _read_document_info(pdf_document, "/Producer"),
                    "creation_date": _read_document_info(pdf_document, "/CreationDate"),
                    "modification_date": _read_document_info(pdf_document, "/ModDate"),
                    "has_xmp_metadata": has_xmp_metadata,
                }
        except pikepdf.PasswordError as exception:
            raise InvalidDocumentError(f"{document_path} is encrypted") from exception
        except pikepdf.PdfError as exception:
            raise InvalidDocumentError(f"{document_path} is not a valid PDF") from exception
        return {field_name: value for field_name, value in metadata.items() if value is not None}

    def _validate_xmp_stream_size(self, pdf_document: pikepdf.Pdf, has_xmp_metadata: bool) -> None:
        if not has_xmp_metadata:
            return
        metadata_stream = pdf_document.Root.Metadata
        if len(metadata_stream.read_raw_bytes()) > MAX_XMP_STREAM_SIZE:
            raise InvalidDocumentError("PDF XMP metadata exceeds the configured size limit")


def _read_document_info(pdf_document: pikepdf.Pdf, key: str) -> str | None:
    if key not in pdf_document.docinfo:
        return None
    return str(pdf_document.docinfo[key])
