# /format — Auto-Format All Code

Auto-fix formatting and linting issues across the entire project.

## Steps

1. **Ruff Format**
   ```bash
   ruff format .
   ```
   Auto-formats all `.py` files to project standards.

2. **Ruff Fix**
   ```bash
   ruff check --fix .
   ```
   Auto-fixes safe lint violations (unused imports, import sorting, etc.).

3. **Report**
   - List files that were modified
   - List any remaining unfixable issues (require manual intervention)
   - Confirm: "Formatting complete. N files modified, M issues remain."
