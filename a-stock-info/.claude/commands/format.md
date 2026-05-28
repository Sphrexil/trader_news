# /format — Auto-Format All Code

Auto-format all code files in the project.

## Steps

1. **Python Backend**
   ```bash
   cd backend && ruff format . && ruff check --fix .
   ```

2. **TypeScript Frontend**
   ```bash
   cd frontend && npx prettier --write . && npx eslint --fix .
   ```

3. **Report Results**
   - List files that were modified
   - Report any remaining unfixable issues
   - Confirm completion
