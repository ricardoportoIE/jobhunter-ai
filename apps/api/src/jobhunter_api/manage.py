"""Local administration: migrate, bootstrap. Never prints credentials."""

import argparse
import hashlib
import secrets
from pathlib import Path
from uuid import uuid4

from argon2 import PasswordHasher
from psycopg import sql

from jobhunter_api.records import owner_lock
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


def provision(settings: Settings) -> None:
    if not settings.app_db_password:
        raise RuntimeError("Run scripts/init_env.py to configure JOBHUNTER_APP_DB_PASSWORD")
    role = sql.Identifier(settings.app_db_user)
    with connect(settings) as db:
        if not db.execute(
            "SELECT 1 FROM pg_roles WHERE rolname=%s", (settings.app_db_user,)
        ).fetchone():
            db.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    role, sql.Literal(settings.app_db_password.get_secret_value())
                )
            )
        db.execute(
            sql.SQL(
                "ALTER ROLE {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS"
            ).format(role)
        )
        db.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        db.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
        db.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(role))
        db.execute(sql.SQL("GRANT SELECT ON users TO {}").format(role))
        db.execute(sql.SQL("GRANT SELECT,INSERT,DELETE ON sessions TO {}").format(role))
        db.execute(
            sql.SQL(
                "GRANT SELECT,INSERT,UPDATE,DELETE ON "
                "records,login_limits,idempotency,job_keys TO {}"
            ).format(role)
        )
        db.execute(sql.SQL("GRANT SELECT,INSERT ON audit_events,snapshots TO {}").format(role))
        db.execute(sql.SQL("GRANT SELECT,INSERT,UPDATE ON ai_calls TO {}").format(role))
        db.execute(sql.SQL("GRANT SELECT,INSERT,DELETE ON ai_embeddings TO {}").format(role))
    print(
        "Restricted application role configured; audit and snapshots are append-only for runtime."
    )


def erase(settings: Settings, confirmation: str) -> None:
    if confirmation != "DELETE_LOCAL_APPLICATION_DATA":
        raise ValueError("Erasure requires --confirm DELETE_LOCAL_APPLICATION_DATA")
    with connect(settings) as db:
        user = db.execute("SELECT id FROM users WHERE username='local'").fetchone()
        if user:
            owner_lock(db, user["id"])
            # Keep non-personal monthly charges so erasure cannot reset the budget.
            db.execute(
                "UPDATE ai_calls SET owner_id=NULL,result=NULL,request_key='',payload_hash='',"
                "provider_request_id=NULL WHERE owner_id=%s",
                (user["id"],),
            )
            for table in (
                "ai_embeddings",
                "job_keys",
                "idempotency",
                "snapshots",
                "records",
                "sessions",
                "audit_events",
            ):
                db.execute(
                    sql.SQL("DELETE FROM {} WHERE owner_id=%s").format(sql.Identifier(table)),
                    (user["id"],),
                )
    print("Local application data erased; sessions revoked. Account and source files preserved.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["migrate", "bootstrap", "seed", "provision", "erase"])
    parser.add_argument("--confirm", default="")
    parser.add_argument("--credentials-file", type=Path, default=Path(".private/local-login.txt"))
    args = parser.parse_args()
    settings = Settings()
    migrate(settings)
    if args.command == "bootstrap":
        bootstrap(settings, args.credentials_file)
    elif args.command == "seed":
        seed(settings)
    elif args.command == "provision":
        provision(settings)
    elif args.command == "erase":
        erase(settings, args.confirm)
    print("Database migrations applied.")


if __name__ == "__main__":
    main()
