"""Conservative P5 quotes and atomic reservations; teardown never releases a reservation."""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal

# Closed topology: these are the paid regional SKUs, not free-tier allowances.
SKUS = {
    "compute": ("AmazonEC2", "47NTBKB4KMUU98P8", "Hrs"),
    "disk": ("AmazonEC2", "TXACT7E3PV6ZX2NM", "GB-Mo"),
    "ipv4": ("AmazonVPC", "CNZ4XSXPRJXGA4ZF", "Hrs"),
    "objects": ("AmazonS3", "4AJHPB29ZPVFADXP", "GB-Mo"),
    "puts": ("AmazonS3", "578M9UJHH6X5PZVC", "Requests"),
    "gets": ("AmazonS3", "ZCQD4CM637S7D8U5", "Requests"),
    "logs": ("AmazonCloudWatch", "KJBTQPDHW2H92B8Y", "GB"),
    "log_storage": ("AmazonCloudWatch", "M93YPPU987S2T6U9", "GB-Mo"),
    "metric": ("AmazonCloudWatch", "58YXNUN4MF8JD9ZA", "Metrics"),
    "alarm": ("AmazonCloudWatch", "GDMKAEDCSYJAKBZQ", "Alarms"),
    "requests": ("AmazonCloudWatch", "T3382F3WY8W5UTQS", "Requests"),
    "scheduler": ("AWSEvents", "E82DKZKPTKQ3W532", "Invocations"),
    "transfer": ("AWSDataTransfer", "FSEU4E6BRE95JTX8", "GB"),
}
EUR_PER_USD = Decimal("1.25")
CONTINGENCY = Decimal("1.25")
SESSION_CENTS = 500
RESIDUAL_CENTS = 500
AWS_CENTS = 1500
AI_CENTS = 1000
COMBINED_CENTS = 2500


def now():
    return datetime.now(UTC)


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError("Evidence timestamps must be UTC")
    return result


def fresh(value, at):
    age = at - timestamp(value)
    if age < timedelta(0) or age > timedelta(hours=24):
        raise ValueError("Evidence is future-dated or older than 24 hours")


def amount(value):
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("A known, non-negative finite amount is required")
    return result


def cents(value):
    return int((amount(value) * 100).to_integral_value(rounding=ROUND_CEILING))


def estimate(quote, hours, at):
    fresh(quote["checked_at"], at)
    hours = amount(hours)
    if not 0 < hours <= 8 or quote["region"] != "eu-west-1":
        raise ValueError("Only a session of up to eight hours in eu-west-1 is supported")
    if set(quote["rates"]) != set(SKUS):
        raise ValueError("The quote is incomplete or contains an unreviewed component")
    quantities = {
        "compute": hours,
        "disk": 24 * hours / 720,
        "ipv4": hours,
        # Full-month storage, one full metric/alarm month and generous usage allowances.
        "objects": 1,
        "puts": 1000,
        "gets": 1000,
        "logs": 1,
        "log_storage": 1,
        "metric": 1,
        "alarm": 1,
        "requests": 10000,
        "scheduler": 10,
        "transfer": 1,
    }
    total = Decimal(0)
    for key, (_, sku, unit) in SKUS.items():
        rate = quote["rates"][key]
        if rate["sku"] != sku or rate["unit"] != unit or amount(rate["usd"]) <= 0:
            raise ValueError("The paid SKU or unit does not match the reviewed topology")
        total += amount(rate["usd"]) * amount(quantities[key])
    result = cents(total * EUR_PER_USD * CONTINGENCY)
    if result > SESSION_CENTS:
        raise ValueError("The estimate exceeds the EUR 5 session reservation")
    return result


def ledger(path):
    connection = sqlite3.connect(path, timeout=30, isolation_level=None)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS reservations ("
        "session TEXT PRIMARY KEY, account TEXT NOT NULL, month TEXT NOT NULL, "
        "state TEXT NOT NULL, cents INTEGER NOT NULL, binding TEXT NOT NULL)"
    )
    return connection


def reserve(path, session, quote, spending, at=None):
    at = at or now()
    maximum = estimate(quote, session["hours"], at)
    fresh(spending["checked_at"], at)
    month = at.strftime("%Y-%m")
    if spending["month"] != month or spending["account"] != session["account"]:
        raise ValueError("Spending must describe this account and UTC month")
    if not spending.get("reference", "").strip():
        raise ValueError("Spending evidence requires an explicit source")
    existing = cents(amount(spending["usd"]) * EUR_PER_USD * CONTINGENCY)
    with closing(ledger(path)) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM reservations WHERE account=? AND state!='destroyed'",
                (session["account"],),
            ).fetchone():
                raise ValueError("An unsettled active session requires cleanup first")
            used, count = db.execute(
                "SELECT coalesce(sum(cents),0),count(*) FROM reservations "
                "WHERE account=? AND month=?",
                (session["account"], month),
            ).fetchone()
            projected = existing + used + RESIDUAL_CENTS + SESSION_CENTS
            if count >= 2 or projected > AWS_CENTS or projected + AI_CENTS > COMBINED_CENTS:
                raise ValueError("Monthly AWS or combined budget would be exceeded")
            db.execute(
                "INSERT INTO reservations VALUES (?,?,?,?,?,?)",
                (
                    session["id"],
                    session["account"],
                    month,
                    "reserved",
                    SESSION_CENTS,
                    json.dumps(session, sort_keys=True),
                ),
            )
            db.commit()
        except BaseException:
            db.rollback()
            raise
    return {
        "estimate_eur": maximum / 100,
        "reserved_eur": SESSION_CENTS / 100,
        "aws_projected_eur": projected / 100,
        "combined_projected_eur": (projected + AI_CENTS) / 100,
        "aws_alerts": [p for p in (50, 80, 100) if projected * 100 >= AWS_CENTS * p],
        "combined_alerts": [
            p for p in (50, 80, 100) if (projected + AI_CENTS) * 100 >= COMBINED_CENTS * p
        ],
    }


def mark_destroyed(path, session):
    with closing(ledger(path)) as db:
        # Keep the full monetary reservation until month end: billing is delayed.
        db.execute("UPDATE reservations SET state='destroyed' WHERE session=?", (session,))
