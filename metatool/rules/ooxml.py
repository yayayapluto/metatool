"""Evidence-based OOXML metadata rules."""

from metatool.models import Finding, MetadataValue, Severity

SUSPICIOUS_CREATOR_TOOLS = (
    "python-docx",
    "python-pptx",
    "openpyxl",
    "reportlab",
    "fpdf",
    "pandoc",
    "weasyprint",
    "wkhtmltopdf",
)


class OOXMLMetadataRules:
    """Evaluate OOXML metadata without claiming document authorship."""

    def evaluate(self, metadata: dict[str, MetadataValue]) -> list[Finding]:
        """Return findings for observable OOXML metadata fields."""
        findings: list[Finding] = []
        creator = str(metadata.get("creator") or "")
        application = str(metadata.get("application") or "")
        self._append_creator_finding(findings, creator)
        self._append_application_finding(findings, application)
        self._append_custom_properties_finding(findings, metadata)
        return findings

    def _append_creator_finding(self, findings: list[Finding], creator: str) -> None:
        matched_tool = _find_known_tool(creator)
        if matched_tool is None:
            return
        findings.append(
            Finding(
                rule_id="OOXML_CREATOR_PRESENT",
                severity=Severity.NOTICE,
                field="creator",
                value=creator,
                message=f"The document metadata references {matched_tool}.",
                interpretation=(
                    f"{matched_tool} participated in document creation or modification. "
                    "This does not prove how the document content was authored."
                ),
            )
        )

    def _append_application_finding(self, findings: list[Finding], application: str) -> None:
        if not application:
            return
        findings.append(
            Finding(
                rule_id="OOXML_APPLICATION_PRESENT",
                severity=Severity.INFO,
                field="application",
                value=application,
                message=f"The document metadata lists {application} as its application.",
                interpretation="This records an application involved in a save operation, not authorship.",
            )
        )

    def _append_custom_properties_finding(
        self, findings: list[Finding], metadata: dict[str, MetadataValue]
    ) -> None:
        if metadata.get("has_custom_properties") is not True:
            return
        findings.append(
            Finding(
                rule_id="OOXML_CUSTOM_PROPERTIES_PRESENT",
                severity=Severity.NOTICE,
                field="docProps/custom.xml",
                message="Custom document properties are present.",
                interpretation="Custom properties may contain additional metadata selected by a document author or tool.",
            )
        )


def _find_known_tool(metadata_value: str) -> str | None:
    normalized_value = metadata_value.lower()
    return next((tool for tool in SUSPICIOUS_CREATOR_TOOLS if tool in normalized_value), None)
