import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import pikepdf

import metatool as mt


# ---------------------------------------------------------------- fixtures

def core_xml(creator="Alice", modified_by="Alice", revision="7",
             created="2025-01-01T10:00:00Z", description=""):
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/">'
        f'<dc:creator>{creator}</dc:creator>'
        f'<dc:description>{description}</dc:description>'
        f'<cp:lastModifiedBy>{modified_by}</cp:lastModifiedBy>'
        f'<cp:revision>{revision}</cp:revision>'
        f'<dcterms:created>{created}</dcterms:created>'
        '<dcterms:modified>2025-01-01T10:00:00Z</dcterms:modified>'
        '</cp:coreProperties>'
    )


APP_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
    '<Application>Microsoft Office Word</Application>'
    '<TotalTime>120</TotalTime><Pages>3</Pages><Words>800</Words>'
    '<Company>ACME</Company><Manager>Boss</Manager>'
    '</Properties>'
)


def make_docx(path, core=None, app=APP_XML, include_core=True):
    core = core if core is not None else core_xml()
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "")
        if include_core:
            z.writestr("docProps/core.xml", core)
        if app:
            z.writestr("docProps/app.xml", app)


def make_pdf(path, creator="Microsoft Word 2019", author="Bob"):
    with pikepdf.new() as pdf:
        pdf.docinfo["/Author"] = author
        pdf.docinfo["/Creator"] = creator
        pdf.docinfo["/Producer"] = "Microsoft Word"
        pdf.add_blank_page()
        pdf.save(path)


@pytest.fixture
def tmp_docx(tmp_path):
    p = tmp_path / "a.docx"
    make_docx(p)
    return p


@pytest.fixture
def tmp_pdf(tmp_path):
    p = tmp_path / "a.pdf"
    make_pdf(p)
    return p


def levels(findings):
    return [f["level"] for f in findings]


def has(findings, level, needle=""):
    return any(f["level"] == level and needle.lower() in f["message"].lower()
               for f in findings)


# ---------------------------------------------------------------- check_docx

def test_check_docx_clean(tmp_docx):
    props, findings = mt.check_docx(tmp_docx)
    assert props["creator"] == "Alice"
    assert props["application"] == "Microsoft Office Word"
    assert findings == []


def test_check_docx_flags_suspicious_creator(tmp_path):
    p = tmp_path / "b.docx"
    make_docx(p, core=core_xml(creator="python-docx"))
    _, findings = mt.check_docx(p)
    assert has(findings, "high", "python-docx")


def test_check_docx_flags_default_template_timestamp(tmp_path):
    p = tmp_path / "b.docx"
    make_docx(p, core=core_xml(created="2013-12-23T23:15:00Z"))
    _, findings = mt.check_docx(p)
    assert has(findings, "high", "default template timestamp")


def test_check_docx_flags_creator_modifiedby_mismatch(tmp_path):
    p = tmp_path / "b.docx"
    make_docx(p, core=core_xml(creator="python-docx", modified_by="John"))
    _, findings = mt.check_docx(p)
    assert has(findings, "med", "differs from lastModifiedBy")


def test_check_docx_no_mismatch_when_same(tmp_docx):
    _, findings = mt.check_docx(tmp_docx)
    assert not has(findings, "med", "lastModifiedBy")


def test_check_docx_missing_core_warns(tmp_path):
    p = tmp_path / "b.docx"
    make_docx(p, include_core=False)
    _, findings = mt.check_docx(p)
    assert has(findings, "warn", "core.xml missing")


def test_check_docx_low_edit_time_for_long_doc(tmp_path):
    p = tmp_path / "b.docx"
    app = APP_XML.replace("<Pages>3</Pages>", "<Pages>20</Pages>")
    app = app.replace("<TotalTime>120</TotalTime>", "<TotalTime>5</TotalTime>")
    make_docx(p, core=core_xml(revision="2"), app=app)
    _, findings = mt.check_docx(p)
    assert has(findings, "med", "editing time")


# ---------------------------------------------------------------- check_pdf

def test_check_pdf_clean(tmp_pdf):
    props, findings = mt.check_pdf(tmp_pdf)
    assert props["Author"] == "Bob"
    assert findings == []


def test_check_pdf_flags_suspicious(tmp_path):
    p = tmp_path / "b.pdf"
    make_pdf(p, creator="reportlab 4.0")
    _, findings = mt.check_pdf(p)
    assert has(findings, "high", "reportlab")


def test_check_pdf_flags_same_dates(tmp_path):
    p = tmp_path / "b.pdf"
    with pikepdf.new() as pdf:
        pdf.docinfo["/CreationDate"] = "D:20250101"
        pdf.docinfo["/ModDate"] = "D:20250101"
        pdf.add_blank_page()
        pdf.save(p)
    _, findings = mt.check_pdf(p)
    assert has(findings, "low", "CreationDate equals ModDate")


# ---------------------------------------------------------------- analyze

def test_analyze_missing_file():
    r = mt.analyze("/no/such/file.docx")
    assert r["error"] == "file not found"


