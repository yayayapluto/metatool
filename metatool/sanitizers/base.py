"""Sanitizer protocol."""

from pathlib import Path
from typing import Protocol

from metatool.models import SanitizationOptions, SanitizationResult


class Sanitizer(Protocol):
    """Contract implemented by format-specific sanitizers."""

    def supports(self, document_path: Path) -> bool:
        """Return whether this sanitizer supports the path."""

    def sanitize(
        self,
        source_path: Path,
        destination_path: Path,
        sanitization_options: SanitizationOptions,
    ) -> SanitizationResult:
        """Sanitize a source document into a separate destination."""
