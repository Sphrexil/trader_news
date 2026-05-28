# coding-standard

Code quality and formatting enforcement for the trader_news project.

## Triggers

- **Manual**: `/lint` or `/format` slash commands
- **Automatic**: Not yet auto-triggered (PostToolUse hook available in `githooks/`)

## Python Standards

### Ruff Formatter (`ruff format`)

| Setting | Value |
|---------|-------|
| Line length | 100 |
| Quote style | double |
| Indent style | space (4) |
| Target version | py311 |

### Ruff Linter (`ruff check`)

| Rule | Code | Purpose |
|------|------|---------|
| pycodestyle | E, W | PEP 8 compliance |
| Pyflakes | F | Unused imports, undefined names |
| isort | I | Import sorting |
| pep8-naming | N | Naming conventions |
| pyupgrade | UP | Modern Python syntax |
| flake8-bugbear | B | Common bug patterns |
| flake8-simplify | SIM | Code simplification |
| flake8-comprehensions | C4 | Comprehension style |

### Mypy (`mypy .`)

- `python_version = 3.11`
- `warn_return_any = true` — no implicit `Any` returns
- `warn_unused_configs = true` — catch dead config
- Third-party packages without stubs: `ignore_missing_imports = true`

## Code Conventions

### Naming
- Classes: `PascalCase` — `BaseCrawler`, `NewsService`
- Functions/methods: `snake_case` — `fetch_news()`, `get_by_source()`
- Variables: `snake_case` — `news_count`, `ts_code`
- Constants: `UPPER_SNAKE_CASE` — `MAX_RETRIES`, `DEFAULT_TTL`
- Private members: `_leading_underscore` — `_build_query()`, `_redis`

### Imports
```python
# Order: stdlib → third-party → local
import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import get_settings
from models.news import News
```

### Function Signatures
```python
# Type hints required on ALL parameters and return
def search_news(
    ts_code: str | None = None,
    source: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[News], int]:
    ...
```

### Crawler Pattern
```python
class MyCrawler(BaseCrawler):
    """Collect news from <source>."""

    def fetch(self) -> list[dict]:
        """Return standardized records."""
        records = []
        # ... fetch logic ...
        return records

    def upsert(self, records: list[dict]):
        """Write to database (UPSERT by url)."""
        # ... upsert logic ...
```

### API Response Pattern
```python
@router.get("/news", response_model=ApiResponse[PaginatedData[NewsItem]])
def list_news(...):
    items, total = news_service.search(...)
    return ApiResponse(
        data=PaginatedData(
            list=items,
            pagination=PaginationMeta(
                total=total, page=page, page_size=page_size,
                pages=(total + page_size - 1) // page_size
            )
        )
    )
```

## Anti-Patterns to Avoid

- Do NOT write business logic in `routers/` — use `services/`
- Do NOT cache in route handlers — use `cache.py` abstraction
- Do NOT use bare `except:` — always catch specific exceptions
- Do NOT skip type hints "because it's obvious"
- Do NOT hardcode URLs or keys — use `config.py` + environment variables
- Do NOT commit `.env` files
- Do NOT use `print()` for logging — use `logging.getLogger(__name__)`
