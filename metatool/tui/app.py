"""Textual application using the same core APIs as the CLI."""

from collections.abc import Mapping
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Input, Static

from metatool.exceptions import MetaToolError
from metatool.models import SanitizationOptions
from metatool.services import (
    inspect_document,
    resolve_output_path,
    sanitize_document,
    validate_document,
)


class MetaToolApp(App[None]):
    """Interactive inspection, sanitization, and validation interface."""

    TITLE = "MetaTool"
    CSS = """
    #document-path { width: 1fr; }
    #result { height: 1fr; border: round $accent; padding: 1; }
    """

    def compose(self) -> ComposeResult:
        """Compose path input, workflow controls, and result panel."""
        with Horizontal():
            yield Input(placeholder="Document path", id="document-path")
            yield Button("Inspect", id="inspect", variant="primary")
            yield Button("Sanitize", id="sanitize")
            yield Button("Validate", id="validate")
        yield Static("Choose a document to inspect.", id="result")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dispatch document operations without blocking the event loop."""
        document_path = Path(self.query_one("#document-path", Input).value)
        if event.button.id == "inspect":
            self.inspect_document_worker(document_path)
        elif event.button.id == "sanitize":
            self.sanitize_document_worker(document_path)
        elif event.button.id == "validate":
            self.validate_document_worker(document_path)

    @work(thread=True)
    def inspect_document_worker(self, document_path: Path) -> None:
        """Inspect metadata with the shared core API."""
        try:
            inspection_result = inspect_document(document_path)
            result_text = _format_metadata(inspection_result.metadata)
        except MetaToolError as exception:
            result_text = f"Error: {exception}"
        self._update_result(result_text)

    @work(thread=True)
    def sanitize_document_worker(self, document_path: Path) -> None:
        """Apply the privacy profile to the core-selected output destination."""
        try:
            destination_path = resolve_output_path(document_path, None)
            sanitization_result = sanitize_document(
                document_path, destination_path, SanitizationOptions(profile="privacy")
            )
            result_text = f"Sanitized: {sanitization_result.destination}"
        except MetaToolError as exception:
            result_text = f"Error: {exception}"
        self._update_result(result_text)

    @work(thread=True)
    def validate_document_worker(self, document_path: Path) -> None:
        """Validate package integrity with the shared core API."""
        try:
            validation_result = validate_document(document_path)
            if validation_result.is_valid:
                result_text = f"Valid: {validation_result.path}"
            else:
                result_text = "Validation failed: " + "; ".join(validation_result.errors)
        except MetaToolError as exception:
            result_text = f"Error: {exception}"
        self._update_result(result_text)

    def _update_result(self, result_text: str) -> None:
        self.call_from_thread(self.query_one("#result", Static).update, result_text)


def _format_metadata(metadata: Mapping[str, object]) -> str:
    metadata_lines = [
        f"{field_name}: {field_value}" for field_name, field_value in metadata.items()
    ]
    return "\n".join(metadata_lines) or "No metadata found."
