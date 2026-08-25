---
layout: default
title: Еженедельные отчёты
permalink: /weekly/
---

{% assign reports = site.pages | where: "report_type", "weekly" | sort: "report_date" | reverse %}

# Еженедельные отчёты

Не семь склеенных ежедневных выпусков, а изменения, которые действительно подтвердились, усилились или потеряли значение.

{% if reports.size > 0 %}
<div class="grid">
{% for report in reports %}
<a class="card" href="{{ report.url | relative_url }}">
  <span class="kicker">{{ report.report_date_display | default: report.title }}</span>
  <strong>{{ report.card_title | default: report.title }}</strong>
  <p>{{ report.summary | default: report.description }}</p>
</a>
{% endfor %}
</div>
{% else %}
**Опубликованных недельных отчётов пока нет.**
{% endif %}
