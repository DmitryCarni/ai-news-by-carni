# AI News by Carni — public site/content repository

This repository is the **public output surface** of the wider AI News by Carni system.

Public site:
`https://news.carni.ltd/`

## Repository role

Owns:
- RU/EN Daily reports;
- RU/EN Weekly reports;
- Telegram teaser source files;
- GitHub Pages layouts/assets;
- public SEO/search infrastructure.

Does **not** own:
- global project state;
- Shorts Factory architecture;
- approval/publisher state;
- project strategy;
- global working memory.

## Global source of truth

The control-plane and project-memory repository is:

`DmitryCarni/ai-news-by-carni-private`

For cross-project architecture/current state, use its startup packet:

1. `README.md`
2. `docs/PROJECT_INDEX.md`
3. `docs/WORKING_STATE.md`
4. `docs/KNOWLEDGE_BASE_MAP.md`

Do not create a competing global project-state document in this public repository.

## Local structure

- `index.md` — main page
- `daily/` — Daily reports
- `weekly/` — Weekly reports
- `en/` — English edition
- `_telegram/` — Telegram teaser source files
- `_layouts/` — site layouts
- `assets/` — public assets/styles

## GitHub Pages

Published from `main`.

Custom domain:
`news.carni.ltd`

The public repository remains authoritative for the **actual public files it contains**, while global product/architecture memory remains in the private control-plane repository.
