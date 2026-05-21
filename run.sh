#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -z "${IN_NIX_SHELL:-}" ] && exec nix develop "$SCRIPT_DIR" --command bash "$0" "$@"

SIM_DIR="$SCRIPT_DIR/build/sim"
SV2V_DIR="$SCRIPT_DIR/build/sv2v"

mkdir -p "$SIM_DIR" "$SV2V_DIR"

echo "=== PyMTL3 --test-verilog ==="
export PKG_CONFIG_PATH="/nix/store/wl8c1s56dn566asz404bqwcl0gdrw933-verilator-5.044/share/pkgconfig:${PKG_CONFIG_PATH:-}"
# Run from SIM_DIR so PyMTL3 writes _noparam.v there
pushd "$SIM_DIR" > /dev/null
PYTHONPATH="$SCRIPT_DIR" python3.11 -m pytest \
  "$SCRIPT_DIR/proj2/test/Proj2Xcel_test.py" \
  --test-verilog --dump-vtb -v --tb=short
popd > /dev/null

echo "=== sv2v ==="
sv2v -D SYNTHESIS "$SIM_DIR/Proj2Xcel_noparam__pickled.v" -w "$SV2V_DIR/Proj2Xcel.v"

echo "=== LibreLane flow ==="
python "$SCRIPT_DIR/flow.py"
