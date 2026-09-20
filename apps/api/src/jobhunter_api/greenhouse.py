"""Read the documented public Job Board API; never call submission endpoints."""

import hashlib
import html
import json
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, ValidationError, field_validator

from jobhunter_api.job_url import PageText
from jobhunter_api.source_http import SourceFailure, request_json
from jobhunter_api.store import Row


class DiscoveredItem(BaseModel):
    external_id: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    company: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=500)
    url: str = Field(max_length=2000)
    raw_text: str = Field(min_length=1, max_length=50000)
    source_updated_at: str | None = Field(default=None, max_length=100)
    item_type: Literal["vacancy", "email"] = "vacancy"

    @field_validator("url")
    @classmethod
    def safe_reference(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 443}
            or any(ord(char) < 33 or char == "\\" for char in value)
        ):
            raise ValueError("Unsafe reference")
        return value

    def fingerprint(self) -> str:
        # Changes to provider timestamps alone do not create duplicate alerts.
        return hashlib.sha256(
            json.dumps(self.model_dump(exclude={"source_updated_at"}), sort_keys=True).encode()
        ).hexdigest()


@dataclass
class DiscoveryBatch:
    items: list[DiscoveredItem] = field(default_factory=list)
    complete: bool = False
    not_modified: bool = False
    etag: str | None = None
    last_modified: str | None = None
    cursor: str | None = None


def read_greenhouse(source: Row) -> DiscoveryBatch:
    data = source["data"]
    headers = {}
    if data.get("etag"):
        headers["If-None-Match"] = data["etag"]
    if data.get("last_modified"):
        headers["If-Modified-Since"] = data["last_modified"]
    status, response_headers, payload = request_json(
        f"https://boards-api.greenhouse.io/v1/boards/{data['reference']}/jobs?content=true",
        headers=headers,
    )
    if status == 304:
        return DiscoveryBatch(not_modified=True)
    try:
        jobs = payload["jobs"]
        if not isinstance(jobs, list) or len(jobs) > 500 or payload["meta"]["total"] != len(jobs):
            raise ValueError("Incomplete board")
        items = []
        for job in jobs:
            if job.get("internal_job_id") is None:
                continue  # Prospect posts are not advertised vacancies.
            if not isinstance(job["id"], int) or not isinstance(job["content"], str):
                raise ValueError("Invalid post")
            parser = PageText()
            parser.feed(html.unescape(job["content"]))
            items.append(
                DiscoveredItem(
                    external_id=str(job["id"]),
                    title=job["title"],
                    company=job.get("company_name"),
                    location=job["location"]["name"] or None,
                    url=job["absolute_url"],
                    raw_text="\n".join(parser.parts),
                    source_updated_at=job.get("updated_at"),
                )
            )
        if len({item.external_id for item in items}) != len(items):
            raise ValueError("Duplicate post IDs")
        return DiscoveryBatch(
            items=items,
            complete=True,
            etag=response_headers.get("etag"),
            last_modified=response_headers.get("last-modified"),
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        raise SourceFailure("SOURCE_INVALID_RESPONSE") from None
