#!/usr/bin/env python3
"""One-off reviewable editorial corrections to the SEALED Daily29 archive.

Never loosens completeness checks, never modifies the signed archive or
any other date. The corrected public bytes are independently reproduced
by the OIDC poller's final 4/4 content readback.
"""
import argparse
from pathlib import Path

DATE = "2026-10-29"
SEALED_ARCHIVE_SHA256 = "43435e54d41aa046ba2ec01cc8921e7eb30e2655612a6ebe8d4fa938379f2d61"
HEADINGS = {
    "daily/2026-10-29.md": (
        ("Аудит происхождения и безопасности ИИ-расширений",
         "В отчёт пилота нужно отдельно включить список поддерживаемых версий, "
         "правила допуска новых обновлений и способ оповещения при отзыве пакета. "
         "Руководитель разработки получает перечень измеримых рисков и согласованный "
         "план действий для каждого класса инцидента. Внедрение не должно требовать "
         "передачи секретов проверяющей системе или установки непроверенного кода."),
        ("Безопасные браузерные агенты для процессов без API",
         "Чтобы сравнить решение с ручной работой, следует заранее фиксировать "
         "исходные данные и ожидаемое состояние целевого сервиса. После каждого "
         "сеанса независимая проверка должна подтвердить результат и сохранить "
         "доказательство, а при неизвестном экране агент прекращает изменения. "
         "Отдельно оцениваются стоимость сопровождения и риски случайной отправки "
         "данных за пределы разрешённого кабинета."),
        ("ИИ-маршрутизация сервисных заявок и внутренних согласований",
         "Коммерческий формат можно построить из первичного обследования, "
         "настройки набора сценариев и ограниченного сопровождения. Изменение "
         "критически важных разрешений должно требовать решения назначенного "
         "ответственного, а любое отклонение от известного маршрута — создавать "
         "эскалацию, а не скрытую автоматическую попытку. Это позволяет измерить "
         "пользу без передачи ИИ неограниченных административных полномочий."),
    ),
    "en/daily/2026-10-29.md": (
        ("AI extension provenance and security audits",
         "A useful deliverable would also define an approved-version register, "
         "a process for emergency withdrawal of compromised packages and a "
         "named owner for reviewing alerts. An independent acceptance exercise "
         "should verify that risky changes are detected without collecting "
         "credentials or installing untrusted binaries. These controls can "
         "be priced and maintained separately from ordinary developer support."),
        ("Controlled browser agents for workflows without APIs",
         "Before deployment, the customer and integrator should agree on "
         "observable success criteria, permissible websites and a clear "
         "incident-stop rule. Every completed job needs evidence from the "
         "target system rather than a model-generated assertion. Maintenance "
         "cost, site redesigns and data-leakage exposure must be included "
         "in the pilot economics, not deferred until after rollout."),
        ("AI-assisted service tickets and internal approvals",
         "A practical engagement could separate initial process mapping, "
         "a constrained implementation and ongoing exception reviews. "
         "Policy exceptions and privileged access changes should route to "
         "a named human approver, with immutable records of the original "
         "request and final decision. Such evidence gives customers a way "
         "to assess both the cost savings and the operational risks."),
    ),
}

def corrected_content(path: str, source: str) -> str:
    if path not in HEADINGS:
        return source
    if f"report_date: {DATE}" not in source:
        raise ValueError("Daily29 source identity mismatch")
    result = source
    for heading, paragraph in HEADINGS[path]:
        marker = "### " + heading + "\n\n"
        if result.count(marker) != 1:
            raise ValueError(f"Expected exactly one {heading!r} section")
        start = result.index(marker) + len(marker)
        next_starts = [p for p in (
            result.find("\n### ", start),
            result.find("\n## ", start),
            result.find("\n<div id=", start),
        ) if p >= 0]
        end = min(next_starts) if next_starts else len(result)
        section = result[start:end]
        delimiter = "\n\nИсточник:" if path.startswith("daily/") else "\n\nSource:"
        if section.count(delimiter) != 1:
            raise ValueError(f"Expected one source boundary: {heading}")
        pre, post = section.split(delimiter)
        if pre.count("\n\n") != 1:
            raise ValueError(f"Expected exactly two original prose paragraphs: {heading}")
        if paragraph in pre:
            raise ValueError(f"Correction already present: {heading}")
        result = result[:start] + pre + "\n\n" + paragraph + delimiter + post + result[end:]
    if path.startswith("daily/"):
        if "Coding Agent" not in result:
            raise ValueError("Expected Russian Coding Agent terminology is missing")
        result = result.replace("Artificial Analysis Coding Agent Index", "индексе оценки агентов для программирования Artificial Analysis")
        result = result.replace("Coding Agent", "агенты для программирования")
        if "Coding Agent" in result:
            raise ValueError("Untranslated phrase remains")
    return result

def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--date", required=True)
    cli.add_argument("--archive-sha", required=True)
    args = cli.parse_args()
    if args.date != DATE or args.archive_sha != SEALED_ARCHIVE_SHA256:
        raise SystemExit("Correction is restricted to exact previously rejected sealed Daily29")
    for path in HEADINGS:
        file = Path(path)
        old = file.read_text(encoding="utf-8")
        new = corrected_content(path, old)
        if old == new:
            raise SystemExit("No expected correction applied")
        file.write_text(new, encoding="utf-8")
        print(f"DAILY29 EDITORIAL PATCH {path}: {len(old)} -> {len(new)}")
    print("DAILY29 MANUAL CORRECTION APPLIED; PRODUCTION VERIFIER STILL REQUIRED")

if __name__ == "__main__":
    main()
