# Contributing to trader_news

## Development Workflow

1. **Fork** the repository
2. **Clone** your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/trader_news.git
   cd trader_news
   ```
3. **Enable hooks**:
   ```bash
   git config core.hooksPath githooks
   ```
4. **Create a feature branch** from `dev`:
   ```bash
   git checkout dev
   git checkout -b feat/my-feature
   ```
5. **Write code** following project conventions
6. **Run checks** before committing:
   ```bash
   ruff check . && ruff format --check .
   pytest
   ```
7. **Commit** using Conventional Commits:
   ```bash
   git commit -m "feat: add support for custom RSS sources"
   ```
8. **Push** and open a PR to `dev`

## Code Standards

### Python
- **Formatter**: Ruff (`ruff format`) — 100 char line width, double quotes
- **Linter**: Ruff (`ruff check`) — PEP 8, Pyflakes, isort, pyupgrade, bugbear
- **Type hints**: Required on all function signatures
- **Docstrings**: Not required for private methods; public APIs should have brief docstrings

### Git
- **Commit messages**: [Conventional Commits](https://www.conventionalcommits.org/)
- **Branch names**: `feat/description`, `fix/description`, `chore/description`
- **No direct commits to `main` or `dev`**

## Adding a New Crawler

1. Create `crawlers/my_source.py` inheriting from `BaseCrawler`
2. Implement `fetch() → list[dict]`
3. Register in `scheduler.py`
4. Add test in `tests/crawlers/`

## Running Tests

```bash
pytest                          # All tests
pytest tests/crawlers/          # Crawler tests only
pytest -m "not slow"            # Skip integration tests
```

## Questions?

Open an issue or start a discussion.
