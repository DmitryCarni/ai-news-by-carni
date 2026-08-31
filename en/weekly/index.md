---
layout: default
title: Week in Review
lang: en
translation_url: /weekly/
permalink: /en/weekly/
description: "AI News by Carni weekly reports: the shifts that actually mattered in AI."
---

{% assign reports = site.pages | where: "report_type", "weekly_en" | sort: "report_date" | reverse %}

# Week in Review

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
**No published reports yet.**
{% endif %}
