"""Local administration: migrate, bootstrap. Never prints credentials."""

import argparse
import hashlib
import secrets
from pathlib import Path
from uuid import uuid4

from argon2 import PasswordHasher

from jobhunter_api.seed import seed
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect


def migrate(settings: Settings) -> None:
    with connect(settings) as db:
        db.execute("SELECT pg_advisory_xact_lock(71001)")
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(name text PRIMARY KEY, checksum text NOT NULL)"
        )
        for path in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
            source = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(source.encode()).hexdigest()
            existing = db.execute(
                "SELECT checksum FROM schema_migrations WHERE name=%s", (path.name,)
            ).fetchone()
            if existing:
                if existing["checksum"] != checksum:
                    raise RuntimeError("Applied migration changed: " + path.name)
                continue
            db.execute(source)
            db.execute("INSERT INTO schema_migrations VALUES (%s,%s)", (path.name, checksum))


def bootstrap(settings: Settings, destination: Path) -> None:
    with connect(settings) as db:
        db.execute("SELECT pg_advisory_xact_lock(71002)")
        if db.execute("SELECT id FROM users").fetchone():
            print("Existing local account preserved.")
            return
        password = secrets.token_urlsafe(24)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as output:
            output.write("Username: local\nPassword: " + password + "\n")
        destination.chmod(0o600)
        db.execute(
            "INSERT INTO users (id,username,password_hash) VALUES (%s,%s,%s)",
            (uuid4(), "local", PasswordHasher().hash(password)),
        )
    print("Local account created; credentials saved in the private file.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["migrate", "bootstrap", "seed"])
    parser.add_argument("--credentials-file", type=Path, default=Path(".private/local-login.txt"))
    args = parser.parse_args()
    settings = Settings()
    migrate(settings)
    if args.command == "bootstrap":
        bootstrap(settings, args.credentials_file)
    elif args.command == "seed":
        seed(settings)
    print("Database migrations applied.")


if __name__ == "__main__":
    main()
