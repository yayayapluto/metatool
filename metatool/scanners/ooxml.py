"""OOXML metadata inspection."""

import xml.etree.ElementTree as element_tree
from pathlib import Path

from metatool.constants import (
    CORE_NAMESPACES,
    CORE_PROPERTIES_PART,
    CUSTOM_PROPERTIES_PART,
    EXTENDED_PROPERTIES_NAMESPACE,
    EXTENDED_PROPERTIES_PART,
    OOXML_EXTENSIONS,
)
from metatool.exceptions import InvalidDocumentError, UnsupportedFormatError
from metatool.models import InspectionResult, MetadataValue
from metatool.rules.ooxml import OOXMLMetadataRules
from metatool.sanitizers.ooxml import OOXMLPackage

MAX_CUSTOM_PROPERTIES = 1_000
CUSTOM_PROPERTIES_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
)


class OOXMLScanner:
    """Extract normalized OOXML metadata from DOCX, XLSX, and PPTX packages."""

    def supports(self, document_path: Path) -> bool:
        """Return whether a document has a supported OOXML extension."""
        return document_path.suffix.lower() in OOXML_EXTENSIONS

    def inspect(self, document_path: Path) -> InspectionResult:
        """Inspect package properties without modifying the input document."""
        if not self.supports(document_path):
            raise UnsupportedFormatError(f"unsupported OOXML format: {document_path.suffix}")
        package = OOXMLPackage.read(document_path)
        metadata, warnings = self._extract_metadata(package)
        return InspectionResult(
            path=str(document_path),
            file_format=document_path.suffix.lower().removeprefix("."),
            metadata=metadata,
            findings=OOXMLMetadataRules().evaluate(metadata),
            warnings=warnings,
        )

    def _extract_metadata(
        self, package: OOXMLPackage
    ) -> tuple[dict[str, MetadataValue], list[str]]:
        metadata: dict[str, MetadataValue] = {
            "has_custom_properties": CUSTOM_PROPERTIES_PART in package.parts,
        }
        warnings: list[str] = []
        self._validate_custom_property_count(package)
        self._extract_core_properties(package, metadata, warnings)
        self._extract_extended_properties(package, metadata, warnings)
        return metadata, warnings

    def _validate_custom_property_count(self, package: OOXMLPackage) -> None:
        custom_property_bytes = package.parts.get(CUSTOM_PROPERTIES_PART)
        if custom_property_bytes is None:
            return
        custom_properties = _parse_xml(CUSTOM_PROPERTIES_PART, custom_property_bytes)
        property_name = f"{{{CUSTOM_PROPERTIES_NAMESPACE}}}property"
        if len(custom_properties.findall(property_name)) > MAX_CUSTOM_PROPERTIES:
            raise InvalidDocumentError("OOXML custom property count exceeds the configured limit")

    def _extract_core_properties(
        self, package: OOXMLPackage, metadata: dict[str, MetadataValue], warnings: list[str]
    ) -> None:
        core_property_bytes = package.parts.get(CORE_PROPERTIES_PART)
        if core_property_bytes is None:
            warnings.append("docProps/core.xml is missing")
            return
        core_properties = _parse_xml(CORE_PROPERTIES_PART, core_property_bytes)
        property_names = {
            "title": (CORE_NAMESPACES["dc"], "title"),
            "subject": (CORE_NAMESPACES["dc"], "subject"),
            "creator": (CORE_NAMESPACES["dc"], "creator"),
            "keywords": (CORE_NAMESPACES["cp"], "keywords"),
            "description": (CORE_NAMESPACES["dc"], "description"),
            "last_modified_by": (CORE_NAMESPACES["cp"], "lastModifiedBy"),
            "revision": (CORE_NAMESPACES["cp"], "revision"),
            "created": (CORE_NAMESPACES["dcterms"], "created"),
            "modified": (CORE_NAMESPACES["dcterms"], "modified"),
            "category": (CORE_NAMESPACES["cp"], "category"),
        }
        for field_name, (namespace, property_name) in property_names.items():
            property_element = core_properties.find(f"{{{namespace}}}{property_name}")
            if property_element is not None and property_element.text:
                metadata[field_name] = property_element.text

    def _extract_extended_properties(
        self, package: OOXMLPackage, metadata: dict[str, MetadataValue], warnings: list[str]
    ) -> None:
        extended_property_bytes = package.parts.get(EXTENDED_PROPERTIES_PART)
        if extended_property_bytes is None:
            warnings.append("docProps/app.xml is missing")
            return
        extended_properties = _parse_xml(EXTENDED_PROPERTIES_PART, extended_property_bytes)
        property_names = {
            "application": "Application",
            "company": "Company",
            "manager": "Manager",
            "template": "Template",
            "total_time": "TotalTime",
            "pages": "Pages",
            "words": "Words",
        }
        for field_name, property_name in property_names.items():
            property_element = extended_properties.find(
                f"{{{EXTENDED_PROPERTIES_NAMESPACE}}}{property_name}"
            )
            if property_element is not None and property_element.text:
                metadata[field_name] = property_element.text


def _parse_xml(part_name: str, document_bytes: bytes) -> element_tree.Element:
    try:
        return element_tree.fromstring(document_bytes)
    except element_tree.ParseError as exception:
        raise InvalidDocumentError(f"invalid XML in {part_name}") from exception
