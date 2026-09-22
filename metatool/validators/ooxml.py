"""OOXML archive and metadata relationship validation."""

import xml.etree.ElementTree as element_tree
import zipfile
from pathlib import Path

from metatool.models import ValidationResult
from metatool.sanitizers.ooxml import OOXMLPackage


class OOXMLValidator:
    """Validate the structural parts of a supported OOXML package."""

    def validate(self, document_path: Path) -> ValidationResult:
        """Return structural validation errors instead of throwing for invalid documents."""
        try:
            package = OOXMLPackage.read(document_path)
            package.validate()
            return ValidationResult(path=str(document_path), is_valid=True)
        except (OSError, ValueError, zipfile.BadZipFile, element_tree.ParseError) as exception:
            return ValidationResult(
                path=str(document_path), is_valid=False, errors=[str(exception)]
            )
