#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -z "${IN_NIX_SHELL:-}" ] && exec nix develop "$SCRIPT_DIR" --command bash "$0" "$@"
"$SCRIPT_DIR/run-sim.sh" "$@"
"$SCRIPT_DIR/run-flow.sh" "$@"