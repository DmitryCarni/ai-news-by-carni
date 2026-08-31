---
layout: default
title: Home
lang: en
translation_url: /
permalink: /en/
description: "AI News by Carni filters the AI market noise into the most important daily and weekly signals for technology, deployment and business."
---

{% assign daily_reports = site.pages | where: "report_type", "daily_en" | sort: "report_date" | reverse %}
{% assign weekly_reports = site.pages | where: "report_type", "weekly_en" | sort: "report_date" | reverse %}
{% assign latest_daily = daily_reports | first %}
{% assign latest_weekly = weekly_reports | first %}

<section class="hero" style="padding-top:20px">
<h1>AI News by Carni</h1>
<p class="lead"><strong>Information noise dies here.</strong><br>The most important things in AI — daily and weekly.</p>

<div class="grid">
{% if latest_daily %}
<a class="card" href="{{ latest_daily.url | relative_url }}">
  <span class="kicker">HOT IN AI</span>
  <strong>{{ latest_daily.title | replace: "AI News:", "Top AI News —" }}</strong>
  <p>{{ latest_daily.summary | default: latest_daily.card_title | default: latest_daily.description }}</p>
</a>
{% else %}
<a class="card" href="{{ '/en/daily/' | relative_url }}">
  <span class="kicker">HOT IN AI</span>
  <strong>Top AI News</strong>
  <p>What actually matters today — without news for the sake of news.</p>
</a>
{% endif %}

{% if latest_weekly %}
<a class="card" href="{{ latest_weekly.url | relative_url }}">
  <span class="kicker">AFTER THE NOISE</span>
  <strong>Week in Review</strong>
  <p>What changed the week in AI — and why it matters.</p>
</a>
{% else %}
<a class="card" href="{{ '/en/weekly/' | relative_url }}">
  <span class="kicker">AFTER THE NOISE</span>
  <strong>Week in Review</strong>
  <p>What changed the week in AI — and why it matters.</p>
</a>
{% endif %}
</div>
</section>
