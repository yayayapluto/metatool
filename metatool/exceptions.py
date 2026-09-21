"""Domain exceptions raised by MetaTool core modules."""


class MetaToolError(Exception):
    """Base exception for MetaTool failures."""


class InvalidDocumentError(MetaToolError):
    """Raised when a document cannot be parsed safely."""


class UnsupportedFormatError(MetaToolError):
    """Raised when a document format is unsupported."""


class SanitizationError(MetaToolError):
    """Raised when sanitization cannot complete."""


class ValidationError(MetaToolError):
    """Raised when validation cannot complete."""
