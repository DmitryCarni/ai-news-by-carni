---
layout: default
title: News
lang: en
translation_url: /daily/
permalink: /en/daily/
description: "All published AI News by Carni daily reports by date."
---

{% assign reports = site.pages | where: "report_type", "daily_en" | sort: "report_date" | reverse %}

# News

All published reports by date.

{% if reports.size > 0 %}
<div class="grid archive-grid">
{% for report in reports %}
<a class="card archive-card" href="{{ report.url | relative_url }}">
  <strong class="archive-date">{{ report.report_date_display | default: report.title }}</strong>
  <p class="archive-summary">{{ report.summary | default: report.card_title | default: report.description }}</p>
</a>
{% endfor %}
</div>
{% else %}
**No news yet.**
{% endif %}
