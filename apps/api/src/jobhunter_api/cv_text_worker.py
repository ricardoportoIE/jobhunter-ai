"""Extract bounded CV text in a disposable process; never execute embedded content."""

from __future__ import annotations

import io
import json
import sys
from zipfile import ZipFile

MAX_FILE = 4 * 1024 * 1024
MAX_TEXT = 50000


def extract(content: bytes, extension: str) -> str:
    if not content or len(content) > MAX_FILE:
        raise ValueError("CV_FILE_LIMIT")
    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise ValueError("CV_INVALID_FILE")
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise ValueError("CV_ENCRYPTED")
        if len(reader.pages) > 20:
            raise ValueError("CV_PAGE_LIMIT")
        parts = []
        has_text = False
        for number, page in enumerate(reader.pages, 1):
            page_text = page.extract_text() or ""
            has_text = has_text or bool(page_text.strip())
            parts.append(f"[Page {number}]\n{page_text}")
            if sum(len(part) for part in parts) > MAX_TEXT:
                raise ValueError("CV_TEXT_LIMIT")
        text = "\n\n".join(parts)
        if not has_text:
            raise ValueError("CV_NO_TEXT")
    elif extension == ".md":
        text = content.decode("utf-8-sig")
        if any(ord(char) < 32 and char not in "\n\r\t" for char in text):
            raise ValueError("CV_INVALID_FILE")
        # Markdown is source text: never render HTML, fetch links or run embedded commands.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    elif extension == ".docx":
        if not content.startswith(b"PK"):
            raise ValueError("CV_INVALID_FILE")
        with ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if (
                len(entries) > 500
                or sum(item.file_size for item in entries) > 12 * 1024 * 1024
                or any(item.file_size > 4 * 1024 * 1024 for item in entries)
                or any(item.flag_bits & 1 for item in entries)
                or any("vba" in item.filename.lower() for item in entries)
                or len({item.filename for item in entries}) != len(entries)
            ):
                raise ValueError("CV_UNSAFE_DOCUMENT")
            from lxml import etree  # type: ignore[import-untyped]

            parts = []
            names = ["word/document.xml"] + sorted(
                name
                for name in archive.namelist()
                if name.startswith(("word/header", "word/footer")) and name.endswith(".xml")
            )
            for name in names:
                xml = archive.read(name)
                if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                    raise ValueError("CV_UNSAFE_DOCUMENT")
                parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
                root = etree.fromstring(xml, parser)
                paragraphs = root.findall(
                    ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
                )
                for paragraph in paragraphs:
                    words = paragraph.findall(
                        ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
                    )
                    parts.append("".join(word.text or "" for word in words))
            text = "\n".join(parts)
    else:
        raise ValueError("CV_FORMAT")
    text = text.replace("\x00", "").strip()
    if len(text) > MAX_TEXT:
        raise ValueError("CV_TEXT_LIMIT")
    if len(text) < 30:
        raise ValueError("CV_NO_TEXT")
    return text


def main() -> None:
    if sys.platform != "win32":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    try:
        text = extract(sys.stdin.buffer.read(MAX_FILE + 1), sys.argv[1])
        print(json.dumps({"text": text}, ensure_ascii=True))
    except Exception as error:
        code = (
            str(error)
            if isinstance(error, ValueError) and str(error).startswith("CV_")
            else "CV_INVALID_FILE"
        )
        print(json.dumps({"error": code}))


if __name__ == "__main__":
    main()
