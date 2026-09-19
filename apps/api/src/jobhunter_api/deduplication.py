"""Conservative identities: content alone never merges postings across locations."""

import hashlib
import json
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from jobhunter_api.store import Row


def fingerprint(data: Row) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip().casefold()


def canonical_url(value: str) -> str:
    parts = urlsplit(value)
    # Drop only known tracking parameters; identifiers and location parameters remain.
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in {"gclid", "fbclid"}
    ]
    host = (parts.hostname or "").lower()
    if ":" in host:
        host = "[" + host + "]"
    if parts.port and (parts.scheme, parts.port) not in {("http", 80), ("https", 443)}:
        host += ":" + str(parts.port)
    return urlunsplit((parts.scheme.lower(), host, parts.path or "/", urlencode(sorted(query)), ""))


def identity_keys(data: Row) -> list[str]:
    keys = []
    if data.get("external_id"):
        keys.append(
            "external:"
            + fingerprint(
                {"source": normalized(data["source_name"]), "external_id": data["external_id"]}
            )
        )
    if data.get("source_url"):
        keys.append("url:" + hashlib.sha256(canonical_url(data["source_url"]).encode()).hexdigest())
    if data.get("location_hint") and normalized(data["location_hint"]):
        keys.append(
            "content_location:"
            + fingerprint(
                {
                    "text": normalized(data["raw_text"]),
                    "location": normalized(data["location_hint"]),
                }
            )
        )
    return keys
