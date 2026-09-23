"""Offline checks for synthetic-host isolation and recovery failure paths."""

import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "operations", Path(__file__).with_name("operations.py")
)
operations = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(operations)


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / ".private").mkdir()
        self.patch = patch.object(operations, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_context_rejects_an_unrelated_bucket(self):
        with (
            patch.object(Path, "read_text", side_effect=["p5-abcdefghijkl", "unrelated-bucket"]),
            self.assertRaises(ValueError),
        ):
            operations.context()

    def test_context_accepts_only_the_matching_session_bucket(self):
        with patch.object(
            Path,
            "read_text",
            side_effect=["p5-abcdefghijkl", "jobhunter-p5-abcdefghijkl-123456789012"],
        ):
            self.assertEqual(operations.context()[0], "p5-abcdefghijkl")

    def test_backup_refuses_a_changing_database_before_upload(self):
        with (
            patch.object(operations, "context", return_value=("session", "bucket")),
            patch.object(operations, "record_hash", side_effect=["before", "after"]),
            patch.object(operations, "compose", return_value=b"dump"),
            patch.object(operations, "command") as command,
        ):
            with self.assertRaisesRegex(ValueError, "Data changed"):
                operations.backup()
            command.assert_not_called()

    def prepare_restore(self, contents=b"dump"):
        (self.root / ".private/restored.dump").write_bytes(contents)
        (self.root / ".private/backup.json").write_text(
            json.dumps({"sha256": hashlib.sha256(b"dump").hexdigest(), "records_hash": "records"})
        )

    def test_corrupt_download_never_creates_a_database(self):
        self.prepare_restore(b"corrupt")
        with (
            patch.object(operations, "context", return_value=("session", "bucket")),
            patch.object(operations, "command"),
            patch.object(operations, "compose") as compose,
        ):
            with self.assertRaises(AssertionError):
                operations.restore_check()
            compose.assert_not_called()

    def test_failed_restore_still_removes_only_the_scratch_database(self):
        self.prepare_restore()
        with (
            patch.object(operations, "context", return_value=("session", "bucket")),
            patch.object(operations, "command"),
            patch.object(
                operations, "compose", side_effect=[b"", RuntimeError("failed"), b""]
            ) as compose,
        ):
            with self.assertRaises(RuntimeError):
                operations.restore_check()
            self.assertEqual(
                compose.call_args.args,
                ("exec", "-T", "db", "dropdb", "-U", "jobhunter", "jobhunter_p5_restore"),
            )

    def test_restore_compares_data_before_publishing_success(self):
        self.prepare_restore()
        with (
            patch.object(operations, "context", return_value=("session", "bucket")),
            patch.object(operations, "command") as command,
            patch.object(operations, "compose"),
            patch.object(operations, "record_hash", return_value="different"),
        ):
            with self.assertRaises(AssertionError):
                operations.restore_check()
            self.assertEqual(command.call_count, 1)
            self.assertFalse((self.root / ".private/restore.json").exists())

    def test_restore_reports_success_after_matching_data(self):
        self.prepare_restore()
        with (
            patch.object(operations, "context", return_value=("session", "bucket")),
            patch.object(operations, "command") as command,
            patch.object(operations, "compose"),
            patch.object(operations, "record_hash", return_value="records"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            operations.restore_check()
            self.assertEqual(command.call_count, 2)
            report = json.loads((self.root / ".private/restore.json").read_text())
            self.assertEqual(report["restore"], "passed")


if __name__ == "__main__":
    unittest.main()
