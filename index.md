---
layout: default
title: Главная
---

{% assign daily_reports = site.pages | where: "report_type", "daily" | sort: "report_date" | reverse %}
{% assign weekly_reports = site.pages | where: "report_type", "weekly" | sort: "report_date" | reverse %}
{% assign latest_daily = daily_reports | first %}
{% assign latest_weekly = weekly_reports | first %}

<section class="hero" style="padding-top:20px">
<h1>AI News by Carni</h1>
<p class="lead"><strong>Информационный шум умирает здесь.</strong><br>Самое важное в ИИ — за день и за неделю.</p>

<div class="grid">
{% if latest_daily %}
{% assign daily_key = latest_daily.report_date | date: "%Y-%m-%d" %}
{% assign daily_teaser = site.data.daily_teasers[daily_key] | default: latest_daily.card_title | default: latest_daily.summary | default: latest_daily.description %}
<a class="card" href="{{ latest_daily.url | relative_url }}">
  <span class="kicker">ГОРЯЧЕЕ В ИИ</span>
  <strong>{{ latest_daily.title | replace: "ИИ новости:", "Главные новости" }}</strong>
  <p>{{ daily_teaser }}</p>
</a>
{% else %}
<a class="card" href="{{ '/daily/' | relative_url }}">
  <span class="kicker">ГОРЯЧЕЕ В ИИ</span>
  <strong>Главные новости</strong>
  <p>Что действительно важно сегодня — без новостей ради новостей.</p>
</a>
{% endif %}

{% if latest_weekly %}
<a class="card" href="{{ latest_weekly.url | relative_url }}">
  <span class="kicker">ПОСЛЕ ШУМА</span>
  <strong>Главное за неделю</strong>
  <p>Что изменило неделю в ИИ — и почему это важно.</p>
</a>
{% else %}
<a class="card" href="{{ '/weekly/' | relative_url }}">
  <span class="kicker">ПОСЛЕ ШУМА</span>
  <strong>Главное за неделю</strong>
  <p>Что изменило неделю в ИИ — и почему это важно.</p>
</a>
{% endif %}
</div>
</section>
