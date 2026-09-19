"""Minimal database probe; no schema or candidate data is created here."""

import logging

import psycopg

from jobhunter_api.settings import Settings

logger = logging.getLogger(__name__)


def check_database(settings: Settings) -> bool:
    try:
        with psycopg.connect(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password.get_secret_value(),
            connect_timeout=3,
            options="-c statement_timeout=3000",
            autocommit=True,
        ) as connection:
            return connection.execute("SELECT 1").fetchone() == (1,)
    except psycopg.Error:
        # Driver exceptions may contain connection details; never log their payload.
        logger.warning("Database readiness check failed")
        return False
