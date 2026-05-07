#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Pass --fresh to start over, otherwise resumes last run
FRESH=${1:-""}

echo "=== LibreLane flow ==="
if [ "$FRESH" = "--fresh" ]; then
    python "$SCRIPT_DIR/flow.py" --fresh
else
    python "$SCRIPT_DIR/flow.py"
fi