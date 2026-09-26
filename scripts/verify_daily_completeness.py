from __future__ import annotations

from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
START_DATE = "2026-09-24"

REQUIRED_RU_FRONT_MATTER = (
    "layout:",
    "report_type:",
    "report_date:",
    "report_date_display:",
    "card_title:",
    "summary:",
    "title:",
    "description:",
    "permalink:",
)

def h3_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("### "))

def telegram_story_count(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(("Итоги дня", "Главный вывод", "Полный разбор")):
            continue
        first = line[0]
        if unicodedata.category(first) in {"So", "Sk"}:
            count += 1
    return count

def fail(errors: list[str], message: str) -> None:
    errors.append(message)

def verify_date(date: str, errors: list[str]) -> None:
    ru_path = ROOT / "daily" / f"{date}.md"
    en_path = ROOT / "en" / "daily" / f"{date}.md"
    tg_path = ROOT / "_telegram" / "daily" / f"{date}.txt"

    if not ru_path.exists():
        fail(errors, f"{date}: missing RU Daily")
        return
    if not en_path.exists():
        fail(errors, f"{date}: missing EN Daily")
        return

    ru = ru_path.read_text(encoding="utf-8")
    en = en_path.read_text(encoding="utf-8")

    for marker in REQUIRED_RU_FRONT_MATTER:
        if marker not in ru:
            fail(errors, f"{date}: RU Daily missing front-matter field {marker}")

    for label, text in (("RU", ru), ("EN", en)):
        if '<div class="report-nav">' not in text:
            fail(errors, f"{date}: {label} Daily missing report navigation")
        if 'id="conclusions"' not in text:
            fail(errors, f"{date}: {label} Daily missing conclusions block")
        if h3_count(text) < 3:
            fail(errors, f"{date}: {label} Daily has only {h3_count(text)} story/opportunity blocks")

    ru_h3 = h3_count(ru)
    en_h3 = h3_count(en)
    if ru_h3 != en_h3:
        fail(errors, f"{date}: RU/EN block count mismatch ({ru_h3} vs {en_h3})")

    teaser_count = telegram_story_count(tg_path)
    if teaser_count and ru_h3 < teaser_count:
        fail(
            errors,
            f"{date}: Daily has {ru_h3} blocks but Telegram teaser contains {teaser_count} news items",
        )

def main() -> int:
    errors: list[str] = []
    dates = sorted(
        p.stem
        for p in (ROOT / "daily").glob("20??-??-??.md")
        if p.stem >= START_DATE
    )
    if not dates:
        print("No Daily reports found in guarded range")
        return 1

    for date in dates:
        verify_date(date, errors)

    if errors:
        print("Daily completeness verification FAILED:")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"Daily completeness verification passed for {len(dates)} report(s): {', '.join(dates)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
