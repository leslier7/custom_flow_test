#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -z "${IN_NIX_SHELL:-}" ] && exec nix develop "$SCRIPT_DIR" --command bash "$0" "$@"

CHIP=0
for arg in "$@"; do [ "$arg" = "--chip" ] && CHIP=1; done

if [ "$CHIP" -eq 1 ]; then
  echo "=== sv2v (chip core, Stage 2) ==="
  mkdir -p "$SCRIPT_DIR/build/sv2v_chip_core"
  sv2v -D PROJ2XCEL_BLACKBOX \
    -I "$SCRIPT_DIR/proj2/" \
    "$SCRIPT_DIR/proj2/Proj2XcelChip.v" \
    -w "$SCRIPT_DIR/build/sv2v_chip_core/Proj2XcelChipCore.v"
fi

echo "=== LibreLane flow ==="
python "$SCRIPT_DIR/flow.py" "$@"
