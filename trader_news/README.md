# trader_news

A-share financial news aggregation and processing module. Part of the a-stock-info platform (v2.0).

## Overview

`trader_news` is a specialized microservice for collecting, storing, and serving financial news related to the Chinese A-share market. It provides:

- **Multi-source news collection** — RSS feeds, web scraping, API-based news aggregation
- **News-crawling engine** — Background scheduler with retry, idempotent UPSERT writes
- **Sentiment analysis pipeline** — Lightweight NLP scoring (snownlp) for news sentiment
- **Stock relation tagging** — Automatic association of news items with related stock codes
- **REST API** — Searchable, paginated news endpoints
- **Caching layer** — Redis-backed (with in-memory fallback) for high-frequency queries

## Architecture

```
Data Sources (东方财富 / 财联社 / RSS)
        │
        ▼
Scheduler (APScheduler, every 30min)
        │
        ▼
Collection → Dedup (URL hash) → Sentiment → Storage → API
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Collection | `httpx`, `BeautifulSoup4`, `feedparser` |
| Scheduling | `APScheduler` |
| Backend | `FastAPI` + `SQLAlchemy 2.0` |
| Database | `SQLite` (dev) / `PostgreSQL` (prod) |
| Cache | `Redis` (optional, degrades to in-memory) |
| Testing | `pytest` + `pytest-asyncio` |

## Quick Start

```bash
# Clone
git clone https://github.com/Sphrexil/trader_news.git
cd trader_news

# Install dependencies
pip install -r requirements.txt

# Run (SQLite by default, zero config)
uvicorn main:app --reload

# With Redis caching (optional)
REDIS_URL=redis://localhost:6379/0 uvicorn main:app --reload
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/news` | List/search news (supports `ts_code`, `source`, `page`) |
| `GET` | `/api/v1/news/sources` | Available news sources |
| `GET` | `/api/v1/system/status` | Service health + scheduler jobs |

## Project Structure

```
.
├── main.py              # FastAPI entry point
├── config.py            # Environment-based settings
├── database.py          # SQLAlchemy engine + session
├── models/
│   └── news.py          # News ORM model
├── schemas/
│   ├── common.py        # ApiResponse, PaginatedData
│   └── news.py          # News schemas
├── routers/
│   ├── news.py          # News endpoints
│   └── system.py        # Health/status endpoints
├── services/
│   ├── news_service.py  # Business logic
│   └── sentiment.py     # NLP sentiment analysis
├── crawlers/
│   ├── base.py          # BaseCrawler with retry/UPSERT
│   ├── eastmoney.py     # 东方财富 crawler
│   ├── cls.py           # 财联社 crawler
│   └── rss.py           # Generic RSS crawler
├── scheduler.py         # APScheduler job registration
├── cache.py             # Redis/memory cache
├── requirements.txt
├── githooks/            # Git hook scripts
│   ├── pre-commit       # Lint staged files
│   ├── commit-msg       # Conventional commits enforcement
│   └── prepare-commit-msg
├── .github/             # PR + issue templates
└── .gitattributes       # Line-ending normalization
```

## Git Workflow

- **Branching**: `main` (stable) ← `dev` (integration) ← `feat/*` / `fix/*` / `chore/*`
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) enforced by `commit-msg` hook
- **Pre-commit**: Auto-runs `ruff` on Python files, `eslint` + `prettier` on JS files
- **Merge**: `git merge --no-ff` only, no fast-forward

```bash
# Hooks are pre-configured — just clone and go:
git config core.hooksPath githooks  # auto-set on first push recommendation
```

## Sentiment Scoring

News items are scored from -1 (negative) to +1 (positive) using `snownlp`:

```
score > 0.6  → 正面 (positive)
0.4 - 0.6   → 中性 (neutral)
score < 0.4  → 负面 (negative)
```

## License

MIT
