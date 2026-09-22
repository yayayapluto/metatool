"""Centralized Rich rendering and JSON serialization."""

import json
from dataclasses import asdict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from metatool.constants import JSON_SCHEMA_VERSION
from metatool.models import (
    Finding,
    InspectionResult,
    SanitizationResult,
    Severity,
    ValidationResult,
)

SEVERITY_STYLES = {
    Severity.INFO: "cyan",
    Severity.NOTICE: "yellow",
    Severity.SUSPICIOUS: "red",
}


def render_inspection(inspection_result: InspectionResult, console: Console) -> None:
    """Render an inspection's normalized metadata and findings."""
    metadata_table = Table(title=inspection_result.path)
    metadata_table.add_column("Property")
    metadata_table.add_column("Value")
    for field_name, field_value in inspection_result.metadata.items():
        metadata_table.add_row(_humanize_field_name(field_name), str(field_value))
    console.print(metadata_table)
    render_findings(inspection_result.findings, console)
    for warning in inspection_result.warnings:
        console.print(Panel(warning, title="Warning", style="yellow"))


def render_findings(findings: list[Finding], console: Console) -> None:
    """Render finding messages and their evidence-based interpretations."""
    for finding in findings:
        style = SEVERITY_STYLES[finding.severity]
        body = finding.message
        if finding.interpretation:
            body = f"{body}\n\n{finding.interpretation}"
        console.print(Panel(body, title=finding.severity.value.upper(), style=style))


def render_sanitization_diff(sanitization_result: SanitizationResult, console: Console) -> None:
    """Render explicit metadata changes as a before-and-after table."""
    changes_table = Table(title="Sanitization Preview")
    changes_table.add_column("Field")
    changes_table.add_column("Before")
    changes_table.add_column("After")
    for sanitization_change in sanitization_result.changes:
        after_value = (
            "removed"
            if sanitization_change.new_value is None
            else str(sanitization_change.new_value)
        )
        changes_table.add_row(
            sanitization_change.field,
            str(sanitization_change.previous_value),
            after_value,
        )
    console.print(changes_table)


def render_validation(validation_result: ValidationResult, console: Console) -> None:
    """Render an OOXML or PDF validation result."""
    if validation_result.is_valid:
        console.print(f"[green]Valid:[/green] {validation_result.path}")
        return
    console.print(
        Panel("\n".join(validation_result.errors), title="Validation failed", style="red")
    )


def render_error(message: str, console: Console) -> None:
    """Render an expected user-facing command error."""
    console.print(Panel(message, title="Error", style="red"))


def serialize_inspection_result(inspection_result: InspectionResult) -> dict[str, object]:
    """Serialize an inspection without leaking Python implementation details."""
    serialized_result = asdict(inspection_result)
    serialized_result["schema_version"] = JSON_SCHEMA_VERSION
    serialized_result["format"] = serialized_result.pop("file_format")
    return serialized_result


def render_json_inspections(inspection_results: list[InspectionResult]) -> str:
    """Return pure machine-readable JSON output."""
    return json.dumps(
        [serialize_inspection_result(result) for result in inspection_results], ensure_ascii=False
    )


def _humanize_field_name(field_name: str) -> str:
    return field_name.replace("_", " ").title()
