---
layout: default
title: Главная
---

{% assign daily_reports = site.pages | where: "report_type", "daily" | sort: "report_date" | reverse %}
{% assign weekly_reports = site.pages | where: "report_type", "weekly" | sort: "report_date" | reverse %}
{% assign latest_daily = daily_reports | first %}
{% assign latest_weekly = weekly_reports | first %}

<section class="hero">
<span class="eyebrow">AI-радар рынка</span>
<h1>AI News by Carni</h1>
<p class="lead">Не поток AI-новостей, а радар изменений: куда движется отрасль, где появляется экономический сигнал, какие технологии уже можно применять и что происходит отдельно в 1С и финансах.</p>

<div class="grid">
{% if latest_daily %}
<a class="card" href="{{ latest_daily.url | relative_url }}">
  <span class="kicker">Последний ежедневный отчёт</span>
  <strong>{{ latest_daily.report_date_display | default: latest_daily.title }}</strong>
  <p>{{ latest_daily.summary | default: latest_daily.description }}</p>
</a>
{% else %}
<a class="card" href="{{ '/daily/' | relative_url }}">
  <span class="kicker">Ежедневный отчёт</span>
  <strong>Ежедневный радар</strong>
  <p>Полный AI-радар за каждый завершённый календарный день.</p>
</a>
{% endif %}

{% if latest_weekly %}
<a class="card" href="{{ latest_weekly.url | relative_url }}">
  <span class="kicker">Последний еженедельный отчёт</span>
  <strong>{{ latest_weekly.report_date_display | default: latest_weekly.title }}</strong>
  <p>{{ latest_weekly.summary | default: latest_weekly.description }}</p>
</a>
{% else %}
<a class="card" href="{{ '/weekly/' | relative_url }}">
  <span class="kicker">Еженедельный отчёт</span>
  <strong>Еженедельный радар</strong>
  <p>Сжатая картина трендов без механической склейки ежедневных новостей.</p>
</a>
{% endif %}
</div>
</section>
