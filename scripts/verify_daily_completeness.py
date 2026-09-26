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

REQUIRED_EN_FRONT_MATTER = REQUIRED_RU_FRONT_MATTER + (
    "lang:",
    "translation_url:",
)

MIN_BLOCK_CHARS = 280

def h3_blocks(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^###\s+(.+?)\s*$", text))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((match.group(1).strip(), text[match.end():end].strip()))
    return blocks

def h3_count(text: str) -> int:
    return len(h3_blocks(text))

def visible_text_len(block: str) -> int:
    cleaned = re.sub(r"<[^>]+>", " ", block)
    cleaned = re.sub(r"\[[^\]]+\]\([^\)]+\)", " ", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return len(cleaned)

def verify_content_blocks(date: str, label: str, text: str, errors: list[str]) -> None:
    for title, block in h3_blocks(text):
        if '<div class="score">' not in block:
            fail(errors, f"{date}: {label} block '{title}' missing score card")
        pill_count = len(re.findall(r'<span class="pill(?:\s+[^"]*)?">', block))
        if pill_count != 3:
            fail(errors, f"{date}: {label} block '{title}' has {pill_count} score pills, expected 3")
        if "http://" not in block and "https://" not in block:
            fail(errors, f"{date}: {label} block '{title}' missing direct source URL")
        if visible_text_len(block) < MIN_BLOCK_CHARS:
            fail(
                errors,
                f"{date}: {label} block '{title}' is suspiciously thin "
                f"({visible_text_len(block)} visible chars < {MIN_BLOCK_CHARS})",
            )

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
    tg_en_path = ROOT / "_telegram" / "en" / "daily" / f"{date}.txt"

    if not ru_path.exists():
        fail(errors, f"{date}: missing RU Daily")
        return
    if not en_path.exists():
        fail(errors, f"{date}: missing EN Daily")
        return
    if not tg_path.exists():
        fail(errors, f"{date}: missing RU Telegram teaser")
    if not tg_en_path.exists():
        fail(errors, f"{date}: missing EN Telegram teaser")

    ru = ru_path.read_text(encoding="utf-8")
    en = en_path.read_text(encoding="utf-8")

    for marker in REQUIRED_RU_FRONT_MATTER:
        if marker not in ru:
            fail(errors, f"{date}: RU Daily missing front-matter field {marker}")
    for marker in REQUIRED_EN_FRONT_MATTER:
        if marker not in en:
            fail(errors, f"{date}: EN Daily missing front-matter field {marker}")

    for label, text in (("RU", ru), ("EN", en)):
        if '<div class="report-nav">' not in text:
            fail(errors, f"{date}: {label} Daily missing report navigation")
        if 'id="conclusions"' not in text:
            fail(errors, f"{date}: {label} Daily missing conclusions block")
        if h3_count(text) < 3:
            fail(errors, f"{date}: {label} Daily has only {h3_count(text)} story/opportunity blocks")
        verify_content_blocks(date, label, text, errors)

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
