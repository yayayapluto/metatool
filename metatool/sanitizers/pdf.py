"""Safe, deterministic PDF sanitization."""

import os
import tempfile
from pathlib import Path

import pikepdf

from metatool.constants import PDF_EXTENSION
from metatool.exceptions import SanitizationError
from metatool.models import (
    SanitizationAction,
    SanitizationChange,
    SanitizationOptions,
    SanitizationResult,
)


class PDFSanitizer:
    """Remove or explicitly replace PDF metadata."""

    def supports(self, document_path: Path) -> bool:
        """Return whether a document has a PDF extension."""
        return document_path.suffix.lower() == PDF_EXTENSION

    def sanitize(
        self,
        source_path: Path,
        destination_path: Path,
        sanitization_options: SanitizationOptions,
    ) -> SanitizationResult:
        """Sanitize into a validated temporary PDF then atomically replace the destination."""
        self._validate_destination(source_path, destination_path, sanitization_options)
        temporary_output_path = self._create_temporary_output_path(destination_path)
        try:
            sanitization_changes = self._sanitize_to_temporary_output(
                source_path, temporary_output_path, sanitization_options
            )
            self._validate_temporary_output(
                temporary_output_path, sanitization_options.validate_output
            )
            os.replace(temporary_output_path, destination_path)
        except (OSError, pikepdf.PdfError) as exception:
            raise SanitizationError(f"could not sanitize PDF: {source_path}") from exception
        finally:
            if temporary_output_path.exists():
                temporary_output_path.unlink()
        return SanitizationResult(
            source=str(source_path),
            destination=str(destination_path),
            profile=sanitization_options.profile,
            changes=sanitization_changes,
        )

    def _validate_destination(
        self,
        source_path: Path,
        destination_path: Path,
        sanitization_options: SanitizationOptions,
    ) -> None:
        if source_path.resolve() == destination_path.resolve():
            raise SanitizationError("source and destination must be different paths")
        if destination_path.exists() and not sanitization_options.overwrite:
            raise SanitizationError(f"destination already exists: {destination_path}")

    def _create_temporary_output_path(self, destination_path: Path) -> Path:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_file_descriptor, temporary_file_name = tempfile.mkstemp(
            dir=destination_path.parent, prefix=f".{destination_path.name}.", suffix=".tmp"
        )
        os.close(temporary_file_descriptor)
        return Path(temporary_file_name)

    def _sanitize_to_temporary_output(
        self,
        source_path: Path,
        temporary_output_path: Path,
        sanitization_options: SanitizationOptions,
    ) -> list[SanitizationChange]:
        with pikepdf.open(source_path) as pdf_document:
            sanitization_changes = self._apply_profile(pdf_document, sanitization_options)
            pdf_document.save(temporary_output_path)
        return sanitization_changes

    def _apply_profile(
        self, pdf_document: pikepdf.Pdf, sanitization_options: SanitizationOptions
    ) -> list[SanitizationChange]:
        profile_name = sanitization_options.profile.lower()
        if profile_name not in {"privacy", "minimal", "author"}:
            raise SanitizationError(f"unknown sanitization profile: {sanitization_options.profile}")
        sanitization_changes = self._remove_document_information(pdf_document)
        sanitization_changes.extend(self._remove_xmp_metadata(pdf_document))
        if profile_name == "author":
            sanitization_changes.append(
                self._replace_author(pdf_document, sanitization_options.author)
            )
        return sanitization_changes

    def _remove_document_information(self, pdf_document: pikepdf.Pdf) -> list[SanitizationChange]:
        sanitization_changes: list[SanitizationChange] = []
        for key in list(pdf_document.docinfo.keys()):
            previous_value = str(pdf_document.docinfo[key])
            del pdf_document.docinfo[key]
            sanitization_changes.append(
                SanitizationChange(
                    key.removeprefix("/"), previous_value, None, SanitizationAction.REMOVE
                )
            )
        return sanitization_changes

    def _remove_xmp_metadata(self, pdf_document: pikepdf.Pdf) -> list[SanitizationChange]:
        if "/Metadata" not in pdf_document.Root:
            return []
        del pdf_document.Root.Metadata
        return [SanitizationChange("xmp_metadata", "present", None, SanitizationAction.REMOVE)]

    def _replace_author(self, pdf_document: pikepdf.Pdf, author: str | None) -> SanitizationChange:
        if author is None or not author.strip():
            raise SanitizationError("the author profile requires a non-empty author")
        pdf_document.docinfo["/Author"] = author
        return SanitizationChange("Author", None, author, SanitizationAction.REPLACE)

    def _validate_temporary_output(
        self, temporary_output_path: Path, should_validate_output: bool
    ) -> None:
        if not should_validate_output:
            return
        from metatool.validators.pdf import PDFValidator

        validation_result = PDFValidator().validate(temporary_output_path)
        if not validation_result.is_valid:
            raise SanitizationError(
                "output validation failed: " + "; ".join(validation_result.errors)
            )
