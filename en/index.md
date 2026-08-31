---
layout: default
title: English Edition
lang: en
translation_url: /
permalink: /en/
description: "AI News by Carni filters the AI market noise into one weekly view of the shifts that actually matter for technology, deployment and business."
---

{% assign weekly_reports = site.pages | where: "report_type", "weekly_en" | sort: "report_date" | reverse %}
{% assign latest_weekly = weekly_reports | first %}

<section class="hero" style="padding-top:20px">
<h1>AI News by Carni</h1>
<p class="lead"><strong>The noise stops here.</strong><br>What actually mattered in AI — once a week.</p>

<div class="grid">
{% if latest_weekly %}
<a class="card" href="{{ latest_weekly.url | relative_url }}">
  <span class="kicker">AFTER THE NOISE</span>
  <strong>{{ latest_weekly.card_title | default: latest_weekly.title }}</strong>
  <p>{{ latest_weekly.summary | default: latest_weekly.description }}</p>
</a>
{% else %}
<a class="card" href="{{ '/en/weekly/' | relative_url }}">
  <span class="kicker">AFTER THE NOISE</span>
  <strong>AI Weekly</strong>
  <p>The shifts that changed the week in AI — and why they matter.</p>
</a>
{% endif %}

<a class="card" href="{{ '/' | relative_url }}">
  <span class="kicker">RUSSIAN EDITION</span>
  <strong>Daily + Weekly</strong>
  <p>The full Russian edition includes daily reports and the weekly radar.</p>
</a>
</div>
</section>
