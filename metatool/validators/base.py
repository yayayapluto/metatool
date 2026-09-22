"""Validator protocol."""

from pathlib import Path
from typing import Protocol

from metatool.models import ValidationResult


class Validator(Protocol):
    """Contract implemented by format-specific validators."""

    def validate(self, document_path: Path) -> ValidationResult:
        """Validate document structure without changing the document."""
