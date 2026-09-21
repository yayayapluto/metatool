"""Evidence-based PDF metadata rules."""

from metatool.models import Finding, MetadataValue, Severity
from metatool.rules.ooxml import SUSPICIOUS_CREATOR_TOOLS


class PDFMetadataRules:
    """Evaluate PDF producer and creator metadata."""

    def evaluate(self, metadata: dict[str, MetadataValue]) -> list[Finding]:
        """Return evidence-based findings for PDF metadata."""
        findings: list[Finding] = []
        for field_name in ("creator", "producer"):
            field_value = str(metadata.get(field_name) or "")
            matched_tool = next(
                (tool for tool in SUSPICIOUS_CREATOR_TOOLS if tool in field_value.lower()), None
            )
            if matched_tool is None:
                continue
            findings.append(
                Finding(
                    rule_id=f"PDF_{field_name.upper()}_PRESENT",
                    severity=Severity.NOTICE,
                    field=field_name,
                    value=field_value,
                    message=f"The PDF metadata references {matched_tool}.",
                    interpretation=(
                        f"{matched_tool} participated in PDF creation or modification. "
                        "This does not prove how the document content was authored."
                    ),
                )
            )
        return findings
