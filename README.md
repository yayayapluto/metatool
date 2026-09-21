# MetaTool

MetaTool inspects and sanitizes metadata in OOXML documents (`.docx`, `.xlsx`,
and `.pptx`) and PDFs. It reports metadata as evidence: application and library
metadata can show that a tool participated in a document's creation or
modification, but cannot prove how its content was authored.

## Install

For normal use, install in an isolated environment:

```bash
pipx install metatool
```

For development:

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
python -m pip install -e ".[dev,tui]"
```

Do not use `--break-system-packages` as a normal installation method.

## Commands

```bash
# Rich inspection output
metatool inspect report.docx

# Machine-readable inspection without Rich output mixed into stdout
metatool inspect report.docx --format json

# Inspect a directory and exclude exact directory names
metatool inspect documents --recursive --exclude results --exclude .git

# Preview deterministic privacy changes without writing an output
metatool sanitize report.docx --profile privacy --dry-run

# Create a separate validated output document
metatool sanitize report.docx --profile privacy --output report-clean.docx

# Replace identity fields explicitly
metatool sanitize report.docx --profile author --author "Jane Doe"

# Verify structural integrity after sanitization
metatool validate report-clean.docx

# Launch the optional Textual interface
metatool tui
```

Exit codes are predictable: `0` success, `1` findings exceeded `--fail-on`,
`2` invalid arguments, `3` inspection failure, `4` sanitization failure, and
`5` validation failure.

## Sanitization profiles

- `privacy` removes creator, last-modified-by, company, manager, and custom
  properties while preserving descriptive fields such as title and keywords.
- `minimal` removes optional core metadata, selected extended properties, and
  custom properties while preserving OOXML package validity.
- `author` replaces creator and last-modified-by with the required `--author`
  value, and removes company, manager, and custom properties.

Sanitization never fabricates timestamps, revision counts, author histories, or
random metadata. Outputs are written to a temporary sibling file, validated,
then atomically moved into place. The source document is never overwritten.

## Development phases

### Phase 1: correctness

The OOXML package layer performs namespace-aware XML edits, preserves unrelated
properties, removes custom-property relationships and content-type overrides,
enforces archive and custom-property-count limits, validates output, and uses
atomic writes. PDF inspection limits file and raw XMP stream sizes; PDF metadata
and XMP removal also uses validated atomic output.

### Phase 2: tests

Pytest fixtures cover metadata preservation, custom-property cleanup,
determinism, malformed OOXML XML, archive and PDF resource limits, encrypted
PDFs, PDF metadata removal, and output validation.

### Phase 3: core architecture

Immutable models, scanners, sanitizers, validators, and independently testable
rules are separated from presentation. Core modules do not import Typer, Rich,
or Textual.

### Phase 4: CLI and automation

Typer routes `inspect`, `sanitize`, `validate`, and `tui`. Rich renders
human-facing tables, panels, and sanitization diffs. JSON output is versioned
and remains pure for automation.

### Phase 5: packaging and quality

`pyproject.toml` defines package metadata, dependencies, the `metatool` console
script, Ruff, mypy, and pytest settings. GitHub Actions tests Python 3.10–3.13.

### Phase 6: TUI

The optional Textual app delegates inspection, privacy sanitization, and
validation to the same core APIs as the CLI. Each workflow runs in a worker so
the event loop remains responsive.

### Phase 7: OOXML expansion

The shared OOXML implementation selects `.docx`, `.xlsx`, and `.pptx` by
extension; all use the same package metadata parts and validation rules.

## Quality checks

```bash
pytest
ruff check .
ruff format --check .
mypy metatool
```

## Scope and limitations

MetaTool operates on file-level metadata and package relationships. It does not
alter document body content, recover authorship facts, or remove every possible
content-level artifact such as revision history embedded in document text.
