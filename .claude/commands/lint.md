# /lint — Run All Code Quality Checks

Run linters on the entire project without modifying files.

## Steps

1. **Python Backend**
   ```bash
   cd backend && ruff check . && mypy .
   ```

2. **TypeScript Frontend**
   ```bash
   cd frontend && npx eslint . && npx prettier --check .
   ```

3. **Report Results**
   - Summarize all errors and warnings by category
   - List each file that has issues
   - If clean, confirm all checks passed
