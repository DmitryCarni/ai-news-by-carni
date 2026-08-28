---
layout: default
title: Поиск
permalink: /search/
---

<section class="search-page">
<h1>Поиск</h1>
<form id="search-page-form" class="search-page-form" action="{{ '/search/' | relative_url }}" method="get" role="search">
  <div class="search-page-field">
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M16 16l5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    <input id="search-query" type="search" name="q" placeholder="Что ищем?" aria-label="Поиск по статьям" autocomplete="off">
    <button type="submit">Найти</button>
  </div>
</form>
<p id="search-status" class="search-status"></p>
<div id="search-results" class="search-results"></div>
</section>

<style>
.search-page{max-width:920px}
.search-page>h1{margin-bottom:22px}
.search-page-form{margin:0 0 18px}
.search-page-field{position:relative;display:flex;align-items:center;gap:10px}
.search-page-field>svg{position:absolute;left:17px;width:19px;height:19px;color:var(--muted);pointer-events:none}
.search-page-field input{min-width:0;flex:1;height:48px;border:1px solid var(--line);border-radius:999px;background:var(--panel);color:var(--text);font:inherit;font-size:16px;padding:0 18px 0 48px;outline:0;transition:border-color .2s ease,background-color .2s ease,box-shadow .2s ease}
.search-page-field input::placeholder{color:var(--muted)}
.search-page-field input:focus{border-color:#2f6feb;box-shadow:0 0 0 3px rgba(47,111,235,.12);background:var(--panel2)}
.search-page-field button{height:48px;padding:0 22px;border:1px solid var(--line);border-radius:999px;background:var(--panel2);color:var(--text);font:inherit;font-weight:650;cursor:pointer;transition:border-color .2s ease,background-color .2s ease}
.search-page-field button:hover{border-color:var(--card-hover-border);background:var(--panel)}
.search-status{min-height:26px;margin:10px 0 18px;color:var(--muted)}
.search-results{display:grid;gap:14px}
.search-result{display:block;padding:20px 22px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);color:var(--text);transition:border-color .2s ease,background-color .2s ease}
.search-result:hover{text-decoration:none;border-color:var(--card-hover-border);background:var(--panel2)}
.search-result-meta{margin-bottom:5px;color:var(--muted);font-size:12px;letter-spacing:.07em;text-transform:uppercase}
.search-result-title{display:block;font-size:20px;font-weight:750;line-height:1.3}
.search-result-snippet{margin:8px 0 0;color:var(--muted);font-size:15px;line-height:1.55}
.search-result mark{padding:.04em .16em;border-radius:4px;background:rgba(47,111,235,.28);box-shadow:inset 0 0 0 1px rgba(47,111,235,.38);color:var(--text);font-weight:650}
html[data-theme="light"] .search-result mark{background:rgba(47,111,235,.15);box-shadow:inset 0 0 0 1px rgba(47,111,235,.24)}
.search-empty{padding:22px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);color:var(--muted)}
@media(max-width:700px){
  .search-page-field{align-items:stretch;flex-direction:column}
  .search-page-field>svg{top:15px}
  .search-page-field input,.search-page-field button{width:100%}
}
</style>

