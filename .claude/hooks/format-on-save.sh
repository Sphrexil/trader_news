#!/usr/bin/env bash
# PostToolUse hook: auto-format files after Write/Edit via Claude Code.
# Reads tool_input.file_path from stdin JSON.
# Silently no-ops if required tools are missing.

set -euo pipefail

# Parse the file path from stdin
FILE=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || true)

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  exit 0
fi

EXT="${FILE##*.}"

# Python files → Ruff
if [ "$EXT" = "py" ]; then
  if command -v ruff &>/dev/null; then
    ruff format "$FILE" 2>&1 || true
    ruff check --fix "$FILE" 2>&1 || true
  fi
fi

# TypeScript/JavaScript files → Prettier + ESLint
case "$EXT" in
  ts|tsx|js|jsx)
    PROJECT_DIR=$(dirname "$(dirname "$(dirname "$FILE")")")
    if command -v npx &>/dev/null; then
      (cd "$PROJECT_DIR/frontend" && npx prettier --write "$FILE" 2>&1) || true
      (cd "$PROJECT_DIR/frontend" && npx eslint --fix "$FILE" 2>&1) || true
    fi
    ;;
esac

exit 0
