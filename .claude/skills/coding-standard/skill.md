# Coding Standard Skill

Enforce code quality and formatting standards for this project.

## When to Apply

This skill activates automatically via the PostToolUse hook after any `Write` or `Edit` tool call. It also provides the `/lint` and `/format` manual commands.

## Python Standards

- **Formatter**: Ruff (`ruff format`)
- **Linter**: Ruff (`ruff check --fix`)
- **Type Checker**: Mypy (`mypy .`)
- Config: `backend/ruff.toml`, `backend/pyproject.toml`

Rules enforced:
- PEP 8 via pycodestyle (E/W)
- Unused imports/variables via Pyflakes (F)
- Import sorting via isort (I)
- Naming conventions via pep8-naming (N)
- Modern Python via pyupgrade (UP)
- Bug detection via flake8-bugbear (B)
- Simplification via flake8-simplify (SIM)
- Comprehension via flake8-comprehensions (C4)
- Line length: 100 chars

## TypeScript Standards

- **Formatter**: Prettier (`npx prettier --write`)
- **Linter**: ESLint (`npx eslint`)
- Config: `frontend/.prettierrc`, `frontend/eslint.config.js`

Rules enforced:
- Double quotes, semicolons required
- Trailing commas: all
- Print width: 100
- Tab width: 2

## Hook Behavior

The PostToolUse hook (`hooks/format-on-save.sh`) runs automatically:
1. Reads the file path from the tool input
2. If `.py` → runs `ruff format` + `ruff check --fix`
3. If `.ts`/`.tsx`/`.js`/`.jsx` → runs `prettier --write` + `eslint --fix`
4. If formatting fails, errors are forwarded to Claude for correction
5. If tools are missing, the hook silently skips (no-op)
