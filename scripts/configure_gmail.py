"""Import a Google web OAuth client into ignored local configuration without displaying secrets."""

import argparse
import json
import re
from pathlib import Path

from cryptography.fernet import Fernet


def configure(source: Path, destination: Path, redirect: str) -> None:
    if not destination.exists():
        raise ValueError("Run scripts/init_env.py first.")
    value = json.loads(source.read_text(encoding="utf-8-sig")).get("web", {})
    identity, secret = value.get("client_id", ""), value.get("client_secret", "")
    if (
        not re.fullmatch(r"[A-Za-z0-9._-]+\.apps\.googleusercontent\.com", identity)
        or not re.fullmatch(r"[A-Za-z0-9_-]{10,200}", secret)
        or redirect not in value.get("redirect_uris", [])
        or not re.fullmatch(r"http://(?:127\.0\.0\.1|localhost):[0-9]{2,5}/", redirect)
    ):
        raise ValueError("Use a web client with the exact local redirect URI registered.")
    lines = destination.read_text(encoding="utf-8").splitlines()
    previous = dict(
        line.split("=", 1) for line in lines if "=" in line and not line.startswith("#")
    )
    key = previous.get("JOBHUNTER_DISCOVERY_ENCRYPTION_KEY") or Fernet.generate_key().decode()
    Fernet(key.encode())  # Preserve the existing key so stored tokens remain decryptable.
    values = {
        "JOBHUNTER_GMAIL_CLIENT_ID": identity,
        "JOBHUNTER_GMAIL_CLIENT_SECRET": secret,
        "JOBHUNTER_GMAIL_REDIRECT_URI": redirect,
        "JOBHUNTER_DISCOVERY_ENCRYPTION_KEY": key,
    }
    lines = [line for line in lines if line.split("=", 1)[0] not in values]
    destination.write_text(
        "\n".join([*lines, *(f"{key}={value}" for key, value in values.items())]) + "\n",
        encoding="utf-8",
    )
    destination.chmod(0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client_file", type=Path)
    parser.add_argument("--redirect-uri", default="http://127.0.0.1:5173/")
    args = parser.parse_args()
    try:
        configure(args.client_file, Path(__file__).resolve().parents[1] / ".env", args.redirect_uri)
    except (ValueError, OSError, TypeError):
        raise SystemExit(
            "Configuration was not changed. Check the web client file and redirect URI."
        ) from None
    print(
        "Gmail configuration saved in ignored .env; secrets were not displayed. "
        "Restart API and discovery."
    )


if __name__ == "__main__":
    main()
