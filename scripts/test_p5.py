"""Offline regression checks for cost gates, source isolation and failed-session cleanup."""

import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import p5
import p5_costs as costs


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ledger.sqlite"
        self.at = datetime(2026, 9, 23, 12, tzinfo=UTC)
        self.session = {"id": "p5-abcdef123456", "account": "123456789012", "hours": 2}
        self.quote = {
            "checked_at": self.at.isoformat(),
            "region": "eu-west-1",
            "rates": {
                key: {"sku": sku, "unit": unit, "usd": "0.00001"}
                for key, (_, sku, unit) in costs.SKUS.items()
            },
        }
        self.spending = {
            "checked_at": self.at.isoformat(),
            "month": "2026-09",
            "usd": "1",
            "account": "123456789012",
            "reference": "Synthetic test declaration",
        }

    def reserve(self, **overrides):
        args = dict(
            path=self.path,
            session=self.session,
            quote=self.quote,
            spending=self.spending,
            at=self.at,
        )
        return costs.reserve(**(args | overrides))

    def test_unknown_non_finite_and_negative_spending_is_blocked(self):
        for value in (None, "unknown", "NaN", "Infinity", "-1"):
            with self.subTest(value=value), self.assertRaises((ValueError, ArithmeticError)):
                self.reserve(spending=self.spending | {"usd": value})

    def test_stale_future_wrong_month_and_wrong_account_evidence_is_blocked(self):
        for changes in (
            {"checked_at": (self.at - timedelta(days=2)).isoformat()},
            {"checked_at": (self.at + timedelta(seconds=1)).isoformat()},
            {"month": "2026-08"},
            {"account": "999999999999"},
            {"reference": ""},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.reserve(spending=self.spending | changes)

    def test_missing_price_wrong_unit_and_excessive_price_are_blocked(self):
        for kind in ("missing", "unit", "price", "stale"):
            quote = copy.deepcopy(self.quote)
            if kind == "missing":
                del quote["rates"]["transfer"]
            elif kind == "unit":
                quote["rates"]["compute"]["unit"] = "Seconds"
            elif kind == "price":
                quote["rates"]["compute"]["usd"] = "1000"
            else:
                quote["checked_at"] = (self.at - timedelta(days=2)).isoformat()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.reserve(quote=quote)

    def test_overlong_session_is_blocked(self):
        with self.assertRaises(ValueError):
            self.reserve(session=self.session | {"hours": 9})

    def test_existing_spending_and_ai_envelope_are_reserved(self):
        result = self.reserve()
        self.assertEqual(result["aws_projected_eur"], 11.57)
        self.assertEqual(result["combined_projected_eur"], 21.57)
        self.assertEqual(result["combined_alerts"], [50, 80])

    def test_cleanup_does_not_reset_the_money_counter(self):
        self.reserve()
        costs.mark_destroyed(self.path, self.session["id"])
        with self.assertRaisesRegex(ValueError, "budget"):
            self.reserve(session=self.session | {"id": "p5-abcdef654321"})

    def test_active_previous_month_session_blocks_new_allocation(self):
        self.reserve()
        later = datetime(2026, 10, 1, 12, tzinfo=UTC)
        with self.assertRaisesRegex(ValueError, "cleanup"):
            self.reserve(
                at=later,
                quote=self.quote | {"checked_at": later.isoformat()},
                spending=self.spending | {"checked_at": later.isoformat(), "month": "2026-10"},
                session=self.session | {"id": "p5-abcdef654321"},
            )

    def test_concurrent_reservations_cannot_overspend(self):
        # Initialise the schema before competing for the reservation transaction.
        costs.ledger(self.path).close()

        def attempt(index):
            try:
                self.reserve(session=self.session | {"id": f"p5-{index:012x}"})
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(attempt, (1, 2))), [False, True])


class ControllerTests(unittest.TestCase):
    def test_personal_files_history_and_tests_are_excluded_from_upload(self):
        for path in (
            ".env",
            ".private/cv.pdf",
            ".git/config",
            "docs/profile.md",
            "apps/api/tests/fixture.json",
            "apps/web/.env",
            "scripts/configure_openai.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(p5.allowed_source(path))
        self.assertTrue(p5.allowed_source("apps/api/src/jobhunter_api/main.py"))

    def test_changed_prepared_file_blocks_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "plan.tfplan"
            path.write_bytes(b"reviewed")
            session = {"files": {"plan.tfplan": p5.digest(path)}}
            path.write_bytes(b"different")
            with self.assertRaises(ValueError):
                p5.intact(root, session)

    def test_failed_apply_still_invokes_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name in ("quote", "spending"):
                (folder / (name + ".json")).write_text("{}")
            session = {
                "profile": "test",
                "expires_at": (costs.now() + timedelta(hours=2)).isoformat(),
            }
            with (
                patch.object(p5, "load_session", return_value=(folder, session)),
                patch.object(p5, "intact"),
                patch.object(costs, "reserve", return_value={}),
                patch.object(p5, "tf", side_effect=RuntimeError("apply failed")),
                patch.object(p5, "destroy") as cleanup,
                self.assertRaises(RuntimeError),
            ):
                p5.run("synthetic")
            cleanup.assert_called_once_with(folder, session)
            self.assertEqual(json.loads((folder / "reservation.json").read_text()), {})

    def test_unknown_resource_cannot_be_added_to_the_plan(self):
        with self.assertRaises(ValueError):
            p5.validate_plan(
                {
                    "resource_changes": [
                        {
                            "address": "aws_nat_gateway.extra",
                            "mode": "managed",
                            "change": {"actions": ["create"], "after": {}},
                        }
                    ]
                }
            )


if __name__ == "__main__":
    unittest.main()
