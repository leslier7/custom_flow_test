#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -z "${IN_NIX_SHELL:-}" ] && exec nix develop "$SCRIPT_DIR" --command bash "$0" "$@"

# Simulate and convert RTL to Verilog
"$SCRIPT_DIR/run-sim.sh" "$@"

# Always harden the core macro first
"$SCRIPT_DIR/run-flow.sh"

# If --chip, harden the wrapper on top of the macro outputs
for arg in "$@"; do
  if [ "$arg" = "--chip" ]; then
    "$SCRIPT_DIR/run-flow.sh" --chip
    break
  fi
done
