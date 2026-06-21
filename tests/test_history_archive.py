# -*- coding: utf-8 -*-
"""
历史归档读取测试。
"""

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, ".")

from core.content_store import (  # noqa: E402
    is_valid_history_date,
    latest_archive_batch_file,
    list_recent_history_dates,
    load_history_archive_snapshot,
)


class TestHistoryArchive(unittest.TestCase):
    def _write_snapshot(self, root, source_id, date_text, batch_name, item_count=1):
        target_dir = Path(root) / source_id / date_text
        target_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": "{}T07:50:00".format(date_text),
            "source": {"id": source_id},
            "item_count": item_count,
            "items": [
                {
                    "title": "item-{}".format(batch_name),
                    "url": "https://example.com/{}".format(batch_name),
                }
            ],
        }
        path = target_dir / batch_name
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f)
        return path

    def test_latest_archive_batch_file_uses_largest_number(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_snapshot(temp_dir, "github-daily", "2026-06-06", "01.json")
            self._write_snapshot(temp_dir, "github-daily", "2026-06-06", "03.json")
            self._write_snapshot(temp_dir, "github-daily", "2026-06-06", "02.json")

            latest_file = latest_archive_batch_file(
                "github-daily",
                "2026-06-06",
                output_dir=temp_dir,
            )

            self.assertEqual(latest_file.name, "03.json")

    def test_load_history_archive_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_snapshot(temp_dir, "github-daily", "2026-06-06", "01.json")
            self._write_snapshot(temp_dir, "github-daily", "2026-06-06", "02.json")

            snapshot, served_from, batch_file = load_history_archive_snapshot(
                "github-daily",
                "2026-06-06",
                output_dir=temp_dir,
            )

            self.assertEqual(served_from, "archive-history")
            self.assertEqual(batch_file, "02.json")
            self.assertEqual(snapshot["items"][0]["title"], "item-02.json")

    def test_list_recent_history_dates_excludes_today(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_snapshot(temp_dir, "github-daily", "2026-06-06", "01.json")

            result = list_recent_history_dates(
                days=7,
                output_dir=temp_dir,
                today=date(2026, 6, 7),
            )

            self.assertEqual(len(result), 7)
            self.assertEqual(result[0]["date"], "2026-06-06")
            self.assertEqual(result[-1]["date"], "2026-05-31")
            self.assertNotIn("2026-06-07", [item["date"] for item in result])
            self.assertTrue(result[0]["has_archive"])

    def test_invalid_date_and_unknown_source_return_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertFalse(is_valid_history_date("2026-99-99"))
            self.assertFalse(is_valid_history_date("../../etc/passwd"))

            snapshot, served_from, batch_file = load_history_archive_snapshot(
                "unknown-source",
                "2026-06-06",
                output_dir=temp_dir,
            )

            self.assertIsNone(snapshot)
            self.assertEqual(served_from, "unknown")
            self.assertEqual(batch_file, "")


if __name__ == "__main__":
    unittest.main()
