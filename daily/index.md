---
layout: default
title: Новости
permalink: /daily/
---

{% assign reports = site.pages | where: "report_type", "daily" | sort: "report_date" | reverse %}

# Новости

Все опубликованные выпуски по датам.

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
**Новостей пока нет.**
{% endif %}
