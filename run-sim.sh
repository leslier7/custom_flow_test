#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -z "${IN_NIX_SHELL:-}" ] && exec nix develop "$SCRIPT_DIR" --command bash "$0" "$@"
export PKG_CONFIG_PATH="/nix/store/wl8c1s56dn566asz404bqwcl0gdrw933-verilator-5.044/share/pkgconfig:${PKG_CONFIG_PATH:-}"
export PYTHONDONTWRITEBYTECODE=1

CHIP=0
for arg in "$@"; do [ "$arg" = "--chip" ] && CHIP=1; done

if [ "$CHIP" -eq 1 ]; then
  SIM_DIR="$SCRIPT_DIR/build/sim_chip"
  SV2V_DIR="$SCRIPT_DIR/build/sv2v_chip"
  TEST_FILE="$SCRIPT_DIR/proj2/test/Proj2XcelChip_test.py"
  PICKLED="$SIM_DIR/Proj2XcelChip_noparam__pickled.v"
  SV2V_OUT="$SV2V_DIR/Proj2XcelChip.v"
else
  SIM_DIR="$SCRIPT_DIR/build/sim"
  SV2V_DIR="$SCRIPT_DIR/build/sv2v"
  TEST_FILE="$SCRIPT_DIR/proj2/test/Proj2Xcel_test.py"
  PICKLED="$SIM_DIR/Proj2Xcel_noparam__pickled.v"
  SV2V_OUT="$SV2V_DIR/Proj2Xcel.v"
fi

mkdir -p "$SIM_DIR" "$SV2V_DIR"

echo "=== PyMTL3 --test-verilog ==="
pushd "$SIM_DIR" > /dev/null
PYTHONPATH="$SCRIPT_DIR" python3.11 -m pytest \
  "$TEST_FILE" \
  --test-verilog --dump-vtb -v --tb=short
popd > /dev/null

echo "=== sv2v ==="
sv2v -D SYNTHESIS \
  "$PICKLED" \
  -w "$SV2V_OUT"