"""Shared immutable domain models."""

from dataclasses import dataclass, field
from enum import Enum

MetadataValue = str | int | float | bool | None


class Severity(str, Enum):
    """Evidence-oriented finding severity."""

    INFO = "info"
    NOTICE = "notice"
    SUSPICIOUS = "suspicious"


class SanitizationAction(str, Enum):
    """Explicit mutation actions reported by sanitizers."""

    PRESERVE = "preserve"
    REMOVE = "remove"
    REPLACE = "replace"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    field: str | None = None
    value: str | None = None
    interpretation: str | None = None


@dataclass(frozen=True)
class InspectionResult:
    path: str
    file_format: str
    metadata: dict[str, MetadataValue]
    findings: list[Finding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SanitizationChange:
    field: str
    previous_value: object
    new_value: object
    action: SanitizationAction


@dataclass(frozen=True)
class SanitizationOptions:
    profile: str = "privacy"
    author: str | None = None
    overwrite: bool = False
    validate_output: bool = True


@dataclass(frozen=True)
class SanitizationResult:
    source: str
    destination: str
    profile: str
    changes: list[SanitizationChange] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ValidationResult:
    path: str
    is_valid: bool
    errors: list[str] = field(default_factory=list)
