"""Application orchestration for scanner, sanitizer, and validator selection."""

import tempfile
from pathlib import Path

from metatool.exceptions import UnsupportedFormatError
from metatool.models import (
    InspectionResult,
    SanitizationOptions,
    SanitizationResult,
    ValidationResult,
)
from metatool.sanitizers.ooxml import OOXMLSanitizer
from metatool.sanitizers.pdf import PDFSanitizer
from metatool.scanners.ooxml import OOXMLScanner
from metatool.scanners.pdf import PDFScanner
from metatool.validators.ooxml import OOXMLValidator
from metatool.validators.pdf import PDFValidator

_SCANNERS = (OOXMLScanner(), PDFScanner())
_SANITIZERS = (OOXMLSanitizer(), PDFSanitizer())
_VALIDATORS = ((OOXMLScanner(), OOXMLValidator()), (PDFScanner(), PDFValidator()))


def inspect_document(document_path: Path) -> InspectionResult:
    """Inspect a document using its registered scanner."""
    scanner = _select_component(_SCANNERS, document_path)
    return scanner.inspect(document_path)


def sanitize_document(
    source_path: Path, destination_path: Path, sanitization_options: SanitizationOptions
) -> SanitizationResult:
    """Sanitize a document using its registered sanitizer."""
    sanitizer = _select_component(_SANITIZERS, source_path)
    return sanitizer.sanitize(source_path, destination_path, sanitization_options)


def preview_sanitization(
    source_path: Path, sanitization_options: SanitizationOptions
) -> SanitizationResult:
    """Calculate validated sanitization changes without creating a user-visible output."""
    with tempfile.TemporaryDirectory(prefix="metatool-preview-") as temporary_directory:
        temporary_output_path = Path(temporary_directory) / source_path.name
        return sanitize_document(source_path, temporary_output_path, sanitization_options)


def validate_document(document_path: Path) -> ValidationResult:
    """Validate a document using its registered validator."""
    for scanner, validator in _VALIDATORS:
        if scanner.supports(document_path):
            return validator.validate(document_path)
    raise UnsupportedFormatError(f"unsupported document format: {document_path.suffix}")


def collect_input_paths(
    input_paths: list[Path], is_recursive: bool, excluded_names: tuple[str, ...] = ()
) -> list[Path]:
    """Collect supported document paths without substring-based directory exclusions."""
    discovered_paths: list[Path] = []
    excluded_name_set = set(excluded_names)
    for input_path in input_paths:
        if input_path.is_file():
            if _is_supported_document(input_path):
                discovered_paths.append(input_path)
            continue
        if not input_path.is_dir():
            continue
        candidate_paths = input_path.rglob("*") if is_recursive else input_path.glob("*")
        for candidate_path in sorted(candidate_paths):
            if excluded_name_set.intersection(candidate_path.parts):
                continue
            if candidate_path.is_file() and _is_supported_document(candidate_path):
                discovered_paths.append(candidate_path)
    return discovered_paths


def resolve_output_path(source_path: Path, output_path: Path | None) -> Path:
    """Choose a non-destructive default sanitized output path."""
    if output_path is not None:
        return output_path
    return source_path.with_name(f"{source_path.stem}-clean{source_path.suffix}")


def _select_component(components: tuple[object, ...], document_path: Path):
    for component in components:
        if component.supports(document_path):
            return component
    raise UnsupportedFormatError(f"unsupported document format: {document_path.suffix}")


def _is_supported_document(document_path: Path) -> bool:
    return any(scanner.supports(document_path) for scanner in _SCANNERS)
