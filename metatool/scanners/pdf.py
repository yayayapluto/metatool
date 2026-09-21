"""PDF metadata inspection."""

from pathlib import Path

import pikepdf

from metatool.constants import PDF_EXTENSION
from metatool.exceptions import InvalidDocumentError, UnsupportedFormatError
from metatool.models import InspectionResult, MetadataValue
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
                metadata = {
                    "author": _read_document_info(pdf_document, "/Author"),
                    "creator": _read_document_info(pdf_document, "/Creator"),
                    "producer": _read_document_info(pdf_document, "/Producer"),
                    "creation_date": _read_document_info(pdf_document, "/CreationDate"),
                    "modification_date": _read_document_info(pdf_document, "/ModDate"),
                    "has_xmp_metadata": "/Metadata" in pdf_document.Root,
                }
        except pikepdf.PasswordError as exception:
            raise InvalidDocumentError(f"{document_path} is encrypted") from exception
        except pikepdf.PdfError as exception:
            raise InvalidDocumentError(f"{document_path} is not a valid PDF") from exception
        return {
            field_name: field_value
            for field_name, field_value in metadata.items()
            if field_value is not None
        }


def _read_document_info(pdf_document: pikepdf.Pdf, key: str) -> str | None:
    if key not in pdf_document.docinfo:
        return None
    return str(pdf_document.docinfo[key])
