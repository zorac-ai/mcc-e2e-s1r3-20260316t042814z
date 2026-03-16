from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(db_path: Path, *args: str) -> object:
    result = subprocess.run(
        [sys.executable, "-m", "issue_tracker", "--db", str(db_path), *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "issues.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_json(self, *args: str) -> object:
        return run_cli(self.db_path, *args)

    def test_create_and_list_open_issues(self) -> None:
        created = self.run_json("add", "Ship the CLI")
        self.assertEqual(created["id"], 1)
        self.assertEqual(created["status"], "open")

        issues = self.run_json("list")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["title"], "Ship the CLI")

    def test_list_includes_created_issue(self) -> None:
        created = self.run_json("add", "Document the commands")
        issues = self.run_json("list")
        self.assertEqual(issues[0]["id"], created["id"])
        self.assertEqual(issues[0]["title"], "Document the commands")

    def test_close_issue_and_filter_closed(self) -> None:
        self.run_json("add", "Close me")
        closed = self.run_json("close", "1")
        self.assertEqual(closed["status"], "closed")
        self.assertIsNotNone(closed["closed_at"])

        issues = self.run_json("list", "--status", "closed")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["id"], 1)

    def test_close_with_reason(self) -> None:
        self.run_json("add", "Fix the bug")
        closed = self.run_json("close", "1", "--reason", "done")
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["close_reason"], "done")

    def test_close_without_reason_has_no_close_reason_field(self) -> None:
        self.run_json("add", "No reason needed")
        closed = self.run_json("close", "1")
        self.assertEqual(closed["status"], "closed")
        self.assertNotIn("close_reason", closed)

    def test_open_issue_has_null_closed_at(self) -> None:
        created = self.run_json("add", "Still open")
        self.assertIsNone(created["closed_at"])

    def test_closed_at_is_valid_iso8601(self) -> None:
        self.run_json("add", "Timestamp check")
        closed = self.run_json("close", "1")
        self.assertIsNotNone(closed["closed_at"])
        parsed = datetime.fromisoformat(closed["closed_at"])
        self.assertIsNotNone(parsed.tzinfo)

    def test_closed_at_recorded_with_reason(self) -> None:
        self.run_json("add", "With reason and timestamp")
        closed = self.run_json("close", "1", "--reason", "completed")
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["close_reason"], "completed")
        self.assertIsNotNone(closed["closed_at"])
        datetime.fromisoformat(closed["closed_at"])

    def test_missing_issue_returns_non_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "issue_tracker", "--db", str(self.db_path), "close", "999"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("issue 999 not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
