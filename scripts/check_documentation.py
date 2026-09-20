"""Check authored Markdown for local links and common en-GB language regressions."""

from __future__ import annotations

import argparse
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PRESERVED = {".private"}
PORTUGUESE = re.compile(
    r"\b(?:não|são|também|através|após|ainda|somente|nenhum|nenhuma|"
    r"utilizador(?:es)?|usuário(?:s)?|relatório(?:s)?|documentação|"
    r"verificação|validação|concluído|concluída|evidências|requisitos|"
    r"orçamento|candidatura(?:s)?|desconhecido|desconhecida|"
    r"fase|fases|arquivo(?:s)?|próximo|próxima|\w+ções|\w+ção)\b",
    re.IGNORECASE,
)
US_SPELLINGS = {
    "analyze": "analyse",
    "analyzed": "analysed",
    "analyzing": "analysing",
    "artifact": "artefact",
    "artifacts": "artefacts",
    "authorization": "authorisation",
    "authorize": "authorise",
    "authorized": "authorised",
    "unauthorized": "unauthorised",
    "behavior": "behaviour",
    "behaviors": "behaviours",
    "catalog": "catalogue",
    "catalogs": "catalogues",
    "center": "centre",
    "centers": "centres",
    "color": "colour",
    "colors": "colours",
    "colored": "coloured",
    "enrollment": "enrolment",
    "fulfillment": "fulfilment",
    "initialize": "initialise",
    "initialized": "initialised",
    "initialization": "initialisation",
    "initializer": "initialiser",
    "normalize": "normalise",
    "normalized": "normalised",
    "normalization": "normalisation",
    "normalizer": "normaliser",
    "organization": "organisation",
    "organize": "organise",
    "organized": "organised",
    "prioritize": "prioritise",
    "prioritized": "prioritised",
    "prioritization": "prioritisation",
    "prioritizing": "prioritising",
    "sanitize": "sanitise",
    "sanitized": "sanitised",
    "sanitization": "sanitisation",
    "serialize": "serialise",
    "serialized": "serialised",
    "serialization": "serialisation",
    "anonymized": "anonymised",
    "anonymization": "anonymisation",
    "minimize": "minimise",
    "minimized": "minimised",
    "minimization": "minimisation",
    "favorable": "favourable",
    "unfavorable": "unfavourable",
    "afterward": "afterwards",
}
US_WORD = re.compile(r"\b(?:" + "|".join(US_SPELLINGS) + r")\b", re.IGNORECASE)
INLINE_CODE = re.compile(r"(`+).*?\1")
INLINE_LINK = re.compile(
    r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[\"'][^\n]*?[\"'])?\s*\)"
)
REFERENCE = re.compile(r"^ {0,3}\[([^\]]+)\]:\s*(<[^>]+>|\S+)")
REFERENCE_USE = re.compile(r"!?\[([^\]\n]+)\]\[([^\]\n]*)\]")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})([^\n]*)$")


def authored_paths(private: bool) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths = {
        ROOT / name
        for raw in result.stdout.split(b"\0")
        if raw
        and (name := raw.decode("utf-8")).lower().endswith(".md")
        and Path(name).parts[0] not in PRESERVED
        and (ROOT / name).is_file()
    }
    if private:
        paths.update((ROOT / ".private/review").rglob("*.md"))
    return sorted(paths)


def markdown_lines(text: str) -> tuple[list[tuple[int, str, bool]], int | None]:
    """Retain prose/text diagrams; mark executable fences for exclusion."""
    result = []
    fence: str | None = None
    start: int | None = None
    language = ""
    for number, line in enumerate(text.splitlines(), 1):
        marker = FENCE.match(line)
        if marker and fence is None:
            fence, language = marker[1], marker[2].strip().lower()
            start = number
            continue
        if (
            marker
            and fence
            and marker[1][0] == fence[0]
            and len(marker[1]) >= len(fence)
            and not marker[2].strip()
        ):
            fence, start = None, None
            continue
        if fence is None or language in {"text", "mermaid"}:
            result.append((number, line, fence is not None))
    return result, start


