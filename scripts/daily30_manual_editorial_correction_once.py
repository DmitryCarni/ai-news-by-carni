#!/usr/bin/env python3
"""Exact one-off editorial repair of sealed Daily 2026-10-30.

The source archive and its per-file SHA-256 are checked by the handoff
workflow before this runs. No change to production completeness rules.
The independent public poller reproduces the same byte-level corrections.
"""
import argparse
from pathlib import Path

DATE = "2026-10-30"
SEALED_ARCHIVE_SHA256 = "30b85a0b27982bd638dcc273b04ea3fb26e3f011d917fed23157de4a51cba92a"

ADDITIONS = {
    "daily/2026-10-30.md": (
        ("Проверяемые AI-процессы для финансовых отделов",
         "В договоре пилота стоит зафиксировать перечень документов, допустимые действия агента "
         "и контрольные точки согласования с бухгалтером. Для каждой операции нужна сверка с "
         "учётной системой и журнал исключений; экономический эффект считают по времени "
         "обработки, числу исправлений и стоимости ручной проверки, а не по количеству "
         "сгенерированных ответов."),
        ("Аудит политик ИИ-краулеров для издательств",
         "Результат аудита должен включать карту правил для разных путей сайта, проверку "
         "реальных запросов по журналам сервера и список расхождений между опубликованной "
         "политикой и наблюдаемым трафиком. Отдельно нужно объяснить владельцу, какие "
         "ограничения технически проверяемы, а какие зависят от добровольного соблюдения "
         "правил конкретным роботом."),
        ("Независимый аудит окупаемости корпоративных ИИ-внедрений",
         "Независимому оценщику потребуется исходный уровень затрат до внедрения: время "
         "сотрудников, стоимость ошибок, лицензии, сопровождение и доля задач, требующих "
         "ручной доработки. Пилот следует оценивать на одинаковых типах операций и "
         "фиксированном периоде. Отчёт должен разделять подтверждённую экономию, "
         "непроверенные ожидания и риски масштабирования."),
    ),
    "en/daily/2026-10-30.md": (
        ("Auditable AI workflows for finance teams",
         "A pilot contract should define which document classes the agent may handle, "
         "which operations require an accountant's approval, and how every proposed "
         "entry is reconciled against the system of record. The acceptance report "
         "should measure time saved alongside correction rates, manual review effort "
         "and the cost of handling exceptions. Generated answers alone are not "
         "evidence of a functioning finance workflow."),
        ("Crawler preference audits for publishers",
         "The audit deliverable should map site-path rules, compare the published "
         "preferences with actual server-log requests, and flag observable mismatches. "
         "It must distinguish technically testable access controls from voluntary "
         "crawler compliance: publishing a rule does not prove every automated client "
         "will obey it. A repeatable review schedule and documented escalation "
         "process make the service useful after the first assessment."),
        ("Independent enterprise AI ROI reviews",
         "The assessment needs a baseline for staff time, error costs, licenses, "
         "maintenance and the share of work still requiring human correction. "
         "Compare similar transactions over a defined observation window and "
         "show the sensitivity of the result to usage volume and exception rates. "
         "The final report should separate realized savings from projected benefits "
         "and identify costs that increase when the pilot is scaled."),
    ),
}


def corrected_content(path: str, source: str) -> str:
    if path not in ADDITIONS:
        return source
    if source.count(f"report_date: {DATE}") != 1:
        raise ValueError("Daily30 report-date identity mismatch")
    result = source
    if path.startswith("en/"):
        if result.count("report_type: daily\n") != 1:
            raise ValueError("Expected original EN report_type: daily")
        if "\nlang:" in result or "\ntranslation_url:" in result:
            raise ValueError("EN translation metadata already present")
        permalink = "permalink: /en/daily/2026-10-30/\n"
        if result.count(permalink) != 1:
            raise ValueError("EN permalink mismatch")
        result = result.replace("report_type: daily\n", "report_type: daily_en\n", 1)
        result = result.replace(
            permalink,
            "lang: en\ntranslation_url: /daily/2026-10-30/\n" + permalink,
            1,
        )
    for heading, addition in ADDITIONS[path]:
        marker = "### " + heading + "\n\n"
        if result.count(marker) != 1:
            raise ValueError(f"Expected exactly one section: {heading}")
        start = result.index(marker) + len(marker)
        following = [
            pos for pos in (
                result.find("\n### ", start),
                result.find("\n## ", start),
                result.find("\n<div id=", start),
            ) if pos >= 0
        ]
        end = min(following) if following else len(result)
        block = result[start:end]
        delimiter = "\n\nSource:" if path.startswith("en/") else "\n\nИсточник:"
        if block.count(delimiter) != 1:
            raise ValueError(f"Expected exactly one source boundary: {heading}")
        prose, remainder = block.split(delimiter, 1)
        paragraphs = [part.strip() for part in prose.split("\n\n") if part.strip()]
        if len(paragraphs) not in (3, 4):
            raise ValueError(f"Unexpected prose paragraph count for {heading}: {len(paragraphs)}")
        if addition in prose:
            raise ValueError(f"Correction already applied: {heading}")
        corrected = prose.rstrip() + " " + addition + delimiter + remainder
        result = result[:start] + corrected + result[end:]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--archive-sha", required=True)
    args = parser.parse_args()
    if args.date != DATE or args.archive_sha != SEALED_ARCHIVE_SHA256:
        raise SystemExit("Daily30 correction refused: sealed archive identity mismatch")
    for path in ADDITIONS:
        target = Path(path)
        original = target.read_text(encoding="utf-8")
        changed = corrected_content(path, original)
        if original == changed:
            raise SystemExit(f"No expected editorial change: {path}")
        target.write_text(changed, encoding="utf-8")
        print(f"DAILY30 EDITORIAL PATCH {path}: {len(original)} -> {len(changed)}")
    print("DAILY30 EDITORIAL REPAIR APPLIED; PRODUCTION VERIFIER REQUIRED")


if __name__ == "__main__":
    main()
