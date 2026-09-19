"""Reconcile an interrupted request only after checking the provider usage/billing."""

import argparse
from decimal import Decimal
from uuid import UUID

from jobhunter_api.records import audit
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect


def reconcile(settings: Settings, identity: UUID, confirmed_eur: Decimal) -> None:
    if not confirmed_eur.is_finite() or confirmed_eur < 0:
        raise ValueError("Confirmed cost must be finite and nonnegative")
    with connect(settings) as db:
        db.execute("SELECT pg_advisory_xact_lock(71020)")
        row = db.execute(
            "UPDATE ai_calls SET actual_eur=%s,status='failed',finished_at=now(),"
            "error_code='MANUALLY_RECONCILED' WHERE id=%s AND (status='uncertain' OR "
            "(status='running' AND created_at<now()-interval '5 minutes')) RETURNING owner_id",
            (confirmed_eur, identity),
        ).fetchone()
        if row is None:
            raise ValueError("Only interrupted or expired executions can be reconciled")
        if row["owner_id"]:
            audit(db, row["owner_id"], "ai.reconciled", identity, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", type=UUID)
    parser.add_argument("--confirmed-eur", type=Decimal, required=True)
    parser.add_argument("--billing-checked", action="store_true", required=True)
    args = parser.parse_args()
    reconcile(Settings(), args.run_id, args.confirmed_eur)
    print("Confirmed charge recorded; budget history preserved.")


if __name__ == "__main__":
    main()
