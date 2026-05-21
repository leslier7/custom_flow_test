#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -z "${IN_NIX_SHELL:-}" ] && exec nix develop "$SCRIPT_DIR" --command bash "$0" "$@"

echo "=== LibreLane flow ==="
python "$SCRIPT_DIR/flow.py" "$@"