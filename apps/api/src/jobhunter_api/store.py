"""PostgreSQL boundary. Each connection context is one atomic transaction."""

from typing import Any

import psycopg
from psycopg.rows import dict_row

from jobhunter_api.settings import Settings

type Row = dict[str, Any]
type Connection = psycopg.Connection[Row]


def connect(settings: Settings) -> Connection:
    return psycopg.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password.get_secret_value(),
        connect_timeout=5,
        options="-c statement_timeout=10000 -c lock_timeout=5000",
        row_factory=dict_row,
    )
