---
layout: default
title: English Edition
lang: en
translation_url: /
permalink: /en/
description: "AI News by Carni filters the AI market noise into daily signals and a weekly view of the shifts that actually matter for technology, deployment and business."
---

{% assign daily_reports = site.pages | where: "report_type", "daily_en" | sort: "report_date" | reverse %}
{% assign weekly_reports = site.pages | where: "report_type", "weekly_en" | sort: "report_date" | reverse %}
{% assign latest_daily = daily_reports | first %}
{% assign latest_weekly = weekly_reports | first %}

<section class="hero" style="padding-top:20px">
<h1>AI News by Carni</h1>
<p class="lead"><strong>The noise stops here.</strong><br>What matters in AI — every day, then after the noise, every week.</p>

<div class="grid">
{% if latest_daily %}
<a class="card" href="{{ latest_daily.url | relative_url }}">
  <span class="kicker">HOT IN AI</span>
  <strong>{{ latest_daily.card_title | default: latest_daily.title }}</strong>
  <p>{{ latest_daily.summary | default: latest_daily.description }}</p>
</a>
{% else %}
<a class="card" href="{{ '/en/daily/' | relative_url }}">
  <span class="kicker">HOT IN AI</span>
  <strong>AI Daily</strong>
  <p>The signals that actually mattered today — without news for the sake of news.</p>
</a>
{% endif %}

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
</div>
</section>
