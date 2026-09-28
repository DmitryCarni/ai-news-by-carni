# AI News by Carni — публичный сайт и контент

Этот репозиторий — публичная поверхность проекта AI News by Carni.

Сайт: `https://news.carni.ltd/`

## Роль репозитория

Здесь хранятся:
- RU/EN Daily;
- RU/EN Weekly;
- Telegram teaser source files;
- GitHub Pages layouts/assets;
- SEO/search infrastructure;
- публичные файлы сайта.

Здесь **не хранится глобальная база знаний проекта**.

Главный источник архитектуры, production contracts и current state:

`DmitryCarni/ai-news-by-carni-private`

Каноническая база знаний находится только в его каталоге `docs/`.

## Структура

- `index.md` — главная;
- `daily/` — RU Daily;
- `weekly/` — RU Weekly;
- `en/` — English edition;
- `_telegram/` — Telegram teaser source;
- `_layouts/` — layouts;
- `assets/` — styles/assets;
- `scripts/` — publication/verifier utilities.

## Publication

GitHub Pages публикуется из `main`.

Custom domain:

`news.carni.ltd`

Daily должен попадать в `main` только полным verified bundle. Частичные placeholder/stub-файлы недопустимы.

Редакционные правила находятся в:

`DmitryCarni/ai-news-by-carni-private/docs/AI_RADAR_RULES.md`

## Язык документации

README и техническая документация ведутся на русском.

English edition сайта остаётся английской — это продуктовый контент, а не project documentation.
