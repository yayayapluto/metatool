"""PDF structural validation."""

from pathlib import Path

import pikepdf

from metatool.models import ValidationResult


class PDFValidator:
    """Validate that pikepdf can reopen a generated PDF."""

    def validate(self, document_path: Path) -> ValidationResult:
        """Return a validation result without exposing a parser exception to callers."""
        try:
            with pikepdf.open(document_path):
                return ValidationResult(path=str(document_path), is_valid=True)
        except (OSError, pikepdf.PdfError, pikepdf.PasswordError) as exception:
            return ValidationResult(
                path=str(document_path), is_valid=False, errors=[str(exception)]
            )
