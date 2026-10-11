"""Independent, read-only Daily liveness check: public 4/4 + Telegram receipts.

This check NEVER creates editorial content, mutates publication state, or dispatches
another workflow. Missing business outcomes are an error, even when upstream
scheduler or GitHub Actions reported success.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATE_PATTERN = re.compile(r"20\d\d-\d\d-\d\d\Z")


def normalize_report_date(value: str) -> str:
    if not DATE_PATTERN.fullmatch(value):
        raise ValueError("report_date must use YYYY-MM-DD")
    if dt.date.fromisoformat(value).isoformat() != value:
        raise ValueError("Invalid report date")
    return value


def expected_artifacts(report_date: str) -> tuple[str, str, str, str]:
    date = normalize_report_date(report_date)
    return (
        f"daily/{date}.md",
        f"en/daily/{date}.md",
        f"_telegram/daily/{date}.txt",
        f"_telegram/en/daily/{date}.txt",
    )


def telegram_receipt_path(report_date: str, lang: str) -> str:
    date = normalize_report_date(report_date)
    if lang == "ru":
        return f"_telegram/.state/daily/{date}.json"
    if lang == "en":
        return f"_telegram/.state/en/daily/{date}.json"
    raise ValueError("Unknown language")


def read_receipt_from_git(ref: str, path: str) -> dict:
    # Only constant paths derived from the validated calendar date and fixed
    # language names can reach this function from the CLI.
    raw = subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT)
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Receipt must be an object")
    return result


def inspect_daily(root: Path, report_date: str, receipt_reader) -> list[str]:
    """Return independently observed failures; don't mutate any state."""
    article_ru, article_en, tg_ru, tg_en = expected_artifacts(report_date)
    errors: list[str] = []
    for path in (article_ru, article_en, tg_ru, tg_en):
        if not (root / path).is_file():
            errors.append(f"missing public artifact: {path}")

    for path, report_type in ((article_ru, "daily"), (article_en, "daily_en")):
        file = root / path
        if not file.is_file():
            continue
        text = file.read_text(encoding="utf-8")
        fm = text.split("---", 2)
        if len(fm) < 3 or fm[0].strip() or not fm[1].strip():
            errors.append(f"invalid front matter: {path}")
            continue
        metadata = fm[1]
        for key, expected in (("report_date", report_date), ("report_type", report_type)):
            if not re.search(rf"(?m)^{key}:\s*['\"]?{re.escape(expected)}['\"]?\s*$", metadata):
                errors.append(f"metadata {key} mismatch: {path}")

    for path, lang in ((tg_ru, "ru"), (tg_en, "en")):
        file = root / path
        if not file.is_file():
            continue
        state_path = telegram_receipt_path(report_date, lang)
        try:
            receipt = receipt_reader(state_path)
        except (ValueError, json.JSONDecodeError, subprocess.CalledProcessError, OSError) as exc:
            errors.append(f"Telegram {lang} receipt unreadable: {state_path} ({type(exc).__name__})")
            continue
        if (receipt.get("source_file") != path
                or type(receipt.get("message_id")) is not int
                or receipt["message_id"] <= 0
                or receipt.get("content_sha256") != hashlib.sha256(file.read_bytes()).hexdigest()):
            errors.append(f"Telegram {lang} receipt identity/hash mismatch: {state_path}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-date", help="Exact date, otherwise previous Asia/Aqtobe date")
    parser.add_argument("--telegram-ref", default="FETCH_HEAD", help="Already fetched telegram-state Git ref")
    args = parser.parse_args()
    today = dt.datetime.now(ZoneInfo("Asia/Aqtobe")).date()
    date = normalize_report_date(args.report_date or (today - dt.timedelta(days=1)).isoformat())
    problems = inspect_daily(ROOT, date, lambda path: read_receipt_from_git(args.telegram_ref, path))
    if problems:
        print(f"P0 DAILY INCOMPLETE {date}: {len(problems)} independently detected failure(s)")
        for problem in problems:
            print(f"::error::{problem}")
        return 1
    print(f"DAILY 4/4 + RU/EN TELEGRAM RECEIPTS PASS {date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
