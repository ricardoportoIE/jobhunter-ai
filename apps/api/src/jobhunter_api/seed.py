"""Optional fictional seed, refused when a profile already has facts."""

import hashlib
from datetime import UTC, datetime

from jobhunter_api.records import insert, owner_lock, profile, update
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect


def seed(settings: Settings) -> None:
    with connect(settings) as db:
        user = db.execute("SELECT id FROM users WHERE username='local'").fetchone()
        if not user:
            raise RuntimeError("Run bootstrap first")
        owner = user["id"]
        owner_lock(db, owner)
        if db.execute(
            "SELECT id FROM records WHERE owner_id=%s AND kind='fact'", (owner,)
        ).fetchone():
            raise RuntimeError("Seed refused: candidate already has facts")
        content = "Fictional demonstration: created a small Python API. Not a real candidate claim."
        evidence = insert(
            db,
            owner,
            "evidence",
            {
                "source_type": "candidate_attestation",
                "source_ref": "synthetic:phase1-demo",
                "locator": "Example",
                "content": content,
                "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "sensitivity": "public",
                "reviewed_by": str(owner),
                "reviewed_at": datetime.now(UTC).isoformat(),
            },
        )
        insert(
            db,
            owner,
            "fact",
            {
                "claim": content,
                "category": "skill",
                "status": "verified",
                "evidence_ids": [str(evidence["id"])],
                "evidence_versions": {str(evidence["id"]): 1},
                "sensitivity": "public",
                "allowed_uses": ["matching"],
                "valid_from": None,
                "valid_until": None,
                "reviewed_by": str(owner),
                "reviewed_at": datetime.now(UTC).isoformat(),
            },
        )
        current = profile(db, owner)
        update(
            db,
            current,
            current["version"],
            {
                **current["data"],
                "display_name": "Candidato fictício — demonstração",
                "status": "draft",
            },
        )
    print("Fictional seed created. Review the profile before matching.")
