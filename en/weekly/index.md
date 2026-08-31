---
layout: default
title: AI Weekly
lang: en
translation_url: /weekly/
permalink: /en/weekly/
description: "AI Weekly by Carni: the market shifts, products, deployment patterns and business opportunities that actually mattered this week."
---

{% assign reports = site.pages | where: "report_type", "weekly_en" | sort: "report_date" | reverse %}

# AI Weekly

<p class="lead">Not seven daily reports stitched together. One weekly view of what strengthened, reached production, lost relevance or changed the economics of AI.</p>

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
{% endif %}
