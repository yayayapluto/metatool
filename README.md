# MetaTool

MetaTool is a command-line utility for inspecting, sanitizing, and validating
metadata in OOXML documents and PDF files. It reports metadata as evidence: a
creator, application, or producer value can indicate that a tool participated
in a document's creation or modification, but it cannot prove who authored the
document's content.

## Contents

- [What it does](#what-it-does)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Commands](#commands)
- [Sanitization profiles](#sanitization-profiles)
- [Supported formats](#supported-formats)
- [Safety and privacy](#safety-and-privacy)
- [Automation](#automation)
- [Development](#development)
- [Limitations](#limitations)

## What it does

- Inspects DOCX, XLSX, PPTX, and PDF metadata.
- Reports structured findings with human-readable Rich output or JSON.
- Removes privacy-sensitive metadata deterministically.
- Preserves unrelated metadata whenever the selected profile allows it.
- Validates sanitized documents before they are moved into place.
- Provides an optional Textual terminal interface.

## Installation

Run these commands from the repository root. Installing with `.` is important:
it selects this checkout instead of a similarly named package from the public
Python Package Index.

### Isolated command-line installation

```powershell
pipx install .
```

To include the optional terminal interface:

```powershell
pipx install ".[tui]"
```

### Development installation

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,tui]"
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev,tui]"
```

Do not use `--break-system-packages` for normal installation. If an old
installation was created from the public package index, remove it first:

```powershell
pipx uninstall metatool
pipx install .
```

## Quick start

```powershell
# Inspect a document with human-readable output
metatool inspect report.docx

# Preview privacy changes without creating an output file
metatool sanitize report.docx --profile privacy --dry-run

# Create a separate, validated sanitized document
metatool sanitize report.docx --profile privacy --output report-clean.docx

# Confirm the resulting document is structurally valid
metatool validate report-clean.docx
```

The source file is never silently overwritten. By default, sanitization writes
`<name>-clean<extension>` beside the source document.

## Commands

### `inspect`

Inspect one or more files or directories.

```powershell
metatool inspect report.docx notes.pdf
metatool inspect documents --recursive
metatool inspect documents --recursive --exclude results --exclude .git
```

Options:

- `--recursive` scans nested directories.
- `--exclude NAME` skips directories whose exact name matches `NAME`.
- `--format table` renders Rich output (the default).
- `--format json` emits machine-readable JSON without presentation output.
- `--fail-on info|notice|suspicious` exits with code `1` when that severity is found.
- `--quiet` disables interactive progress output.

### `sanitize`

Sanitize one or more supported documents.

```powershell
metatool sanitize report.docx --profile privacy
metatool sanitize report.docx --profile minimal --output clean.docx
metatool sanitize report.docx --profile author --author "Jane Doe"
metatool sanitize report.docx --profile privacy --dry-run
```

`--dry-run` calculates and displays the metadata diff without writing the
destination file. Use `--output` when an explicit destination is required.

### `validate`

Reopen a document and check its package or PDF structure.

```powershell
metatool validate report-clean.docx
metatool validate report-clean.pdf
```

### `tui`

Launch the optional Textual interface:

```powershell
metatool tui
```

The interface uses the same inspection, sanitization, and validation services as
the CLI.

## Sanitization profiles

| Profile | Behavior |
| --- | --- |
| `privacy` | Removes identity-related fields, application metadata, company/manager values, custom properties, and the description field while preserving descriptive fields such as title and keywords. |
| `minimal` | Removes optional metadata, including application and description metadata, while preserving package validity. |
| `author` | Replaces creator and last-modified-by with `--author`, then removes application, description, company, manager, and custom properties. |

Sanitization is deterministic. MetaTool does not invent timestamps, revision
counts, author histories, or random replacement values.

## Supported formats

| Format | Inspection | Sanitization | Validation |
| --- | :---: | :---: | :---: |
| DOCX | Yes | Yes | Yes |
| XLSX | Yes | Yes | Yes |
| PPTX | Yes | Yes | Yes |
| PDF | Yes | Yes | Yes |

OOXML formats share one package implementation for core, application, custom
properties, relationships, and content-type declarations.

## Safety and privacy

Inputs are treated as untrusted files.

- OOXML archive size, entry count, uncompressed size, compression ratio, XML
  size, and custom-property count are bounded.
- PDF file size and raw XMP stream size are bounded.
- Encrypted, malformed, or structurally invalid inputs produce controlled
  errors instead of normal-operation stack traces.
- Sanitization writes to a temporary sibling, validates the result, and then
  performs an atomic move.
- Package relationships and content-type declarations are updated when OOXML
  parts are removed.

These protections reduce parser and archive abuse risk; they do not make an
untrusted document safe to open in a vulnerable desktop application.

## Automation

JSON output is intended for scripts and CI:

```powershell
metatool inspect report.docx --format json > inspection.json
```

Rich progress and presentation output are kept out of JSON mode. Exit codes:

| Code | Meaning |
| ---: | --- |
| `0` | Operation completed successfully. |
| `1` | Findings exceeded the requested threshold. |
| `2` | Invalid arguments or unsupported input selection. |
| `3` | Inspection or parsing failure. |
| `4` | Sanitization failure. |
| `5` | Validation failure. |

## Development

Install the development extras, then run the quality gates from the repository
root:

```powershell
python -m pytest -q
ruff check .
ruff format --check .
mypy metatool
```

The project keeps core document processing independent from Typer, Rich, and
Textual presentation layers. The GitHub Actions workflow exercises the
supported Python versions and the same quality checks.

## Limitations

MetaTool operates on file-level metadata and package relationships. It does not
alter document body content, recover authorship facts, or remove every possible
content-level artifact such as revision history embedded in document text.