def heading_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    for _, line, in_fence in markdown_lines(text)[0]:
        heading = re.match(r"^ {0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$", line)
        if not heading or in_fence:
            continue
        title = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", heading[1]).lower()
        title = title.replace("`", "")
        slug = "".join(
            char
            for char in title
            if char in "-_ " or unicodedata.category(char)[0] in {"L", "N"}
        ).replace(" ", "-")
        candidate, suffix = slug, 0
        while candidate in anchors:
            suffix += 1
            candidate = f"{slug}-{suffix}"
        anchors.add(candidate)
    return anchors


def link_error(path: Path, target: str) -> str | None:
    target = target.strip("<>")
    try:
        url = urlsplit(target)
    except ValueError:
        return "invalid link target"
    if url.scheme or url.netloc:
        return None
    destination = (path.parent / unquote(url.path)).resolve() if url.path else path
    if not destination.exists():
        return "local link target does not exist"
    if url.fragment and destination.suffix.lower() == ".md":
        try:
            anchors = heading_anchors(destination.read_text(encoding="utf-8"))
        except UnicodeError:
            return "linked Markdown is not valid UTF-8"
        if unquote(url.fragment) not in anchors:
            return "local Markdown heading anchor does not exist"
    return None


def check_file(path: Path) -> list[tuple[int, str]]:
    """Return locations and safe diagnostics, without exposing document content."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError:
        return [(1, "document is not valid UTF-8")]
    errors = []
    if text.startswith("\ufeff"):
        errors.append((1, "remove the UTF-8 byte-order mark"))
    lines, unclosed = markdown_lines(text)
    if unclosed:
        errors.append((unclosed, "unclosed fenced block"))
    references = {}
    for _, line, in_fence in lines:
        definition = REFERENCE.match(line)
        if definition and not in_fence:
            references[definition[1].casefold()] = definition[2]
    for number, raw in enumerate(text.splitlines(), 1):
        if "\ufffd" in raw:
            errors.append((number, "Unicode replacement character"))
    for number, line, in_fence in lines:
        prose = INLINE_CODE.sub("", line)
        definition = REFERENCE.match(prose) if not in_fence else None
        if not in_fence:
            targets = [match[1] for match in INLINE_LINK.finditer(prose)]
            if definition:
                targets.append(definition[2])
            for reference in REFERENCE_USE.finditer(prose):
                key = (reference[2] or reference[1]).casefold()
                if key not in references:
                    errors.append((number, "undefined reference link"))
            for target in targets:
                error = link_error(path, target)
                if error:
                    errors.append((number, error))
        prose = INLINE_LINK.sub(lambda match: match[0].split("](", 1)[0] + "]", prose)
        if definition:
            prose = ""
        prose = re.sub(r"(?:https?://|mailto:)\S+", "", prose)
        if PORTUGUESE.search(prose):
            errors.append(
                (number, "possible Portuguese prose; review in British English")
            )
        for match in US_WORD.finditer(prose):
            replacement = US_SPELLINGS[match[0].lower()]
            errors.append((number, f"prefer British spelling: {replacement}"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--private",
        action="store_true",
        help="Include authored .private/review Markdown",
    )
    args = parser.parse_args()
    paths = authored_paths(args.private)
    failures = 0
    for path in paths:
        for line, message in check_file(path):
            print(f"{path.relative_to(ROOT).as_posix()}:{line}: {message}")
            failures += 1
    if failures:
        print(f"FAIL: {failures} documentation issues across {len(paths)} files.")
        return 1
    print(
        f"PASS: {len(paths)} authored Markdown files; language, encoding, fences and local links."
    )
    print(
        "Editorial review is still required; original evidence and executable examples are preserved."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
