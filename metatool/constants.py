"""Central project constants."""

MAX_ARCHIVE_MEMBERS = 10_000
MAX_ARCHIVE_SIZE = 100 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_XML_SIZE = 10 * 1024 * 1024
OOXML_EXTENSIONS = frozenset({".docx", ".pptx", ".xlsx"})
PDF_EXTENSION = ".pdf"
JSON_SCHEMA_VERSION = 1

CORE_PROPERTIES_PART = "docProps/core.xml"
EXTENDED_PROPERTIES_PART = "docProps/app.xml"
CUSTOM_PROPERTIES_PART = "docProps/custom.xml"
ROOT_RELATIONSHIPS_PART = "_rels/.rels"
CONTENT_TYPES_PART = "[Content_Types].xml"

CORE_NAMESPACES = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
}
EXTENDED_PROPERTIES_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
)
RELATIONSHIPS_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPES_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/content-types"

CUSTOM_PROPERTIES_RELATIONSHIP_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/metadata/custom-properties"
)
