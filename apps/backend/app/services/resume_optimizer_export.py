"""Private, data-only resume formatting; authorization belongs to the caller.

Neither formatter fetches URLs, writes temporary files, executes Markdown/HTML,
or embeds user/provider metadata. Both formats use the same paragraph model.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
import threading
import unicodedata
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


MAX_DRAFT_CHARACTERS = 60_000
_FONT_PATH = Path(__file__).parents[1] / "assets" / "resume-optimizer" / "NotoSansCJKsc-Regular.ttf"
_FONT_NAME = "OfferSteadyResume"
_PDF_LOCK = threading.Lock()
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_XML = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("w", _W)


class ResumeExportError(ValueError):
    """Fixed safe messages only; never attach original document content."""


@dataclass(frozen=True)
class _Paragraph:
    text: str
    kind: str


def _paragraphs(markdown: str) -> list[_Paragraph]:
    if not isinstance(markdown, str) or not markdown.strip() or len(markdown) > MAX_DRAFT_CHARACTERS:
        raise ResumeExportError("保存的简历为空或超过导出长度限制。")
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    if any(unicodedata.category(c) in {"Cs", "Cc"} and c not in "\n\t" for c in text):
        raise ResumeExportError("保存的简历包含不支持的控制字符。")
    result: list[_Paragraph] = []
    for line in text.splitlines():
        value = line.strip()
        if not value:
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", value)
        bullet = re.match(r"^(?:[-*+]\s+|[•]\s*)(.+)$", value)
        if heading:
            kind = "title" if not result and len(heading[1]) == 1 else "heading"
            value = heading[2]
        elif bullet:
            kind, value = "bullet", bullet[1]
        else:
            kind = "title" if not result and len(value) <= 100 else "body"
        # The deliberately small renderer supports emphasis but never HTML,
        # Markdown links, remote pictures, expressions, or embedded objects.
        value = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", value)
        value = value.replace("\t", "    ")
        result.append(_Paragraph(value, kind))
    if not result:
        raise ResumeExportError("保存的简历没有可导出的正文。")
    return result


def _w(parent: ET.Element, name: str, attrs: dict[str, str] | None = None) -> ET.Element:
    return ET.SubElement(parent, f"{{{_W}}}{name}", {f"{{{_W}}}{k}": v for k, v in (attrs or {}).items()})


def _xml(element: ET.Element) -> bytes:
    return ET.tostring(element, encoding="utf-8", xml_declaration=True)


def _docx(paragraphs: list[_Paragraph]) -> bytes:
    document = ET.Element(f"{{{_W}}}document")
    body = _w(document, "body")
    for item in paragraphs:
        paragraph = _w(body, "p")
        properties = _w(paragraph, "pPr")
        style = {"title": "Title", "heading": "Heading1", "bullet": "ListParagraph"}.get(item.kind, "Normal")
        _w(properties, "pStyle", {"val": style})
        if item.kind in {"title", "heading"} and len(item.text) <= 300:
            _w(properties, "keepNext")
        _w(properties, "widowControl")
        run = _w(paragraph, "r")
        value = _w(run, "t")
        value.set(f"{{{_XML}}}space", "preserve")
        value.text = ("• " if item.kind == "bullet" else "") + item.text
    section = _w(body, "sectPr")
    _w(section, "pgSz", {"w": "11906", "h": "16838"})
    _w(section, "pgMar", {"top": "1080", "right": "1080", "bottom": "1080", "left": "1080", "header": "360", "footer": "360", "gutter": "0"})

    styles = ET.Element(f"{{{_W}}}styles")
    defaults = _w(styles, "docDefaults")
    default_run = _w(_w(defaults, "rPrDefault"), "rPr")
    _w(default_run, "rFonts", {"ascii": "Arial", "hAnsi": "Arial", "eastAsia": "Noto Sans CJK SC", "cs": "Arial"})
    _w(default_run, "sz", {"val": "21"})
    _w(default_run, "color", {"val": "000000"})
    for key, size, before, after in (("Normal", 21, 0, 90), ("Title", 40, 0, 180), ("Heading1", 24, 180, 90), ("ListParagraph", 21, 0, 65)):
        style = _w(styles, "style", {"type": "paragraph", "styleId": key})
        if key == "Normal":
            style.set(f"{{{_W}}}default", "1")
        _w(style, "name", {"val": key})
        if key != "Normal":
            _w(style, "basedOn", {"val": "Normal"})
        pp = _w(style, "pPr")
        _w(pp, "spacing", {"before": str(before), "after": str(after), "line": "290", "lineRule": "auto"})
        if key == "Heading1":
            _w(pp, "outlineLvl", {"val": "0"})
        if key == "ListParagraph":
            _w(pp, "ind", {"left": "220", "hanging": "180"})
        rp = _w(style, "rPr")
        _w(rp, "rFonts", {"ascii": "Arial", "hAnsi": "Arial", "eastAsia": "Noto Sans CJK SC", "cs": "Arial"})
        _w(rp, "sz", {"val": str(size)})
        _w(rp, "color", {"val": "000000"})
        if key in {"Title", "Heading1"}:
            _w(rp, "b")

    content_types = b'''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
    root_rels = b'''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
    doc_rels = b'''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'''
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, data in {"[Content_Types].xml": content_types, "_rels/.rels": root_rels, "word/document.xml": _xml(document), "word/styles.xml": _xml(styles), "word/_rels/document.xml.rels": doc_rels}.items():
            archive.writestr(name, data)
    return output.getvalue()


def _pdf(paragraphs: list[_Paragraph]) -> bytes:
    # Lazy imports keep fonts/formatting out of login and live-interview paths.
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate

    # ReportLab's dynamic font state must not be shared by concurrent renders.
    # Bound this CPU work without waiting indefinitely behind other exports.
    if not _PDF_LOCK.acquire(timeout=2):
        raise ResumeExportError("另一个PDF正在生成，请稍后重试。")
    try:
        if _FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            if not _FONT_PATH.is_file():
                raise ResumeExportError("PDF导出暂不可用，请稍后重试。")
            pdfmetrics.registerFont(TTFont(_FONT_NAME, str(_FONT_PATH)))
        covered = pdfmetrics.getFont(_FONT_NAME).face.charToGlyph
        if any(ord(c) not in covered for p in paragraphs for c in p.text):
            raise ResumeExportError("部分字符无法在PDF中显示，请改用Word或编辑这些字符后重试。")
        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=A4, leftMargin=54, rightMargin=54, topMargin=48, bottomMargin=48, title="Resume", author="", creator="", subject="", pageCompression=1)
        story = []
        for p in paragraphs:
            title, heading, bullet = p.kind == "title", p.kind == "heading", p.kind == "bullet"
            style = ParagraphStyle("Resume", fontName=_FONT_NAME, fontSize=20 if title else 12 if heading else 10.5, leading=26 if title else 17 if heading else 15, alignment=TA_LEFT, textColor=colors.black, spaceBefore=11 if heading else 0, spaceAfter=10 if title else 6 if heading else 4, leftIndent=12 if bullet else 0, firstLineIndent=-10 if bullet else 0, keepWithNext=(title or heading) and len(p.text) <= 300, splitLongWords=True, wordWrap="CJK" if any(ord(c) >= 0x2E80 for c in p.text) else None)
            story.append(Paragraph(("• " if bullet else "") + escape(p.text), style))
        document.build(story)
        return output.getvalue()
    finally:
        _PDF_LOCK.release()


def render_resume_export(markdown: str, format: str) -> tuple[bytes, str, str]:
    """Render the caller-authorized saved draft; no I/O beyond bundled fonts."""
    if format not in {"docx", "pdf"}:
        raise ResumeExportError("请选择Word或PDF格式导出简历。")
    paragraphs = _paragraphs(markdown)
    if format == "docx":
        return _docx(paragraphs), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "优化后简历.docx"
    return _pdf(paragraphs), "application/pdf", "优化后简历.pdf"
