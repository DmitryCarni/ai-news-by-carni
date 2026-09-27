from __future__ import annotations

from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
START_DATE = "2026-09-24"
STRICT_RADAR_START_DATE = "2026-09-27"

CANONICAL_NEWS_SECTIONS = ("fundamental", "risk", "applied", "stack", "finance", "finance-tools")
CANONICAL_SECTION_IDS = set(CANONICAL_NEWS_SECTIONS) | {"monetization", "conclusions"}
MIN_STRICT_NEWS_BLOCKS = 5
MIN_STRICT_NEWS_SECTIONS = 4

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


def section_blocks(text: str) -> list[tuple[str, str, str]]:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)(?:\s+\{#([a-z0-9-]+)\})?\s*$", text))
    sections: list[tuple[str, str, str]] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        section_id = (match.group(2) or ("conclusions" if title in {"Итоги дня", "Day in review"} else "")).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((title, section_id, text[match.end():end].strip()))
    return sections


def strict_news_coverage(text: str) -> tuple[int, set[str], set[str]]:
    news_blocks = 0
    news_sections: set[str] = set()
    unknown_sections: set[str] = set()
    for title, section_id, body in section_blocks(text):
        if section_id and section_id not in CANONICAL_SECTION_IDS:
            unknown_sections.add(section_id)
        if section_id in CANONICAL_NEWS_SECTIONS:
            count = h3_count(body)
            if count:
                news_sections.add(section_id)
                news_blocks += count
    return news_blocks, news_sections, unknown_sections

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


def front_matter_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", text)
    return match.group(1).strip().strip('"').strip("'") if match else None


def verify_language_metadata(errors: list[str]) -> None:
    checks = (
        (ROOT / "daily", "daily", None, "RU Daily"),
        (ROOT / "en" / "daily", "daily_en", "en", "EN Daily"),
        (ROOT / "weekly", "weekly", None, "RU Weekly"),
        (ROOT / "en" / "weekly", "weekly_en", "en", "EN Weekly"),
    )
    for folder, expected_type, expected_lang, label in checks:
        for path in sorted(folder.glob("*.md")):
            if path.name == "index.md":
                continue
            text = path.read_text(encoding="utf-8")
            report_type = front_matter_value(text, "report_type")
            lang = front_matter_value(text, "lang")
            if report_type != expected_type:
                fail(errors, f"{path.relative_to(ROOT)}: {label} report_type={report_type!r}, expected {expected_type!r}")
            if expected_lang is not None and lang != expected_lang:
                fail(errors, f"{path.relative_to(ROOT)}: {label} lang={lang!r}, expected {expected_lang!r}")
            if expected_lang is None and lang == "en":
                fail(errors, f"{path.relative_to(ROOT)}: {label} must not be tagged lang=en")


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

    if date >= STRICT_RADAR_START_DATE:
        for label, text in (("RU", ru), ("EN", en)):
            news_blocks, news_sections, unknown_sections = strict_news_coverage(text)
            if unknown_sections:
                fail(errors, f"{date}: {label} Daily uses non-canonical section ids: {', '.join(sorted(unknown_sections))}")
            if news_blocks < MIN_STRICT_NEWS_BLOCKS:
                fail(errors, f"{date}: {label} Daily has only {news_blocks} factual news blocks; expected at least {MIN_STRICT_NEWS_BLOCKS} (business opportunities do not count)")
            if len(news_sections) < MIN_STRICT_NEWS_SECTIONS:
                fail(errors, f"{date}: {label} Daily covers only {len(news_sections)} canonical news rubrics; expected at least {MIN_STRICT_NEWS_SECTIONS} of {len(CANONICAL_NEWS_SECTIONS)}")

    teaser_count = telegram_story_count(tg_path)
    if teaser_count and ru_h3 < teaser_count:
        fail(
            errors,
            f"{date}: Daily has {ru_h3} blocks but Telegram teaser contains {teaser_count} news items",
        )

def main() -> int:
    errors: list[str] = []
    verify_language_metadata(errors)
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
