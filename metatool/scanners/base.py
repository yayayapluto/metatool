"""Scanner protocol."""

from pathlib import Path
from typing import Protocol

from metatool.models import InspectionResult


class Scanner(Protocol):
    """Contract implemented by format-specific scanners."""

    def supports(self, document_path: Path) -> bool:
        """Return whether this scanner supports the path."""

    def inspect(self, document_path: Path) -> InspectionResult:
        """Inspect document metadata without changing the input."""
