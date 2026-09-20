"""Local ATS-oriented DOCX/PDF rendering from the same immutable structured content."""

import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Literal
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

import reportlab
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate

from jobhunter_api.store import Row

FONT_PATH = Path(reportlab.__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("PackageSans", str(FONT_PATH / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("PackageSansBold", str(FONT_PATH / "VeraBd.ttf")))
HEADINGS = {
    "experience": "Experience",
    "project": "Selected projects",
    "education": "Education",
    "certification": "Certifications",
    "skill": "Technical skills",
    "achievement": "Achievements",
    "preference": "Preferences",
    "constraint": "Additional information",
}
type Kind = Literal["cv", "cover_letter"]


def paragraphs(content: Row, kind: Kind) -> list[tuple[str, str]]:
    lines = [("Title", content["name"])]
    lines.extend(("Contact", line) for line in content["contact_lines"])
    if kind == "cv":
        lines.append(("Subtitle", "Application for " + content["job_title"]))
        categories = list(dict.fromkeys(c["category"] for c in content["cv"]))
        for category in categories:
            lines.append(("Heading 1", HEADINGS[category]))
            lines.extend(("Body", c["text"]) for c in content["cv"] if c["category"] == category)
    else:
        lines.extend(
            [
                ("Subtitle", content["job_title"] + " at " + content["company_name"]),
                ("Body", "Dear Hiring Team,"),
                (
                    "Body",
                    "I am applying for the "
                    + content["job_title"]
                    + " position at "
                    + content["company_name"]
                    + ".",
                ),
                ("Body", "The following background is relevant to my application:"),
            ]
        )
        lines.extend(("Body", claim["text"]) for claim in content["cover_letter"])
        lines.extend(
            [
                (
                    "Body",
                    "I would welcome the opportunity to discuss "
                    "how this background relates to the role.",
                ),
                ("Body", "Yours faithfully,"),
                ("Body", content["name"]),
            ]
        )
    return lines


def docx_bytes(content: Row, kind: Kind) -> bytes:
    document = Document()
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.top_margin = section.bottom_margin = Mm(19)
    section.left_margin = section.right_margin = Mm(21)
    for name, size in (("Normal", 10.5), ("Title", 23), ("Subtitle", 11), ("Heading 1", 12)):
        style = document.styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_after = Pt(7)
        style.paragraph_format.line_spacing = 1.1
        # British English proofing without changing any canonical names or claims.
        rpr = style.element.get_or_add_rPr()
        language = OxmlElement("w:lang")
        language.set(qn("w:val"), "en-GB")
        rpr.append(language)
    for style, text in paragraphs(content, kind):
        p = document.add_paragraph(
            text, style=style if style not in {"Body", "Contact"} else "Normal"
        )
        p.paragraph_format.widow_control = True
        if style in {"Title", "Subtitle", "Heading 1", "Contact"}:
            p.paragraph_format.keep_with_next = True
        if style == "Contact":
            p.paragraph_format.space_after = Pt(3)
    document.core_properties.author = ""
    document.core_properties.last_modified_by = ""
    document.core_properties.title = content["job_title"]
    document.core_properties.subject = "CV" if kind == "cv" else "Cover letter"
    document.core_properties.comments = ""
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def pdf_bytes(content: Row, kind: Kind) -> bytes:
    stream = BytesIO()
    styles = {
        "Title": ParagraphStyle(
            "Title",
            fontName="PackageSansBold",
            fontSize=23,
            leading=28,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "Subtitle": ParagraphStyle(
            "Subtitle",
            fontName="PackageSans",
            fontSize=11,
            leading=15,
            spaceAfter=14,
            keepWithNext=True,
        ),
        "Heading 1": ParagraphStyle(
            "Heading",
            fontName="PackageSansBold",
            fontSize=12,
            leading=16,
            spaceBefore=9,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "Body": ParagraphStyle(
            "Body",
            fontName="PackageSans",
            fontSize=10.5,
            leading=15,
            spaceAfter=9,
            textColor=colors.black,
            splitLongWords=True,
        ),
        "Contact": ParagraphStyle(
            "Contact",
            fontName="PackageSans",
            fontSize=10,
            leading=13,
            spaceAfter=3,
            keepWithNext=True,
        ),
    }
    story: list[Flowable] = [
        Paragraph(escape(text).replace("\n", "<br/>"), styles[style])
        for style, text in paragraphs(content, kind)
    ]
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=59.5,
        rightMargin=59.5,
        topMargin=54,
        bottomMargin=54,
        title=content["job_title"],
        author="",
        invariant=1,
    )
    document.build(story)
    return stream.getvalue()


def json_bytes(data: Row) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def artifact(package: Row, filename: str) -> tuple[bytes, str]:
    content = package["content"]
    if filename == "package.json":
        exported = {k: package[k] for k in ("id", "version", "status", "content_hash", "content")}
        exported["provenance"] = {
            "profile_version": package["snapshot"]["profile"]["version"],
            "job_version": package["snapshot"]["job"]["version"],
            "template_version": content["template_version"],
        }
        return json_bytes(exported), "application/json"
    if filename == "answers.json":
        return json_bytes({"language": "en-GB", "answers": content["answers"]}), "application/json"
    formats: list[tuple[str, Kind]] = [("cv", "cv"), ("cover-letter", "cover_letter")]
    for stem, kind in formats:
        if filename == stem + ".docx":
            return docx_bytes(
                content, kind
            ), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if filename == stem + ".pdf":
            return pdf_bytes(content, kind), "application/pdf"
    if filename == "bundle.zip":
        stream = BytesIO()
        manifest: Row = {
            "package_id": package["id"],
            "version": package["version"],
            "content_hash": package["content_hash"],
            "files": {},
        }
        with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
            for name in (
                "cv.docx",
                "cv.pdf",
                "cover-letter.docx",
                "cover-letter.pdf",
                "answers.json",
                "package.json",
            ):
                payload, _ = artifact(package, name)
                archive.writestr(name, payload)
                manifest["files"][name] = hashlib.sha256(payload).hexdigest()
            archive.writestr("manifest.json", json_bytes(manifest))
        return stream.getvalue(), "application/zip"
    raise ValueError("Unsupported artifact")
