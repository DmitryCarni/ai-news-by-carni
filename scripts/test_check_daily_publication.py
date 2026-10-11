"""Tests for the independent, read-only Daily publication observer."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.check_daily_publication import inspect_daily, normalize_report_date, telegram_receipt_path


class DailyPublicationCheckTest(unittest.TestCase):
    date = "2026-10-10"

    def setup_fixture(self, root: Path):
        articles = {
            f"daily/{self.date}.md": f"---\nreport_date: {self.date}\nreport_type: daily\n---\nRU text\n",
            f"en/daily/{self.date}.md": f"---\nreport_date: {self.date}\nreport_type: daily_en\n---\nEN text\n",
            f"_telegram/daily/{self.date}.txt": "RU Telegram content",
            f"_telegram/en/daily/{self.date}.txt": "EN Telegram content",
        }
        receipts = {}
        for file, content in articles.items():
            target = root / file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            if file.endswith(".txt"):
                lang = "en" if "/en/" in file else "ru"
                receipts[telegram_receipt_path(self.date, lang)] = {
                    "source_file": file,
                    "message_id": 100 if lang == "ru" else 55,
                    "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                }
        return receipts

    def test_full_day_and_receipts(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            receipts = self.setup_fixture(root)
            self.assertEqual([], inspect_daily(root, self.date, lambda path: receipts[path]))

    def test_missing_daily_is_p0_even_if_telegram_exists(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            receipts = self.setup_fixture(root)
            (root / f"daily/{self.date}.md").unlink()
            problems = inspect_daily(root, self.date, lambda path: receipts[path])
            self.assertTrue(any("missing public artifact" in x for x in problems))

    def test_mismatched_telegram_receipt(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            receipts = self.setup_fixture(root)
            receipts[telegram_receipt_path(self.date, "en")]["message_id"] = 0
            problems = inspect_daily(root, self.date, lambda path: receipts[path])
            self.assertTrue(any("Telegram en receipt identity/hash mismatch" in x for x in problems))

    def test_corrupt_receipt(self):
        with TemporaryDirectory() as name:
            root = Path(name)
            self.setup_fixture(root)
            errors = inspect_daily(root, self.date, lambda path: json.loads("INVALID"))
            self.assertEqual(2, len(errors))

    def test_invalid_date(self):
        for bad in ("2026-02-30", "../../secrets", "2026-1-1", "2026-10-10a"):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                normalize_report_date(bad)


if __name__ == "__main__":
    unittest.main()