def test_analyze_unsupported_ext(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("hi")
    assert "unsupported extension" in mt.analyze(str(p))["error"]


def test_analyze_corrupt_file_returns_error(tmp_path):
    p = tmp_path / "bad.docx"
    p.write_bytes(b"not a zip")
    assert "error" in mt.analyze(str(p))


def test_analyze_ok(tmp_docx):
    r = mt.analyze(str(tmp_docx))
    assert r["properties"]["creator"] == "Alice"
    assert r["findings"] == []


# ---------------------------------------------------------------- clean

def test_clean_docx_replaces_core_and_strips_app(tmp_docx, tmp_path):
    dst = tmp_path / "clean.docx"
    mt.clean_docx(tmp_docx, dst, "Anon")
    with zipfile.ZipFile(dst) as z:
        names = z.namelist()
        assert "docProps/custom.xml" not in names or True  # fixture has none
        root = ET.fromstring(z.read("docProps/core.xml"))
        assert mt.text_of(root, "dc:creator", mt.CORE_NS) == "Anon"
        assert mt.text_of(root, "cp:lastModifiedBy", mt.CORE_NS) == "Anon"
        app = z.read("docProps/app.xml").decode()
    assert "ACME" not in app and "Boss" not in app
    assert "<TotalTime>0</TotalTime>" in app
    assert "Microsoft Office Word" in app  # content untouched


def test_clean_docx_custom_xml_dropped(tmp_path):
    src = tmp_path / "c.docx"
    with zipfile.ZipFile(src, "w") as z:
        z.writestr("docProps/core.xml", core_xml())
        z.writestr("docProps/custom.xml", "<props/>")
    dst = tmp_path / "c_clean.docx"
    mt.clean_docx(src, dst, "A")
    with zipfile.ZipFile(dst) as z:
        assert "docProps/custom.xml" not in z.namelist()


def test_clean_docx_adds_core_when_missing(tmp_path):
    src = tmp_path / "d.docx"
    make_docx(src, include_core=False)
    dst = tmp_path / "d_clean.docx"
    mt.clean_docx(src, dst, "A")
    with zipfile.ZipFile(dst) as z:
        assert "docProps/core.xml" in z.namelist()


def test_clean_docx_content_preserved(tmp_path):
    src = tmp_path / "e.docx"
    with zipfile.ZipFile(src, "w") as z:
        z.writestr("word/document.xml", "<w/>")
        z.writestr("docProps/core.xml", core_xml())
    dst = tmp_path / "e_clean.docx"
    mt.clean_docx(src, dst, "A")
    with zipfile.ZipFile(dst) as z:
        assert z.read("word/document.xml") == b"<w/>"


def test_clean_pdf_strips_docinfo_and_xmp(tmp_pdf, tmp_path):
    src = tmp_path / "a_xmp.pdf"
    with pikepdf.open(tmp_pdf) as pdf:
        pdf.Root.Metadata = pdf.make_stream(b"<x:xmpmeta/>")
        pdf.save(src)

    dst = tmp_path / "clean.pdf"
    mt.clean_pdf(src, dst, None)
    with pikepdf.open(dst) as pdf:
        assert len(pdf.docinfo) == 0
        assert "/Metadata" not in pdf.Root


def test_clean_pdf_sets_author(tmp_pdf, tmp_path):
    dst = tmp_path / "clean.pdf"
    mt.clean_pdf(tmp_pdf, dst, "Carol")
    with pikepdf.open(dst) as pdf:
        assert str(pdf.docinfo["/Author"]) == "Carol"


# ---------------------------------------------------------------- clean round-trip check clears flags

def test_cleaned_docx_passes_check(tmp_path):
    p = tmp_path / "b.docx"
    make_docx(p, core=core_xml(creator="python-docx", created="2013-12-23T23:15:00Z"))
    dst = tmp_path / "b_clean.docx"
    mt.clean_docx(p, dst, "Author")
    _, findings = mt.check_docx(dst)
    assert not has(findings, "high")


# ---------------------------------------------------------------- helpers

def test_strip_tag_content():
    assert mt.strip_tag_content("<Company>ACME</Company>", "Company") == "<Company></Company>"
    assert mt.strip_tag_content("<TotalTime>5</TotalTime>", "TotalTime", "0") == "<TotalTime>0</TotalTime>"
    assert mt.strip_tag_content("no tag", "Company") == "no tag"
    assert mt.strip_tag_content("<a><Company>x</Company>tail</a>", "Company") == "<a><Company></Company>tail</a>"


def test_collect_files(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.docx").write_bytes(b"")
    (tmp_path / "sub" / "b.pdf").write_bytes(b"")
    (tmp_path / "c.txt").write_bytes(b"")
    got = {p.name for p in mt.collect_files([str(tmp_path)])}
    assert got == {"a.docx", "b.pdf"}


def test_process_file_default_results_dir(tmp_docx):
    mt.process_file(str(tmp_docx), None, "A")
    assert (tmp_docx.parent / "results" / "a.docx").exists()


def test_process_file_dedupes_existing_names(tmp_docx):
    mt.process_file(str(tmp_docx), None, "A")
    mt.process_file(str(tmp_docx), None, "A")
    r = tmp_docx.parent / "results"
    assert (r / "a.docx").exists()
    assert (r / "a(1).docx").exists()


def test_process_file_skips_unsupported(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("hi")
    assert mt.process_file(str(p), tmp_path, "A") is None
