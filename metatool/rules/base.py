"""Rule protocol."""

from typing import Protocol

from metatool.models import Finding, MetadataValue


class Rule(Protocol):
    """Contract for metadata interpretation rules."""

    def evaluate(self, metadata: dict[str, MetadataValue]) -> list[Finding]:
        """Return evidence-based findings for normalized metadata."""
