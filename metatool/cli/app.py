"""Typer command routing for MetaTool."""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress

from metatool.cli.render import (
    render_error,
    render_inspection,
    render_json_inspections,
    render_sanitization_diff,
    render_validation,
)
from metatool.exceptions import MetaToolError
from metatool.models import InspectionResult, SanitizationOptions, Severity
from metatool.services import (
    collect_input_paths,
    inspect_document,
    preview_sanitization,
    resolve_output_path,
    sanitize_document,
    validate_document,
)

PACKAGE_VERSION = "0.5.0"
app = typer.Typer(name="metatool", no_args_is_help=True)
console = Console()


def _show_version(is_requested: bool) -> None:
    if not is_requested:
        return
    typer.echo(f"metatool {PACKAGE_VERSION}")
    raise typer.Exit()


@app.callback()
def configure_application(
    context: typer.Context,
    version: bool = typer.Option(False, "--version", callback=_show_version, is_eager=True),
    verbose: bool = typer.Option(False, "--verbose"),
    quiet: bool = typer.Option(False, "--quiet"),
    debug: bool = typer.Option(False, "--debug"),
    no_color: bool = typer.Option(False, "--no-color"),
) -> None:
    """Configure global diagnostic and rendering options."""
    context.ensure_object(dict)
    context.obj["quiet"] = quiet
    if quiet:
        logging.disable(logging.INFO)
    if verbose:
        logging.basicConfig(level=logging.INFO)
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    if no_color:
        console.no_color = True


@app.command()
def inspect(
    context: typer.Context,
    paths: list[Path] = typer.Argument(..., exists=True),
    recursive: bool = typer.Option(False, "--recursive"),
    output_format: str = typer.Option("table", "--format"),
    fail_on: Severity | None = typer.Option(None, "--fail-on"),
    exclude: list[str] = typer.Option([], "--exclude"),
) -> None:
    """Inspect document metadata and render evidence-based findings."""
    document_paths = collect_input_paths(paths, recursive, tuple(exclude))
    show_progress = _should_show_progress(
        output_format,
        any(path.is_dir() for path in paths),
        bool(context.obj.get("quiet", False)),
        console.is_terminal,
    )
    inspection_results = _inspect_paths(document_paths, output_format, show_progress)
    if output_format == "json":
        typer.echo(render_json_inspections(inspection_results))
    elif output_format == "table":
        for inspection_result in inspection_results:
            render_inspection(inspection_result, console)
    else:
        render_error("--format must be table or json", console)
        raise typer.Exit(code=2)
    if fail_on is not None and any(
        finding.severity is fail_on
        for inspection_result in inspection_results
        for finding in inspection_result.findings
    ):
        raise typer.Exit(code=1)


@app.command()
def sanitize(
    paths: list[Path] = typer.Argument(..., exists=True),
    profile: str = typer.Option("privacy", "--profile"),
    output: Path | None = typer.Option(None, "--output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    author: str | None = typer.Option(None, "--author"),
) -> None:
    """Sanitize one or more documents into separate destinations."""
    document_paths = collect_input_paths(paths, is_recursive=False)
    if output is not None and len(document_paths) != 1:
        render_error("--output requires exactly one input document", console)
        raise typer.Exit(code=2)
    sanitization_options = SanitizationOptions(profile=profile, author=author)
    try:
        for document_path in document_paths:
            if dry_run:
                sanitization_result = preview_sanitization(document_path, sanitization_options)
            else:
                destination_path = resolve_output_path(document_path, output)
                sanitization_result = sanitize_document(
                    document_path, destination_path, sanitization_options
                )
            render_sanitization_diff(sanitization_result, console)
    except MetaToolError as exception:
        render_error(str(exception), console)
        raise typer.Exit(code=4) from exception


@app.command()
def validate(paths: list[Path] = typer.Argument(..., exists=True)) -> None:
    """Validate document package integrity."""
    document_paths = collect_input_paths(paths, is_recursive=False)
    has_validation_failure = False
    for document_path in document_paths:
        try:
            validation_result = validate_document(document_path)
        except MetaToolError as exception:
            render_error(str(exception), console)
            has_validation_failure = True
            continue
        render_validation(validation_result, console)
        has_validation_failure = has_validation_failure or not validation_result.is_valid
    if has_validation_failure:
        raise typer.Exit(code=5)


@app.command()
def tui() -> None:
    """Launch the optional Textual interface."""
    from metatool.tui.app import MetaToolApp

    MetaToolApp().run()


def _inspect_paths(
    document_paths: list[Path], output_format: str, show_progress: bool = False
) -> list[InspectionResult]:
    inspection_results: list[InspectionResult] = []
    progress = Progress(console=console) if show_progress else None
    if progress is None:
        return _inspect_paths_without_progress(document_paths, output_format)
    with progress:
        task_id = progress.add_task("Inspecting documents", total=len(document_paths))
        for document_path in document_paths:
            inspection_results.append(_inspect_one(document_path, output_format))
            progress.advance(task_id)
    return inspection_results


def _inspect_paths_without_progress(
    document_paths: list[Path], output_format: str
) -> list[InspectionResult]:
    return [_inspect_one(document_path, output_format) for document_path in document_paths]


def _inspect_one(document_path: Path, output_format: str) -> InspectionResult:
    try:
        return inspect_document(document_path)
    except MetaToolError as exception:
        if output_format == "json":
            typer.echo("[]")
        else:
            render_error(str(exception), console)
        raise typer.Exit(code=3) from exception


def _should_show_progress(
    output_format: str,
    has_directory_input: bool,
    quiet: bool,
    is_interactive: bool,
) -> bool:
    """Return whether a human-facing directory operation should show progress."""
    return output_format == "table" and has_directory_input and not quiet and is_interactive
