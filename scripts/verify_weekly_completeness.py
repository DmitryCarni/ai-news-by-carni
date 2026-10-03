from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
START_WEEK = "2026-W40"
MIN_FACTUAL_SECTIONS = 4
MIN_FACTUAL_BLOCKS = 4
MIN_MONETIZATION_BLOCKS = 2
MIN_CONCLUSIONS = 3
MIN_BLOCK_CHARS = 520

def fail(errors: list[str], message: str) -> None:
    errors.append(message)

def front_matter_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", text)
    return match.group(1).strip().strip('"').strip("'") if match else None

def section_blocks(text: str) -> list[tuple[str, str, str]]:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)(?:\s+\{#([a-z0-9-]+)\})?\s*$", text))
    result = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        title = match.group(1).strip()
        section_id = (match.group(2) or ("conclusions" if title in {"Итоги недели", "Week in review"} else "")).strip()
        result.append((title, section_id, text[match.end():end].strip()))
    return result

def h3_blocks(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^###\s+(.+?)\s*$", text))
    result = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result.append((match.group(1).strip(), text[match.end():end].strip()))
    return result

def visible_text_len(text: str) -> int:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text)

def verify_week(week: str, errors: list[str]) -> None:
    ru_path = ROOT / "weekly" / f"{week}.md"
    en_path = ROOT / "en" / "weekly" / f"{week}.md"
    ru_t_path = ROOT / "_telegram" / "weekly" / f"{week}.txt"
    en_t_path = ROOT / "_telegram" / "en" / "weekly" / f"{week}.txt"

    for path in (ru_path, en_path, ru_t_path, en_t_path):
        if not path.exists():
            fail(errors, f"{week}: missing bundle artifact {path.relative_to(ROOT)}")
    if any(not p.exists() for p in (ru_path, en_path, ru_t_path, en_t_path)):
        return

    ru = ru_path.read_text(encoding="utf-8")
    en = en_path.read_text(encoding="utf-8")
    ru_t = ru_t_path.read_text(encoding="utf-8").strip()
    en_t = en_t_path.read_text(encoding="utf-8").strip()

    expected_ru_permalink = f"/weekly/{week}/"
    expected_en_permalink = f"/en/weekly/{week}/"
    if front_matter_value(ru, "report_type") != "weekly":
        fail(errors, f"{week}: RU report_type must be weekly")
    if front_matter_value(en, "report_type") != "weekly_en":
        fail(errors, f"{week}: EN report_type must be weekly_en")
    if front_matter_value(en, "lang") != "en":
        fail(errors, f"{week}: EN lang must be en")
    if front_matter_value(ru, "permalink") != expected_ru_permalink:
        fail(errors, f"{week}: RU permalink must be {expected_ru_permalink}")
    if front_matter_value(en, "permalink") != expected_en_permalink:
        fail(errors, f"{week}: EN permalink must be {expected_en_permalink}")
    if front_matter_value(en, "translation_url") != expected_ru_permalink:
        fail(errors, f"{week}: EN translation_url must point to RU Weekly")

    for label, text in (("RU", ru), ("EN", en)):
        sections = section_blocks(text)
        factual_sections = 0
        factual_blocks = 0
        monetization_blocks = 0
        conclusions_body = ""
        for _title, section_id, body in sections:
            count = len(h3_blocks(body))
            if section_id == "monetization":
                monetization_blocks += count
            elif section_id == "conclusions":
                conclusions_body = body
            elif section_id:
                if count:
                    factual_sections += 1
                    factual_blocks += count

        if factual_sections < MIN_FACTUAL_SECTIONS:
            fail(errors, f"{week}: {label} Weekly has {factual_sections} factual sections; expected at least {MIN_FACTUAL_SECTIONS}")
        if factual_blocks < MIN_FACTUAL_BLOCKS:
            fail(errors, f"{week}: {label} Weekly has {factual_blocks} factual story blocks; expected at least {MIN_FACTUAL_BLOCKS}")
        if monetization_blocks < MIN_MONETIZATION_BLOCKS:
            fail(errors, f"{week}: {label} Weekly has {monetization_blocks} business opportunities; expected at least {MIN_MONETIZATION_BLOCKS}")

        conclusion_count = len(re.findall(r"(?m)^\s*(?:\d+\.|-)\s+\S", conclusions_body))
        if conclusion_count < MIN_CONCLUSIONS:
            fail(errors, f"{week}: {label} Weekly has {conclusion_count} conclusions; expected at least {MIN_CONCLUSIONS}")

        for title, block in h3_blocks(text):
            if '<div class="score">' not in block:
                fail(errors, f"{week}: {label} block '{title}' missing score card")
            pills = len(re.findall(r'<span class="pill(?:\s+[^"]*)?">', block))
            if pills != 3:
                fail(errors, f"{week}: {label} block '{title}' has {pills} score pills; expected 3")
            if visible_text_len(block.split('<div class="score">', 1)[0]) < MIN_BLOCK_CHARS:
                fail(errors, f"{week}: {label} block '{title}' is suspiciously thin")
            if not re.search(r"(?m)^(?:Источник|Источники|Source|Sources):\s+.+", block):
                fail(errors, f"{week}: {label} block '{title}' missing source line")

    if len(h3_blocks(ru)) != len(h3_blocks(en)):
        fail(errors, f"{week}: RU/EN Weekly story counts differ ({len(h3_blocks(ru))} vs {len(h3_blocks(en))})")

    ru_url = f"https://news.carni.ltd/weekly/{week}/"
    en_url = f"https://news.carni.ltd/en/weekly/{week}/"
    if ru_url not in ru_t:
        fail(errors, f"{week}: RU teaser missing exact Weekly URL")
    if en_url not in en_t:
        fail(errors, f"{week}: EN teaser missing exact Weekly URL")
    if len(ru_t) < 300 or len(en_t) < 300:
        fail(errors, f"{week}: Weekly teaser is suspiciously short")

def main() -> int:
    errors: list[str] = []
    weeks = sorted(
        p.stem for p in (ROOT / "weekly").glob("2026-W*.md")
        if p.stem >= START_WEEK
    )
    if not weeks:
        fail(errors, f"No Weekly files found from {START_WEEK}")

    for week in weeks:
        verify_week(week, errors)

    if errors:
        print("WEEKLY COMPLETENESS: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("WEEKLY COMPLETENESS: PASS")
    print("Verified:", ", ".join(weeks))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
