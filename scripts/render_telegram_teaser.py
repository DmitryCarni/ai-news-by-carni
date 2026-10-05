from __future__ import annotations

import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
GUARD_START_DATE = "2026-10-03"
CANONICAL_SECTIONS = (
    "fundamental",
    "risk",
    "applied",
    "stack",
    "finance",
    "finance-tools",
)


def front_matter_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", text)
    if not match:
        return None
    value = match.group(1).strip().split("\\n", 1)[0].strip()
    return value.strip('"').strip("'")


def section_blocks(text: str) -> list[tuple[str, str, str]]:
    matches = list(re.finditer(r"(?m)^##\s+(.+?)(?:\s+\{#([a-z0-9-]+)\})?\s*$", text))
    result: list[tuple[str, str, str]] = []
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        section_id = (match.group(2) or ("conclusions" if title in {"Итоги дня", "Day in review", "Conclusions"} else "")).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result.append((title, section_id, text[match.end():end].strip()))
    return result


def h3_blocks(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^###\s+(.+?)\s*$", text))
    result: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result.append((match.group(1).strip(), text[match.end():end].strip()))
    return result


def clean_inline(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"`([^\`]+)`", r"\1", text)
    text = re.sub(r"[*_#]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def prose_paragraphs(block: str) -> list[str]:
    result: list[str] = []
    for raw in re.split(r"\n\s*\n", block):
        paragraph = clean_inline(raw)
        if not paragraph:
            continue
        lowered = paragraph.casefold()
        if raw.lstrip().startswith("<"):
            continue
        if lowered.startswith(("источник:", "source:")):
            continue
        if "stage:" in lowered and "commercial potential:" in lowered:
            continue
        if "стадия:" in lowered and "коммерческий потенциал:" in lowered:
            continue
        result.append(paragraph)
    return result


def clip_text(text: str, *, hard: int = 320) -> str:
    text = clean_inline(text)
    if len(text) <= hard:
        return text
    shortened = text[: hard - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return shortened + "…"

def first_story(section_body: str) -> str:
    stories = h3_blocks(section_body)
    if not stories:
        raise ValueError("factual section has no ### story")
    _title, body = stories[0]
    paras = prose_paragraphs(body)
    if not paras:
        raise ValueError("factual story has no prose")
    return clip_text(paras[0], hard=320)


def conclusion_text(section_body: str) -> str:
    numbered = re.search(r"(?m)^\s*1\.\s+(.+?)\s*$", section_body)
    if numbered:
        return clip_text(numbered.group(1), hard=360)
    paras = prose_paragraphs(section_body)
    if paras:
        return clip_text(paras[0], hard=360)
    raise ValueError("conclusions section has no readable text")


def opportunity_titles(section_body: str) -> list[str]:
    titles = [clean_inline(title) for title, _ in h3_blocks(section_body)]
    return [title for title in titles if title][:3]


def render_daily_teaser(date: str, daily_text: str, lang: str) -> str:
    sections = {section_id: body for _title, section_id, body in section_blocks(daily_text) if section_id}

    missing = [section for section in CANONICAL_SECTIONS if section not in sections]
    if missing:
        raise ValueError(f"Daily {date} missing factual sections: {', '.join(missing)}")
    if "conclusions" not in sections:
        raise ValueError(f"Daily {date} missing conclusions")
    if "monetization" not in sections:
        raise ValueError(f"Daily {date} missing monetization")

    stories = [first_story(sections[section]) for section in CANONICAL_SECTIONS]
    takeaway = conclusion_text(sections["conclusions"])
    opportunities = opportunity_titles(sections["monetization"])

    display = front_matter_value(daily_text, "report_date_display") or date
    permalink = front_matter_value(daily_text, "permalink")
    if not permalink:
        permalink = f"/{'en/' if lang == 'en' else ''}daily/{date}/"
    url = "https://news.carni.ltd" + permalink

    if lang == "ru":
        parts = [f"Итоги дня за {display}", *stories, f"Главный вывод: {takeaway}"]
        if opportunities:
            parts.append("Где есть потенциал для продукта:\n" + "\n".join(f"• {item}" for item in opportunities))
        parts.extend(["Полный разбор:", url])
    elif lang == "en":
        parts = [f"AI daily — {display}", *stories, f"Key takeaway: {takeaway}"]
        if opportunities:
            parts.append("Where there is product potential:\n" + "\n".join(f"• {item}" for item in opportunities))
        parts.extend(["Full analysis:", url])
    else:
        raise ValueError(f"unsupported language: {lang}")

    teaser = "\n\n".join(part.strip() for part in parts if part.strip()).strip() + "\n"
    if len(teaser) > 3500:
        raise ValueError(f"Rendered {lang} teaser is too long: {len(teaser)} chars")
    return teaser


def render_date(date: str, write: bool) -> tuple[str, str]:
    ru_path = ROOT / "daily" / f"{date}.md"
    en_path = ROOT / "en" / "daily" / f"{date}.md"
    if not ru_path.exists() or not en_path.exists():
        raise FileNotFoundError(f"Daily pair missing for {date}")

    ru = render_daily_teaser(date, ru_path.read_text(encoding="utf-8"), "ru")
    en = render_daily_teaser(date, en_path.read_text(encoding="utf-8"), "en")

    if write:
        ru_out = ROOT / "_telegram" / "daily" / f"{date}.txt"
        en_out = ROOT / "_telegram" / "en" / "daily" / f"{date}.txt"
        ru_out.parent.mkdir(parents=True, exist_ok=True)
        en_out.parent.mkdir(parents=True, exist_ok=True)
        ru_out.write_text(ru, encoding="utf-8")
        en_out.write_text(en, encoding="utf-8")
    return ru, en


def guarded_dates() -> list[str]:
    return sorted(
        p.stem
        for p in (ROOT / "daily").glob("20??-??-??.md")
        if p.stem >= GUARD_START_DATE and (ROOT / "en" / "daily" / p.name).exists()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    dates = guarded_dates() if args.all else [args.date]
    for date in dates:
        ru, en = render_date(date, args.write)
        if not args.write:
            print(f"===== RU {date} =====")
            print(ru)
            print(f"===== EN {date} =====")
            print(en)
        else:
            print(f"Rendered canonical Telegram teasers for {date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
