---
layout: default
title: AI Daily
lang: en
translation_url: /daily/
permalink: /en/daily/
description: "AI Daily by Carni: the market signals, products, deployment patterns and business opportunities that actually mattered today."
---

{% assign reports = site.pages | where: "report_type", "daily_en" | sort: "report_date" | reverse %}

# AI Daily

<p class="lead">The signals that actually mattered today — without news for the sake of news.</p>

{% if reports.size > 0 %}
<div class="grid archive-grid">
{% for report in reports %}
<a class="card archive-card" href="{{ report.url | relative_url }}">
  <span class="kicker">{{ report.report_date_display | default: report.title }}</span>
  <strong class="archive-date">{{ report.card_title | default: report.title }}</strong>
  <p class="archive-summary">{{ report.summary | default: report.description }}</p>
</a>
{% endfor %}
</div>
{% endif %}
