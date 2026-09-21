"""Textual application built on the same core inspection API as the CLI."""

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Input, Static

from metatool.exceptions import MetaToolError
from metatool.services import inspect_document


class MetaToolApp(App[None]):
    """Interactive metadata inspection interface."""

    TITLE = "MetaTool"
    CSS = """
    #document-path { width: 1fr; }
    #result { height: 1fr; border: round $accent; padding: 1; }
    """

    def compose(self) -> ComposeResult:
        """Compose a compact document path input and findings panel."""
        with Horizontal():
            yield Input(placeholder="Document path", id="document-path")
            yield Button("Inspect", id="inspect", variant="primary")
        yield Static("Choose a document to inspect.", id="result")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Start inspection without blocking the Textual event loop."""
        if event.button.id != "inspect":
            return
        document_path = Path(self.query_one("#document-path", Input).value)
        self.inspect_document_worker(document_path)

    @work(thread=True)
    def inspect_document_worker(self, document_path: Path) -> None:
        """Inspect a document in a worker and update the result panel."""
        try:
            inspection_result = inspect_document(document_path)
            metadata_lines = [
                f"{field_name}: {field_value}"
                for field_name, field_value in inspection_result.metadata.items()
            ]
            result_text = "\n".join(metadata_lines) or "No metadata found."
        except MetaToolError as exception:
            result_text = f"Error: {exception}"
        self.call_from_thread(self.query_one("#result", Static).update, result_text)
