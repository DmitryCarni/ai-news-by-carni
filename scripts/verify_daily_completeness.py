from __future__ import annotations

from datetime import date as Date, timedelta
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
START_DATE = "2026-09-24"
STRICT_RADAR_START_DATE = "2026-09-27"
FULL_RUBRIC_START_DATE = "2026-09-28"
STORY_DEPTH_START_DATE = "2026-10-01"
RU_LANGUAGE_GUARD_START_DATE = "2026-10-01"

CANONICAL_NEWS_SECTIONS = ("fundamental", "risk", "applied", "stack", "finance", "finance-tools")
CANONICAL_SECTION_IDS = set(CANONICAL_NEWS_SECTIONS) | {"monetization", "conclusions"}
LEGACY_2026_09_27_MIN_NEWS_BLOCKS = 4
LEGACY_2026_09_27_MIN_NEWS_SECTIONS = 3

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
MIN_FACTUAL_DEPTH_CHARS = 700
MIN_FACTUAL_PROSE_PARAGRAPHS = 3
MIN_MONETIZATION_DEPTH_CHARS = 650
MIN_MONETIZATION_PROSE_PARAGRAPHS = 3

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


def section_h3_count(text: str, target_section_id: str) -> int:
    for _title, section_id, body in section_blocks(text):
        if section_id == target_section_id:
            return h3_count(body)
    return 0


def factual_headlines(text: str) -> set[str]:
    headlines: set[str] = set()
    for _title, section_id, body in section_blocks(text):
        if section_id not in CANONICAL_NEWS_SECTIONS:
            continue
        for title, _block in h3_blocks(body):
            normalized = re.sub(r"[^0-9a-zа-яё]+", " ", title.casefold(), flags=re.I).strip()
            if normalized:
                headlines.add(normalized)
    return headlines


def report_nav_targets(text: str) -> set[str]:
    match = re.search(r'<div class="report-nav">(.*?)</div>', text, flags=re.S)
    if not match:
        return set()
    return set(re.findall(r'href="#([a-z0-9-]+)"', match.group(1)))

def conclusions_numbered(text: str) -> bool:
    match = re.search(r'<div id="conclusions"[^>]*>(.*?)</div>', text, flags=re.S)
    if not match:
        return False
    numbered = re.findall(r"(?m)^\s*\d+\.\s+\S", match.group(1))
    return len(numbered) >= 2


