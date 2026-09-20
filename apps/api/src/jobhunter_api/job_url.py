"""Public vacancy reads with pinned DNS, bounded content and no browser execution."""

from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import Field

from jobhunter_api.auth import Actor, settings_for
from jobhunter_api.errors import Problem
from jobhunter_api.job_parser import ApplyDraft, apply_draft, get_provider, parse_vacancy
from jobhunter_api.jobs import JobImport, import_job
from jobhunter_api.profile import Input
from jobhunter_api.records import get_record
from jobhunter_api.store import Row, connect

router = APIRouter(prefix="/api/v1/jobs", tags=["job URL import"])
AGENT = "JobHunterAI/1.0"
MAX_BYTES = 2 * 1024 * 1024


def public_target(url: str) -> tuple[str, str, list[str]]:
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        if (
            parsed.scheme != "https"
            or parsed.port not in {None, 443}
            or parsed.username
            or parsed.password
            or not host
            or len(url) > 2000
            or any(ord(char) < 33 or char == "\\" for char in url)
            or host == "linkedin.com"
            or host.endswith(".linkedin.com")
            or "%" in host
            or "." not in host
        ):
            raise ValueError("Invalid URL")
        addresses = sorted(
            {str(item[4][0]) for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        )
        if not addresses or any(not safe_address(address) for address in addresses):
            raise ValueError("Non-public destination")
        path = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        return host, path, addresses
    except (ValueError, UnicodeError, OSError):
        raise Problem(
            422,
            "URL_NOT_ALLOWED",
            "Use a public HTTPS vacancy URL without credentials or a custom port. "
            "Private addresses and automated LinkedIn access are not supported.",
        ) from None


def safe_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    blocked = ["64:ff9b::/96", "64:ff9b:1::/48", "2002::/16", "2001::/32", "::ffff:0:0/96"]
    return (
        address.is_global
        and not address.is_multicast
        and not address.is_reserved
        and not any(address in ipaddress.ip_network(network) for network in blocked)
    )


def request_page(url: str, deadline: float) -> tuple[int, dict[str, str], bytes]:
    host, path, addresses = public_target(url)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise Problem(
            422, "URL_TIMEOUT", "The website took too long. Paste the advert text instead."
        )
    connection = http.client.HTTPSConnection(host, timeout=min(remaining, 8))
    raw: socket.socket | None = None
    try:
        # Connect to the validated address, retaining the hostname for TLS and Host.
        raw = socket.create_connection((addresses[0], 443), timeout=min(remaining, 8))
        connection.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        connection.request(
            "GET",
            path,
            headers={
                "Host": host,
                "User-Agent": AGENT,
                "Accept": "text/html,application/xhtml+xml,text/plain",
                "Accept-Encoding": "identity",
            },
        )
        response = connection.getresponse()
        headers = {key.lower(): value for key, value in response.getheaders()}
        if headers.get("content-encoding", "identity").lower() not in {"identity", ""}:
            raise Problem(
                422,
                "URL_CONTENT_UNSUPPORTED",
                "The website returned unsupported compressed content. Paste the text instead.",
            )
        chunks = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            if connection.sock:
                connection.sock.settimeout(min(remaining, 8))
            chunk = response.read1(min(65536, MAX_BYTES + 1 - len(chunks)))
            if not chunk:
                break
            chunks.extend(chunk)
            if len(chunks) > MAX_BYTES:
                raise Problem(
                    422,
                    "URL_CONTENT_LIMIT",
                    "The page is too large. Paste only the vacancy text instead.",
                )
        return response.status, headers, bytes(chunks)
    except (OSError, http.client.HTTPException, UnicodeError):
        raise Problem(
            422,
            "URL_FETCH_FAILED",
            "The public page could not be read. Paste the vacancy text instead.",
        ) from None
    finally:
        connection.close()
        if raw:
            raw.close()


def redirects(url: str, deadline: float) -> tuple[str, int, dict[str, str], bytes]:
    for _ in range(4):
        status, headers, content = request_page(url, deadline)
        if status not in {301, 302, 303, 307, 308}:
            return url, status, headers, content
        if not headers.get("location"):
            break
        url = urljoin(url, headers["location"])
    raise Problem(
        422, "URL_REDIRECT_LIMIT", "The page has too many redirects. Use the final vacancy URL."
    )


class PageText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip: list[str] = []
        self.structured: list[str] = []
        self.ld: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("type", "") == "application/ld+json":
            self.ld = []
        if tag in {"script", "style", "nav", "footer", "noscript", "svg", "form"}:
            self.skip.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.ld is not None:
            self.structured.append("".join(self.ld))
            self.ld = None
        if tag in self.skip:
            self.skip = self.skip[: self.skip.index(tag)]

    def handle_data(self, data: str) -> None:
        if self.ld is not None:
            self.ld.append(data)
        elif not self.skip and data.strip():
            self.parts.append(data.strip())


def page_text(content: bytes, content_type: str) -> str:
    if not any(
        kind in content_type.lower()
        for kind in ("text/html", "application/xhtml+xml", "text/plain")
    ):
        raise Problem(
            422, "URL_CONTENT_UNSUPPORTED", "Use an HTML vacancy page, or paste the advert text."
        )
    decoded = content.decode("utf-8", errors="replace")
    parser = PageText()
    parser.feed(decoded)
    postings: list[dict[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            types = value.get("@type", [])
            if types == "JobPosting" or isinstance(types, list) and "JobPosting" in types:
                postings.append(value)
            if "@graph" in value:
                collect(value["@graph"])

    for source in parser.structured:
        try:
            collect(json.loads(source))
        except (ValueError, RecursionError):
            continue
    unique = {json.dumps(item, sort_keys=True): item for item in postings}
    if len(unique) > 1:
        raise Problem(
            422,
            "URL_MULTIPLE_JOBS",
            "This page contains several vacancies. Open one vacancy or paste its text.",
        )
    if unique:
        posting = next(iter(unique.values())).copy()
        description = PageText()
        description.feed(str(posting.get("description", "")))
        posting["description"] = "\n".join(description.parts)
        text = json.dumps(posting, ensure_ascii=False, indent=2)
    else:
        text = "\n".join(parser.parts)
    if len(text.strip()) < 100:
        raise Problem(
            422,
            "URL_NO_JOB_TEXT",
            "No readable vacancy text was found. The page may require JavaScript or "
            "login; paste the advert text instead.",
        )
    if len(text) > 50000:
        raise Problem(
            422,
            "URL_CONTENT_LIMIT",
            "The page contains too much text. Paste only the vacancy text instead.",
        )
    return text


def fetch_vacancy(url: str) -> tuple[str, str]:
    deadline = time.monotonic() + 25
    for _ in range(4):
        host, _, _ = public_target(url)
        _, status, _, robots = redirects(f"https://{host}/robots.txt", deadline)
        if status == 200:
            rules = RobotFileParser()
            rules.parse(robots.decode("utf-8", errors="replace").splitlines())
            if not rules.can_fetch(AGENT, url):
                raise Problem(
                    422,
                    "URL_ACCESS_RESTRICTED",
                    "The website does not permit this automated read. Paste text you are "
                    "authorised to use.",
                )
        elif status not in {404, 410}:
            raise Problem(
                422,
                "URL_ACCESS_RESTRICTED",
                "The website's access rules could not be confirmed. Paste the advert text instead.",
            )
        status, headers, content = request_page(url, deadline)
        if status in {301, 302, 303, 307, 308} and headers.get("location"):
            url = urljoin(url, headers["location"])
            continue
        if status != 200:
            raise Problem(
                422,
                "URL_ACCESS_RESTRICTED",
                "The page is unavailable or requires access. Paste the text instead; login "
                "and CAPTCHA are not bypassed.",
            )
        return url, page_text(content, headers.get("content-type", ""))
    raise Problem(422, "URL_REDIRECT_LIMIT", "Use the final vacancy URL, or paste the text.")


class URLImport(Input):
    url: str = Field(min_length=1, max_length=2000)
    ai_consent: bool = False


@router.post("/import-url")
def import_url(data: URLImport, actor: Actor, request: Request, response: Response) -> Row:
    if not data.ai_consent:
        raise Problem(
            422,
            "AI_CONSENT_REQUIRED",
            "Confirm importing this public page and sending its text to OpenAI.",
        )
    url, text = fetch_vacancy(data.url)
    job = import_job(
        JobImport(raw_text=text, source_name="web", source_url=url), actor, request, response
    )
    settings = settings_for(request)
    with connect(settings) as db:
        stored = get_record(db, actor.id, "job", UUID(job["id"]))
        job = {**stored["data"], "id": str(stored["id"]), "version": stored["version"]}
    if job["version"] > 1 or job.get("reviewed_at"):
        return {"job": job, "extraction_error": None, "existing": True}
    try:
        run = parse_vacancy(settings, get_provider(settings), actor.id, stored)
        job = apply_draft(
            UUID(job["id"]),
            ApplyDraft(expected_version=job["version"], run_id=run["run_id"]),
            actor,
            request,
        )
        return {"job": job, "extraction_error": None, "existing": False}
    except Problem as error:
        return {"job": job, "extraction_error": error.code, "existing": False}
