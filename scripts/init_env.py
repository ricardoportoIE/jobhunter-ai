"""Create local credentials once, without overwriting an existing .env."""

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    content = template.replace(
        "JOBHUNTER_DB_PASSWORD=\n",
        f"JOBHUNTER_DB_PASSWORD={secrets.token_urlsafe(32)}\n",
    )
    try:
        with (ROOT / ".env").open("x", encoding="utf-8", newline="\n") as target:
            target.write(content)
    except FileExistsError:
        print("Existing .env preserved.")
    else:
        print("Created .env with a random local password. Credentials were not printed.")


if __name__ == "__main__":
    main()
