"""Check one due, opted-in source per minute while the local worker is running."""

import logging
import time
from pathlib import Path
from tempfile import gettempdir

from jobhunter_api.discovery_sync import synchronise
from jobhunter_api.settings import Settings
from jobhunter_api.store import connect


def tick(settings: Settings) -> None:
    with connect(settings) as db:
        row = db.execute(
            "SELECT id,owner_id FROM records WHERE kind='discovery_source' AND NOT deleted "
            "AND (data->>'enabled')::boolean AND (data->>'review_until')::date>=CURRENT_DATE "
            "AND coalesce((data->>'next_sync_at')::timestamptz,'epoch')<=now() "
            "AND coalesce((data->>'lease_until')::timestamptz,'epoch')<=now() "
            "ORDER BY coalesce((data->>'next_sync_at')::timestamptz,'epoch'),id LIMIT 1"
        ).fetchone()
    if row:
        synchronise(settings, row["owner_id"], row["id"])


def main() -> None:
    settings = Settings().runtime()
    while True:
        try:
            tick(settings)
            (Path(gettempdir()) / "discovery-heartbeat").touch()
        except Exception as error:
            logging.getLogger(__name__).warning(
                "Discovery check deferred: %s", type(error).__name__
            )
        time.sleep(60)


if __name__ == "__main__":
    main()