<script>
(() => {
  const input = document.getElementById('search-query');
  const status = document.getElementById('search-status');
  const results = document.getElementById('search-results');
  const params = new URLSearchParams(window.location.search);
  const query = (params.get('q') || '').trim();
  input.value = query;

  document.querySelectorAll('.header-search input[name="q"]').forEach((el) => { el.value = query; });

  if (!query) {
    status.textContent = 'Ищи по компаниям, технологиям, продуктам или любому слову из статей.';
    return;
  }

  const normalize = (value) => String(value || '').toLocaleLowerCase('ru-RU').replace(/ё/g, 'е');
  const normalizedQuery = normalize(query);
  const rawTerms = query.split(/\s+/).filter(Boolean);
  const terms = normalizedQuery.split(/\s+/).filter(Boolean);

  const cleanSearchText = (value) => String(value || '')
    .replace(/Стадия:\s*(?:шум|перспективно|уже внедряется|меняет рынок)/giu, ' ')
    .replace(/(?:Монетизация|Коммерческий потенциал|Доступность|1С\/финансы|Релевантность(?: 1С\/финансам)?)\s*:\s*\d+\s*\/\s*10/giu, ' ')
    .replace(/(?:Источник|Источники|Ссылки):?/giu, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const highlightParts = rawTerms
    .map((term) => escapeRegExp(term).replace(/[её]/giu, '[её]'))
    .sort((a, b) => b.length - a.length);
  const highlightPattern = highlightParts.length ? new RegExp(`(${highlightParts.join('|')})`, 'giu') : null;

  const appendHighlightedText = (element, text) => {
    const value = String(text || '');
    if (!highlightPattern) {
      element.textContent = value;
      return;
    }

    highlightPattern.lastIndex = 0;
    let lastIndex = 0;
    let match;
    while ((match = highlightPattern.exec(value)) !== null) {
      if (match.index > lastIndex) {
        element.appendChild(document.createTextNode(value.slice(lastIndex, match.index)));
      }
      const mark = document.createElement('mark');
      mark.textContent = match[0];
      element.appendChild(mark);
      lastIndex = match.index + match[0].length;
      if (!match[0].length) break;
    }
    if (lastIndex < value.length) {
      element.appendChild(document.createTextNode(value.slice(lastIndex)));
    }
  };

  const makeSnippet = (item) => {
    const content = cleanSearchText(item.content || '');
    const teaser = cleanSearchText(item.teaser || '');
    const source = `${teaser}${teaser && content ? ' — ' : ''}${content}`;
    const normalized = normalize(source);
    let index = normalized.indexOf(normalizedQuery);
    if (index < 0) {
      index = terms.map((term) => normalized.indexOf(term)).find((pos) => pos >= 0);
    }
    if (index === undefined || index < 0) index = 0;
    const start = Math.max(0, index - 90);
    const end = Math.min(source.length, index + Math.max(query.length, 20) + 170);
    let snippet = source.slice(start, end).replace(/\s+/g, ' ').trim();
    if (start > 0) snippet = '…' + snippet;
    if (end < source.length) snippet += '…';
    return snippet;
  };

  const render = (items) => {
    results.innerHTML = '';
    if (!items.length) {
      status.textContent = `По запросу «${query}» ничего не найдено.`;
      const empty = document.createElement('div');
      empty.className = 'search-empty';
      empty.textContent = 'Попробуй другое слово или более короткую формулировку.';
      results.appendChild(empty);
      return;
    }

    status.textContent = `Найдено: ${items.length}`;
    items.forEach(({ item }) => {
      const link = document.createElement('a');
      link.className = 'search-result';
      link.href = item.url;

      const meta = document.createElement('div');
      meta.className = 'search-result-meta';
      meta.textContent = `${item.type === 'weekly' ? 'Главное за неделю' : 'Новости'}${item.date ? ' · ' + item.date : ''}`;

      const title = document.createElement('span');
      title.className = 'search-result-title';
      appendHighlightedText(title, item.title || item.teaser || 'Материал');

      const snippet = document.createElement('p');
      snippet.className = 'search-result-snippet';
      appendHighlightedText(snippet, makeSnippet(item));

      link.append(meta, title, snippet);
      results.appendChild(link);
    });
  };

  status.textContent = 'Ищу…';
  fetch('{{ '/search.json' | relative_url }}')
    .then((response) => {
      if (!response.ok) throw new Error('search index unavailable');
      return response.json();
    })
    .then((items) => {
      const found = items
        .map((item) => {
          const title = normalize(item.title);
          const teaser = normalize(item.teaser);
          const content = normalize(item.content);
          const haystack = `${title} ${teaser} ${content}`;
          if (!terms.every((term) => haystack.includes(term))) return null;

          let score = 0;
          if (title.includes(normalizedQuery)) score += 30;
          if (teaser.includes(normalizedQuery)) score += 20;
          if (content.includes(normalizedQuery)) score += 10;
          terms.forEach((term) => {
            if (title.includes(term)) score += 8;
            if (teaser.includes(term)) score += 5;
            if (content.includes(term)) score += 1;
          });
          return { item, score };
        })
        .filter(Boolean)
        .sort((a, b) => b.score - a.score);

      render(found);
    })
    .catch(() => {
      status.textContent = 'Поиск сейчас не загрузился. Обнови страницу через несколько секунд.';
    });
})();
</script>