def visible_text_len(block: str) -> int:
    cleaned = re.sub(r"<[^>]+>", " ", block)
    cleaned = re.sub(r"\[[^\]]+\]\([^\)]+\)", " ", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return len(cleaned)

def factual_prose_paragraphs(block: str) -> list[str]:
    analysis = block.split('<div class="score">', 1)[0].strip()
    paragraphs: list[str] = []
    for raw in re.split(r"\n\s*\n", analysis):
        paragraph = raw.strip()
        if not paragraph:
            continue
        if paragraph.startswith(("<", "Источник:", "Источники:", "Source:", "Sources:")):
            continue
        paragraphs.append(paragraph)
    return paragraphs


def verify_story_depth(date: str, label: str, text: str, errors: list[str]) -> None:
    if date < STORY_DEPTH_START_DATE:
        return
    for _section_title, section_id, body in section_blocks(text):
        if section_id in CANONICAL_NEWS_SECTIONS:
            min_paragraphs = MIN_FACTUAL_PROSE_PARAGRAPHS
            min_chars = MIN_FACTUAL_DEPTH_CHARS
            kind = "factual"
        elif section_id == "monetization":
            min_paragraphs = MIN_MONETIZATION_PROSE_PARAGRAPHS
            min_chars = MIN_MONETIZATION_DEPTH_CHARS
            kind = "monetization"
        else:
            continue

        for title, block in h3_blocks(body):
            paragraphs = factual_prose_paragraphs(block)
            analysis = block.split('<div class="score">', 1)[0].strip()
            if len(paragraphs) < min_paragraphs:
                fail(
                    errors,
                    f"{date}: {label} {kind} block '{title}' has only "
                    f"{len(paragraphs)} prose paragraphs; expected at least "
                    f"{min_paragraphs} for site-depth coverage",
                )
            if visible_text_len(analysis) < min_chars:
                fail(
                    errors,
                    f"{date}: {label} {kind} block '{title}' is too thin for "
                    f"site-depth coverage ({visible_text_len(analysis)} visible chars < "
                    f"{min_chars})",
                )


RU_AVOIDABLE_ENGLISH_PATTERNS = (
    (r"\bpermissions?\b", "права доступа"),
    (r"\btool calls?\b", "вызов инструмента"),
    (r"\baudit log\b", "журнал аудита"),
    (r"\bpolicy enforcement\b", "контроль/применение правил доступа"),
    (r"\bcoding agents?\b", "агенты для программирования"),
    (r"\binfra agents?\b", "инфраструктурные агенты"),
    (r"\bfinancial assistants?\b", "финансовые помощники"),
    (r"\bmodel-agnostic\b", "независимый от конкретной модели"),
    (r"\btool layer\b", "слой инструментов"),
    (r"\bsandboxed\b", "изолирован в песочнице"),
    (r"\bread-only-first\b", "сначала только чтение"),
    (r"\bhuman approval\b", "подтверждение человеком"),
    (r"\bsecret redaction\b", "сокрытие секретов"),
    (r"\bspend/rate limits\b", "лимиты расходов и частоты вызовов"),
    (r"\bincident replay\b", "восстановление хода инцидента"),
    (r"\bcontrolled availability\b", "ограниченный доступ"),
    (r"\bconsumption-model\b", "оплата по потреблению"),
    (r"\bcustomer support\b", "поддержка клиентов"),
    (r"\bend-to-end\b", "сквозной"),
    (r"\brealtime\b", "в реальном времени"),
)


def verify_ru_readability(date: str, text: str, errors: list[str]) -> None:
    if date < RU_LANGUAGE_GUARD_START_DATE:
        return

    prose = re.sub(r"https?://\S+", " ", text)
    prose = re.sub(r"(?m)^(?:Источник|Источники):.*$", " ", prose)
    prose = re.sub(r"`[^`]+`", " ", prose)

    for pattern, russian_hint in RU_AVOIDABLE_ENGLISH_PATTERNS:
        match = re.search(pattern, prose, flags=re.I)
        if match:
            fail(
                errors,
                f"{date}: RU Daily contains avoidable English '{match.group(0)}'; "
                f"use natural Russian such as '{russian_hint}' unless it is an exact official identifier",
            )


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
        verify_story_depth(date, label, text, errors)

    verify_ru_readability(date, ru, errors)

    ru_h3 = h3_count(ru)
    en_h3 = h3_count(en)
    if ru_h3 != en_h3:
        fail(errors, f"{date}: RU/EN block count mismatch ({ru_h3} vs {en_h3})")

    if date >= STRICT_RADAR_START_DATE:
        for label, text in (("RU", ru), ("EN", en)):
            news_blocks, news_sections, unknown_sections = strict_news_coverage(text)
            if unknown_sections:
                fail(errors, f"{date}: {label} Daily uses non-canonical section ids: {', '.join(sorted(unknown_sections))}")
            if date >= FULL_RUBRIC_START_DATE:
                missing_sections = [section for section in CANONICAL_NEWS_SECTIONS if section not in news_sections]
                if missing_sections:
                    fail(errors, f"{date}: {label} Daily is missing mandatory factual rubrics: {', '.join(missing_sections)}")
                if news_blocks < len(CANONICAL_NEWS_SECTIONS):
                    fail(errors, f"{date}: {label} Daily has only {news_blocks} factual news blocks; expected at least one story in each of {len(CANONICAL_NEWS_SECTIONS)} factual rubrics")
                if section_h3_count(text, "monetization") < 1:
                    fail(errors, f"{date}: {label} Daily is missing mandatory business-opportunity analysis")
                required_nav = set(CANONICAL_NEWS_SECTIONS) | {"monetization", "conclusions"}
                missing_nav = sorted(required_nav - report_nav_targets(text))
                if missing_nav:
                    fail(errors, f"{date}: {label} Daily report-nav is missing mandatory anchors: {', '.join(missing_nav)}")
            else:
                if news_blocks < LEGACY_2026_09_27_MIN_NEWS_BLOCKS:
                    fail(errors, f"{date}: {label} Daily has only {news_blocks} factual news blocks; expected at least {LEGACY_2026_09_27_MIN_NEWS_BLOCKS}")
                if len(news_sections) < LEGACY_2026_09_27_MIN_NEWS_SECTIONS:
                    fail(errors, f"{date}: {label} Daily covers only {len(news_sections)} factual rubrics; expected at least {LEGACY_2026_09_27_MIN_NEWS_SECTIONS}")

            if not conclusions_numbered(text):
                fail(errors, f"{date}: {label} Daily conclusions must contain at least 2 numbered takeaways")

        if date >= FULL_RUBRIC_START_DATE:
            previous_date = str(Date.fromisoformat(date) - timedelta(days=1))
            previous_ru_path = ROOT / "daily" / f"{previous_date}.md"
            if previous_ru_path.exists():
                duplicates = factual_headlines(ru) & factual_headlines(previous_ru_path.read_text(encoding="utf-8"))
                if duplicates:
                    fail(errors, f"{date}: RU Daily repeats factual headline(s) from {previous_date}: {', '.join(sorted(duplicates))}")

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
