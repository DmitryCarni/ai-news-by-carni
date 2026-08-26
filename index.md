---
layout: default
title: Главная
---

{% assign daily_reports = site.pages | where: "report_type", "daily" | sort: "report_date" | reverse %}
{% assign weekly_reports = site.pages | where: "report_type", "weekly" | sort: "report_date" | reverse %}
{% assign latest_daily = daily_reports | first %}
{% assign latest_weekly = weekly_reports | first %}

<section class="hero">
<h1>AI News by Carni</h1>
<p class="lead"><strong>Информационный шум умирает здесь.</strong><br>В фокусе только то, что действительно меняет рынок.</p>

<div class="grid">
{% if latest_daily %}
<a class="card" href="{{ latest_daily.url | relative_url }}">
  <span class="kicker">Новости</span>
  <strong>{{ latest_daily.title }}</strong>
  <p>{{ latest_daily.summary | default: latest_daily.description }}</p>
</a>
{% else %}
<a class="card" href="{{ '/daily/' | relative_url }}">
  <span class="kicker">Новости</span>
  <strong>Новости в AI</strong>
  <p>Главное за каждый завершённый календарный день.</p>
</a>
{% endif %}

{% if latest_weekly %}
<a class="card" href="{{ latest_weekly.url | relative_url }}">
  <span class="kicker">Главное за неделю</span>
  <strong>{{ latest_weekly.title }}</strong>
  <p>{{ latest_weekly.summary | default: latest_weekly.description }}</p>
</a>
{% else %}
<a class="card" href="{{ '/weekly/' | relative_url }}">
  <span class="kicker">Главное за неделю</span>
  <strong>Главное в AI за неделю</strong>
  <p>Сжатая картина трендов без механической склейки ежедневных новостей.</p>
</a>
{% endif %}
</div>
</section>
