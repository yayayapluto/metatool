"""Safe, deterministic OOXML sanitization."""

import os
import posixpath
import tempfile
import xml.etree.ElementTree as element_tree
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from metatool.constants import (
    CONTENT_TYPES_NAMESPACE,
    CONTENT_TYPES_PART,
    CORE_NAMESPACES,
    CORE_PROPERTIES_PART,
    CUSTOM_PROPERTIES_PART,
    EXTENDED_PROPERTIES_NAMESPACE,
    EXTENDED_PROPERTIES_PART,
    MAX_ARCHIVE_MEMBERS,
    MAX_ARCHIVE_SIZE,
    MAX_COMPRESSION_RATIO,
    MAX_XML_SIZE,
    OOXML_EXTENSIONS,
    RELATIONSHIPS_NAMESPACE,
    ROOT_RELATIONSHIPS_PART,
)
from metatool.exceptions import InvalidDocumentError, SanitizationError
from metatool.models import (
    SanitizationAction,
    SanitizationChange,
    SanitizationOptions,
    SanitizationResult,
)


def _qualified_name(namespace: str, local_name: str) -> str:
    return f"{{{namespace}}}{local_name}"


def _serialize_xml(root: element_tree.Element) -> bytes:
    return element_tree.tostring(root, encoding="utf-8", xml_declaration=True)


def _relationship_source_part(relationship_part_name: str) -> str:
    if relationship_part_name == ROOT_RELATIONSHIPS_PART:
        return ""
    relationship_path = PurePosixPath(relationship_part_name)
    if relationship_path.parent.name != "_rels" or not relationship_path.name.endswith(".rels"):
        raise ValueError(f"invalid OOXML relationship part: {relationship_part_name}")
    return str(relationship_path.parent.parent / relationship_path.name.removesuffix(".rels"))


def _resolve_relationship_target(relationship_part_name: str, target: str) -> str:
    if target.startswith("/"):
        return target.removeprefix("/")
    source_part_name = _relationship_source_part(relationship_part_name)
    target_directory = posixpath.dirname(source_part_name)
    resolved_target = posixpath.normpath(posixpath.join(target_directory, target))
    if resolved_target == ".." or resolved_target.startswith("../"):
        raise ValueError(f"OOXML relationship target escapes package: {target}")
    return resolved_target.removeprefix("./")


def _validate_archive_members(package_archive: zipfile.ZipFile) -> None:
    package_members = package_archive.infolist()
    if len(package_members) > MAX_ARCHIVE_MEMBERS:
        raise InvalidDocumentError("OOXML archive contains too many members")
    uncompressed_size = sum(package_member.file_size for package_member in package_members)
    if uncompressed_size > MAX_ARCHIVE_SIZE:
        raise InvalidDocumentError("OOXML archive exceeds the uncompressed size limit")
    for package_member in package_members:
        if (
            package_member.filename.startswith("/")
            or ".." in PurePosixPath(package_member.filename).parts
        ):
            raise InvalidDocumentError("OOXML archive contains an unsafe member path")
        if (
            package_member.compress_size
            and package_member.file_size / package_member.compress_size > MAX_COMPRESSION_RATIO
        ):
            raise InvalidDocumentError("OOXML archive contains an excessive compression ratio")


