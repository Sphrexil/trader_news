# /lint — Run All Code Quality Checks

Execute linters on the entire project. Read-only — no files modified.

## Steps

1. **Ruff Check**
   ```bash
   ruff check .
   ```
   Report all violations by file. Group by rule code.

2. **Ruff Format Check**
   ```bash
   ruff format --check .
   ```
   List files that would be reformatted.

3. **Mypy Type Check**
   ```bash
   mypy .
   ```
   Report all type errors by file.

## Report Format

After running, summarize:

```
## Lint Results

### Ruff (linter)
- X errors, Y warnings across Z files
<list files with issues>

### Ruff (formatter)
- N files would be reformatted
<list files>

### Mypy
- N type errors
<list errors by file>

### Verdict
- ALL CLEAN / N issues to fix
```

If all checks pass, confirm: "All lint checks passed."
