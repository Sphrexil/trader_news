# a-stock-info — Project Context

## Project Overview

A-share (China A-stock) investment information collection platform v2.0.
Personal/hobbyist use, lightweight, extensible, single-machine deployable.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, APScheduler, AKShare
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, ECharts
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Cache**: Redis (optional, degrades to in-memory dict)
- **Deploy**: Docker Compose

## Directory Structure

```
a-stock-info/
├── backend/           # FastAPI application
│   ├── main.py        # Entry point, lifespan, middleware, router registration
│   ├── config.py      # Settings from env vars
│   ├── database.py    # SQLAlchemy engine, session, Base
│   ├── models/        # ORM models (7 tables)
│   ├── schemas/       # Pydantic request/response models
│   ├── routers/       # API route handlers
│   ├── services/      # Business logic layer
│   ├── crawlers/      # Data collectors (inherited from BaseCrawler)
│   ├── scheduler.py   # APScheduler job registration
│   ├── cache.py       # Redis/memory cache abstraction
│   └── requirements.txt
├── frontend/          # React + Vite application
│   └── src/
│       ├── api/       # Axios client + endpoint modules
│       ├── components/# Reusable components (ui/, layout/, charts/)
│       ├── hooks/     # TanStack Query custom hooks
│       ├── pages/     # Page components (Dashboard, StockDetail, etc.)
│       ├── store/     # Zustand global state
│       ├── types/     # TypeScript type definitions
│       └── utils/     # Formatting & color helpers
├── docker-compose.yml
└── .claude/           # Claude Code configuration
```

## Coding Standards

### Python (Backend)
- Follow PEP 8 via Ruff (config: `backend/ruff.toml`)
- Use `double` quotes for strings
- Line length: 100 characters
- Type hints on all function signatures
- All ORM models in `models/`, all Pydantic schemas in `schemas/`
- CRUD in services layer, never in routers
- Unified API response: `ApiResponse[T]` with `{code, message, data, ts}`
- Cache keys follow documented patterns, TTL must be specified

### TypeScript (Frontend)
- Follow ESLint + Prettier config
- Use `double` quotes, semicolons required
- No `useEffect` for data fetching — use TanStack Query hooks
- All API calls go through `api/client.ts` axios instance
- Zustand only for local/client state (theme, preferences)
- Every Tailwind bg/text color must include `dark:` variant
- Use `@/*` path alias for imports

## API Conventions

- Base URL: `/api/v1`
- Error codes: 0=success, 1001=validation, 1002=not found, 1003=not ready, 5001=internal
- Pagination: `?page=1&page_size=20`, response includes `pagination` field
- All data writes use UPSERT (idempotent)

## Commands

- `/lint` — Run all linters (Ruff + ESLint + Prettier check)
- `/format` — Auto-format all code (Ruff + Prettier write)
- Backend: `cd backend && uvicorn main:app --reload`
- Frontend: `cd frontend && npm run dev`