@dataclass
class OOXMLPackage:
    """In-memory OOXML package with relationship-aware part removal."""

    parts: dict[str, bytes]

    @classmethod
    def read(cls, document_path: Path) -> "OOXMLPackage":
        """Read an OOXML archive after resource-limit validation."""
        try:
            with zipfile.ZipFile(document_path) as package_archive:
                _validate_archive_members(package_archive)
                parts = {
                    package_member.filename: package_archive.read(package_member)
                    for package_member in package_archive.infolist()
                }
        except zipfile.BadZipFile as exception:
            raise InvalidDocumentError(
                f"{document_path} is not a valid OOXML package"
            ) from exception
        return cls(parts=parts)

    def replace_part(self, part_name: str, document_bytes: bytes) -> None:
        """Replace a package part with supplied bytes."""
        self.parts[part_name] = document_bytes

    def remove_part(self, part_name: str) -> None:
        """Remove a part plus all relationship and content-type references."""
        self.parts.pop(part_name, None)
        self._remove_relationship_references(part_name)
        self._remove_content_type_references(part_name)

    def _remove_relationship_references(self, removed_part_name: str) -> None:
        relationship_name = _qualified_name(RELATIONSHIPS_NAMESPACE, "Relationship")
        for relationship_part_name in self._relationship_part_names():
            relationships = element_tree.fromstring(self.parts[relationship_part_name])
            for relationship in list(relationships.findall(relationship_name)):
                if relationship.get("TargetMode") == "External":
                    continue
                relationship_target = _resolve_relationship_target(
                    relationship_part_name, relationship.get("Target", "")
                )
                if relationship_target == removed_part_name:
                    relationships.remove(relationship)
            self.parts[relationship_part_name] = _serialize_xml(relationships)

    def _remove_content_type_references(self, removed_part_name: str) -> None:
        content_type_bytes = self.parts.get(CONTENT_TYPES_PART)
        if content_type_bytes is None:
            return
        content_types = element_tree.fromstring(content_type_bytes)
        override_name = _qualified_name(CONTENT_TYPES_NAMESPACE, "Override")
        expected_part_name = f"/{removed_part_name.removeprefix('/')}"
        for content_type in list(content_types.findall(override_name)):
            if content_type.get("PartName") == expected_part_name:
                content_types.remove(content_type)
        self.parts[CONTENT_TYPES_PART] = _serialize_xml(content_types)

    def validate(self) -> None:
        """Validate members, XML parts, and every internal relationship target."""
        if CONTENT_TYPES_PART not in self.parts:
            raise ValueError("OOXML package is missing [Content_Types].xml")
        for part_name, document_bytes in self.parts.items():
            if not part_name.endswith(".xml") and not part_name.endswith(".rels"):
                continue
            if len(document_bytes) > MAX_XML_SIZE:
                raise ValueError(f"OOXML XML part exceeds size limit: {part_name}")
            element_tree.fromstring(document_bytes)
        self._validate_relationship_targets()

    def _relationship_part_names(self) -> list[str]:
        return [part_name for part_name in self.parts if part_name.endswith(".rels")]

    def _validate_relationship_targets(self) -> None:
        relationship_name = _qualified_name(RELATIONSHIPS_NAMESPACE, "Relationship")
        for relationship_part_name in self._relationship_part_names():
            relationships = element_tree.fromstring(self.parts[relationship_part_name])
            for relationship in relationships.findall(relationship_name):
                if relationship.get("TargetMode") == "External":
                    continue
                target = relationship.get("Target", "")
                if not target:
                    raise ValueError(f"OOXML relationship has no target: {relationship_part_name}")
                target_part_name = _resolve_relationship_target(relationship_part_name, target)
                if target_part_name not in self.parts:
                    raise ValueError(f"OOXML relationship target is missing: {target_part_name}")

    def write(self, destination_path: Path) -> None:
        """Write members without extracting untrusted archive paths."""
        with zipfile.ZipFile(destination_path, "w", zipfile.ZIP_DEFLATED) as package_archive:
            for part_name in sorted(self.parts):
                package_archive.writestr(part_name, self.parts[part_name])


