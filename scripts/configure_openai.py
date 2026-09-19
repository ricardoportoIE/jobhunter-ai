"""Import a supplied key into ignored local configuration without printing it."""

import argparse
import re
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key_file", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = root / ".env"
    if not destination.exists():
        raise SystemExit("Run scripts/init_env.py first.")
    matches = re.findall(r"sk-[A-Za-z0-9_-]{20,}", args.key_file.read_text(encoding="utf-8-sig"))
    if len(matches) != 1:
        raise SystemExit("Expected exactly one OpenAI key; no configuration changed.")
    lines = destination.read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if not line.startswith("JOBHUNTER_OPENAI_API_KEY=")]
    destination.write_text("\n".join([*lines, "JOBHUNTER_OPENAI_API_KEY=" + matches[0]]) + "\n",
                           encoding="utf-8")
    destination.chmod(0o600)
    print("OpenAI key configured in ignored .env; value not displayed.")


if __name__ == "__main__":
    main()
