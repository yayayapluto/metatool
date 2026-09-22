"""Central resource limits for untrusted PDF inputs."""

from pathlib import Path

MAX_PDF_FILE_SIZE = 100 * 1024 * 1024
MAX_XMP_STREAM_SIZE = 1 * 1024 * 1024


def exceeds_pdf_size_limit(document_path: Path) -> bool:
    """Return whether the input PDF is larger than the configured byte limit."""
    return document_path.stat().st_size > MAX_PDF_FILE_SIZE