class OOXMLSanitizer:
    """Sanitize OOXML metadata without fabricating random values."""

    def supports(self, document_path: Path) -> bool:
        """Return whether a document has a supported OOXML extension."""
        return document_path.suffix.lower() in OOXML_EXTENSIONS

    def sanitize(
        self,
        source_path: Path,
        destination_path: Path,
        sanitization_options: SanitizationOptions,
    ) -> SanitizationResult:
        """Sanitize into a validated temporary file then atomically replace destination."""
        self._validate_destination(source_path, destination_path, sanitization_options)
        package = OOXMLPackage.read(source_path)
        changes = self._sanitize_package(package, sanitization_options)
        package.validate()
        self._write_validated_output(
            package, destination_path, sanitization_options.validate_output
        )
        return SanitizationResult(
            source=str(source_path),
            destination=str(destination_path),
            profile=sanitization_options.profile,
            changes=changes,
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

    def _sanitize_package(
        self, package: OOXMLPackage, sanitization_options: SanitizationOptions
    ) -> list[SanitizationChange]:
        profile_name = sanitization_options.profile.lower()
        if profile_name == "privacy":
            return self._apply_privacy_profile(package)
        if profile_name == "minimal":
            return self._apply_minimal_profile(package)
        if profile_name == "author":
            return self._apply_author_profile(package, sanitization_options.author)
        raise SanitizationError(f"unknown sanitization profile: {sanitization_options.profile}")

    def _apply_privacy_profile(self, package: OOXMLPackage) -> list[SanitizationChange]:
        changes = self._modify_core_properties(
            package, ("creator", "lastModifiedBy", "description"), None
        )
        changes.extend(self._remove_extended_properties(package, ("Company", "Manager")))
        changes.extend(self._remove_custom_properties(package))
        return changes

    def _apply_minimal_profile(self, package: OOXMLPackage) -> list[SanitizationChange]:
        changes = self._remove_all_core_properties(package)
        changes.extend(
            self._remove_extended_properties(
                package, ("Company", "Manager", "Template", "TotalTime")
            )
        )
        changes.extend(self._remove_custom_properties(package))
        return changes

    def _apply_author_profile(
        self, package: OOXMLPackage, author: str | None
    ) -> list[SanitizationChange]:
        if author is None or not author.strip():
            raise SanitizationError("the author profile requires a non-empty author")
        changes = self._modify_core_properties(
            package, ("creator", "lastModifiedBy", "description"), author
        )
        changes.extend(self._remove_extended_properties(package, ("Company", "Manager")))
        changes.extend(self._remove_custom_properties(package))
        return changes

    def _modify_core_properties(
        self, package: OOXMLPackage, property_names: tuple[str, ...], replacement: str | None
    ) -> list[SanitizationChange]:
        core_property_bytes = package.parts.get(CORE_PROPERTIES_PART)
        if core_property_bytes is None:
            return []
        core_properties = element_tree.fromstring(core_property_bytes)
        namespaces = {
            "creator": CORE_NAMESPACES["dc"],
            "lastModifiedBy": CORE_NAMESPACES["cp"],
            "description": CORE_NAMESPACES["dc"],
        }
        changes: list[SanitizationChange] = []
        for property_name in property_names:
            property_element = core_properties.find(
                _qualified_name(namespaces[property_name], property_name)
            )
            if property_element is None:
                continue
            previous_value = property_element.text
            if replacement is None:
                core_properties.remove(property_element)
                action = SanitizationAction.REMOVE
            else:
                property_element.text = replacement
                action = SanitizationAction.REPLACE
            changes.append(SanitizationChange(property_name, previous_value, replacement, action))
        package.replace_part(CORE_PROPERTIES_PART, _serialize_xml(core_properties))
        return changes

    def _remove_all_core_properties(self, package: OOXMLPackage) -> list[SanitizationChange]:
        core_property_bytes = package.parts.get(CORE_PROPERTIES_PART)
        if core_property_bytes is None:
            return []
        core_properties = element_tree.fromstring(core_property_bytes)
        changes = [
            SanitizationChange(element.tag, element.text, None, SanitizationAction.REMOVE)
            for element in list(core_properties)
        ]
        for property_element in list(core_properties):
            core_properties.remove(property_element)
        package.replace_part(CORE_PROPERTIES_PART, _serialize_xml(core_properties))
        return changes

    def _remove_extended_properties(
        self, package: OOXMLPackage, property_names: tuple[str, ...]
    ) -> list[SanitizationChange]:
        extended_property_bytes = package.parts.get(EXTENDED_PROPERTIES_PART)
        if extended_property_bytes is None:
            return []
        extended_properties = element_tree.fromstring(extended_property_bytes)
        changes: list[SanitizationChange] = []
        for property_name in property_names:
            property_element = extended_properties.find(
                _qualified_name(EXTENDED_PROPERTIES_NAMESPACE, property_name)
            )
            if property_element is None:
                continue
            changes.append(
                SanitizationChange(
                    property_name, property_element.text, None, SanitizationAction.REMOVE
                )
            )
            extended_properties.remove(property_element)
        package.replace_part(EXTENDED_PROPERTIES_PART, _serialize_xml(extended_properties))
        return changes

    def _remove_custom_properties(self, package: OOXMLPackage) -> list[SanitizationChange]:
        if CUSTOM_PROPERTIES_PART not in package.parts:
            return []
        package.remove_part(CUSTOM_PROPERTIES_PART)
        return [SanitizationChange("custom_properties", "present", None, SanitizationAction.REMOVE)]

    def _write_validated_output(
        self, package: OOXMLPackage, destination_path: Path, should_validate_output: bool
    ) -> None:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=destination_path.parent, prefix=f".{destination_path.name}.", suffix=".tmp"
        )
        os.close(descriptor)
        temporary_output_path = Path(temporary_name)
        try:
            package.write(temporary_output_path)
            if should_validate_output:
                from metatool.validators.ooxml import OOXMLValidator

                validation_result = OOXMLValidator().validate(temporary_output_path)
                if not validation_result.is_valid:
                    raise SanitizationError(
                        "output validation failed: " + "; ".join(validation_result.errors)
                    )
            os.replace(temporary_output_path, destination_path)
        except OSError as exception:
            raise SanitizationError(
                f"could not write sanitized document: {destination_path}"
            ) from exception
        finally:
            if temporary_output_path.exists():
                temporary_output_path.unlink()
