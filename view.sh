#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -z "${IN_NIX_SHELL:-}" ] && exec nix develop "$SCRIPT_DIR" --command bash "$0" "$@"

GDS=$(find "$SCRIPT_DIR/build/flow" -name "*.gds" | sort | tail -1)
LYP=$(find "$HOME/.ciel" -name "sky130A.lyp" | head -1)

echo "GDS: $GDS"
echo "LYP: $LYP"

if [ -z "$GDS" ]; then
    echo "No GDS found in build/flow — has the flow completed?"
    exit 1
fi

if [ -z "$LYP" ]; then
    echo "No LYP found"
fi

klayout -l "$LYP" "$GDS"