# trader_news — Project Context

## Project Overview

A-share financial news aggregation and processing microservice. Collects news from multiple Chinese financial sources (东方财富, 财联社, RSS feeds), stores them with sentiment scores, and serves them via a REST API. Part of the a-stock-info platform v2.0.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, APScheduler
- **Data Collection**: httpx, BeautifulSoup4, feedparser
- **Sentiment**: snownlp (lightweight Chinese NLP)
- **Database**: SQLite (dev) → PostgreSQL (prod)
- **Cache**: Redis (optional, degrades to in-memory dict)
- **Dev tools**: Ruff (formatter + linter), Mypy (type checker), pytest

## Directory Structure

```
trader_news/
├── main.py              # FastAPI entry point, lifespan, middleware, router registration
├── config.py            # Environment-based settings (DB_URL, Redis, crawler config)
├── database.py          # SQLAlchemy engine, SessionLocal, Base, get_db dependency
├── models/              # ORM models
│   └── news.py          # News table (source, title, url, pub_time, related_codes, sentiment)
├── schemas/             # Pydantic request/response models
│   ├── common.py        # ApiResponse[T], PaginationMeta, PaginatedData[T]
│   └── news.py          # NewsItem, NewsList response schemas
├── routers/             # API route handlers
│   ├── news.py          # GET /api/v1/news (search/list), GET /api/v1/news/sources
│   └── system.py        # GET /api/v1/system/status, POST /api/v1/system/trigger/{job_id}
├── services/            # Business logic layer
│   ├── news_service.py  # News query, filtering, pagination
│   └── sentiment.py     # snownlp sentiment analysis pipeline
├── crawlers/            # News collectors
│   ├── base.py          # BaseCrawler: retry (3x, exp backoff), UPSERT wrapper, logging
│   ├── eastmoney.py     # 东方财富 news crawler
│   ├── cls.py           # 财联社 news crawler
│   └── rss.py           # Generic RSS feed crawler
├── scheduler.py         # APScheduler job registration (every 30min, polite delay)
├── cache.py             # Redis/memory cache abstraction (get/set/delete/delete_pattern)
├── requirements.txt
├── ruff.toml            # Ruff config: 100 char line, double quotes, PEP 8 + bugbear + isort
├── pyproject.toml       # Mypy config
├── githooks/            # Git hooks (pre-commit, commit-msg, prepare-commit-msg)
└── .claude/             # Claude Code configuration
    ├── CLAUDE.md        # This file
    ├── skills/          # Custom skills
    └── commands/        # Slash commands (/lint, /format)
```

## Coding Standards

### Python

- **Formatter**: Ruff (`ruff format`) — 100 char line width, double quotes
- **Linter**: Ruff (`ruff check`) — PEP 8 (E/W), Pyflakes (F), isort (I), pep8-naming (N), pyupgrade (UP), bugbear (B), flake8-simplify (SIM), comprehensions (C4)
- **Type Checker**: Mypy (`mypy .`) — warn_return_any, warn_unused_configs
- **Config files**: `ruff.toml` (root), `pyproject.toml` (mypy section)

Rules:
- Type hints on ALL function signatures (parameters and return type)
- Use `double` quotes for strings
- Import order: stdlib → third-party → local (enforced by isort)
- All crawlers inherit from `BaseCrawler`, implement `fetch() -> list[dict]`
- Road logic in `services/`, never in `routers/`
- Unified API response envelope: `ApiResponse[T]` with `{code, message, data, ts}`
- Error codes: 0=success, 1001=validation, 1002=not found, 5001=internal
- Cache keys follow pattern: `news:list:{ts_code}:{source}:{page}`, TTL 120s
- `.env.example` documents all config keys; never commit `.env`

### Git

- **Conventional Commits** enforced by `commit-msg` hook:
  - `feat:` / `fix:` / `docs:` / `style:` / `refactor:` / `perf:` / `test:` / `chore:` / `ci:` / `build:`
  - Optional scope: `feat(crawler): ...`
  - Breaking changes: `feat!: ...` or `feat(scope)!: ...`
- **Branch naming**: `feat/description`, `fix/description`, `chore/description`
- **Flow**: `main` (stable) ← `dev` (integration) ← feature branches
- **Merge**: `--no-ff` only on main/dev
- **Pre-commit hook**: Auto-runs `ruff check --fix` + `ruff format --check` on staged `.py` files

## API Conventions

- **Base URL**: `/api/v1`
- **Response format**: `{code: int, message: str, data: T | null, ts: int}`
- **Pagination**: `?page=1&page_size=20`, response includes `pagination: {total, page, page_size, pages}`
- **News list endpoint**: `GET /api/v1/news?ts_code=xxx&source=xxx&page=1&page_size=20`
- **Sentiment values**: `-1.0` (negative) to `+1.0` (positive), `null` if not computed

## Cache Key Patterns

| Pattern | Content | TTL |
|---------|---------|-----|
| `news:list:{ts_code}:{source}:{page}` | Paginated news query result | 120s |
| `news:sources` | Available news source list | 3600s |

## Common Commands

```bash
# Dev server
uvicorn main:app --reload

# Lint & format
ruff check . && ruff format --check .
ruff format .

# Type check
mypy .

# Tests
pytest
pytest -m "not slow"  # skip integration tests

# Manual crawler trigger
curl -X POST http://localhost:8000/api/v1/system/trigger/sync_news

# Git hooks (already configured)
git config core.hooksPath githooks
```

## Extension Points

- **New crawler**: Create `crawlers/<source>.py` → `class XCrawler(BaseCrawler)` → implement `fetch()` → register in `scheduler.py`
- **New API endpoint**: Add route in `routers/` → register in `main.py` → define schemas in `schemas/`
- **New sentiment model**: Replace `services/sentiment.py` implementation, keep the same interface

## Dependencies to Keep in Sync

When adding new packages, update ALL of these:
1. `requirements.txt` — with pinned version
2. `CLAUDE.md` — tech stack table (this file)
3. `.env.example` — if new config keys are needed
