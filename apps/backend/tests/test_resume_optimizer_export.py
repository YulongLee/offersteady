from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from app.services.resume_optimizer_export import ResumeExportError, render_resume_export


SYNTHETIC_RESUME = """# Jordan Élodie 王小明 山田 한글
jordan.synthetic@example.test | https://example.test/portfolio

## Experience
**Backend Engineer** | Example Synthetic Labs | 2023–2025
- Reduced scheduled job duration by 28% with Python and PostgreSQL.
- Built request tracing for 12 internal services; retained 99.95% availability.

## Education
BSc Computer Science | Synthetic University | 2023

## Skills
Python, PostgreSQL, React, English and 中文
"""


def test_docx_is_real_ooxml_and_contains_all_saved_content_without_external_assets():
    data, mime, name = render_resume_export(SYNTHETIC_RESUME, "docx")
    assert data.startswith(b"PK") and name.endswith(".docx")
    assert mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    with ZipFile(BytesIO(data)) as archive:
        assert "word/document.xml" in archive.namelist()
        for path in archive.namelist():
            ET.fromstring(archive.read(path))
        document = ET.fromstring(archive.read("word/document.xml"))
        text = "\n".join(e.text or "" for e in document.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
        for expected in ("王小明", "한글", "28%", "99.95%", "2023–2025", "Python, PostgreSQL, React, English and 中文"):
            assert expected in text
        assert "**" not in text
        assert b"TargetMode=\"External\"" not in b"".join(archive.read(p) for p in archive.namelist())


def test_pdf_is_real_embedded_unicode_text_and_keeps_contacts_numbers_and_last_section():
    from pypdf import PdfReader
    data, mime, name = render_resume_export(SYNTHETIC_RESUME, "pdf")
    assert data.startswith(b"%PDF-") and mime == "application/pdf" and name.endswith(".pdf")
    reader = PdfReader(BytesIO(data))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    for expected in ("Élodie", "王小明", "山田", "한글", "28%", "99.95%", "2023–2025", "中文", "jordan.synthetic@example.test"):
        assert expected in text
    assert "/JavaScript" not in reader.trailer["/Root"]
    fonts = reader.pages[0]["/Resources"]["/Font"]
    assert any("/FontFile2" in f.get_object().get("/FontDescriptor", {}) for f in fonts.values())


def test_long_pdf_and_docx_keep_final_marker_and_every_bullet():
    from pypdf import PdfReader
    source = "# Synthetic Long Resume\n\n" + "\n\n".join(
        f"## Project {n}\n- Delivered component {n} with Python and PostgreSQL. " + "Responsible for durable retries and clear ownership. " * 5
        for n in range(18)
    ) + "\n\n## FINAL CONTENT MARKER\nComplete resume ends here."
    pdf = PdfReader(BytesIO(render_resume_export(source, "pdf")[0]))
    assert 2 <= len(pdf.pages) <= 8
    all_text = "\n".join(p.extract_text() for p in pdf.pages)
    assert "Complete resume ends here." in all_text
    assert all(f"Project {n}" in all_text for n in range(18))
    with ZipFile(BytesIO(render_resume_export(source, "docx")[0])) as archive:
        assert b"Complete resume ends here." in archive.read("word/document.xml")


@pytest.mark.parametrize("text", ["", "  \n", "x" * 60_001, "source\x00text", "source\ud800text"])
def test_invalid_draft_rejected_without_echoing_input(text):
    with pytest.raises(ResumeExportError) as error:
        render_resume_export(text, "docx")
    if text.strip():
        assert text not in str(error.value)


def test_unsupported_pdf_characters_fail_clearly_instead_of_missing_glyphs():
    with pytest.raises(ResumeExportError, match="部分字符"):
        render_resume_export("# Synthetic Resume\nUnsupported emoji 🧑‍💻", "pdf")


def test_literal_markup_never_becomes_active_document_content():
    text = '# Synthetic Resume\n<script src="https://example.test/private"></script>\nA < B & C'
    data = render_resume_export(text, "docx")[0]
    with ZipFile(BytesIO(data)) as archive:
        xml = archive.read("word/document.xml")
        assert b"&lt;script" in xml and b"&amp;" in xml
        assert not any(p.endswith((".html", ".js")) for p in archive.namelist())


def test_only_approved_export_formats():
    with pytest.raises(ResumeExportError):
        render_resume_export(SYNTHETIC_RESUME, "html")
