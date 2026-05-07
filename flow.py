import os
import glob
import sys
import re
from datetime import datetime
from pathlib import Path
from librelane.flows import SequentialFlow
from librelane.steps.yosys import Synthesis
from librelane.steps.openroad import (
    Floorplan, IOPlacement,
    GlobalPlacement, DetailedPlacement,
    CTS, GlobalRouting, DetailedRouting,
    FillInsertion,
)
from librelane.steps.magic import StreamOut, SpiceExtraction
from librelane.steps.netgen import LVS

def get_pdk_root():
    if root := os.environ.get("PDK_ROOT"):
        return root
    candidates = sorted(glob.glob(
        os.path.expanduser("~/.ciel/ciel/sky130/versions/*/")
    ))
    if candidates:
        return candidates[-1].rstrip("/")
    raise RuntimeError("Cannot find PDK root. Set PDK_ROOT.")

class MyFlow(SequentialFlow):
    Steps = [
        Synthesis, Floorplan, IOPlacement,
        GlobalPlacement, DetailedPlacement,
        CTS, GlobalRouting, DetailedRouting,
        FillInsertion, StreamOut, SpiceExtraction, LVS,
    ]


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# OpenROAD: "Design area 123456.78 u^2 45.60% utilization."
_AREA_OR    = re.compile(r"Design area\s+([\d.]+)\s+u\^2\s+([\d.]+)%")
# Yosys: "Chip area for module '\Proj2Xcel': 123456.78"
_AREA_YS    = re.compile(r"Chip area for (?:module|top)\s+'\\?\w+':\s*([\d.]+)")
# Yosys: "Number of cells: 1234"
_CELLS      = re.compile(r"Number of cells:\s*(\d+)")
# OpenROAD STA: "wns -0.123" / "tns -4.56" (standalone lines)
_WNS        = re.compile(r"^\s*wns\s+(-?[\d.]+)", re.MULTILINE)
_TNS        = re.compile(r"^\s*tns\s+(-?[\d.]+)", re.MULTILINE)
# Also catch "worst slack" phrasing
_WSLACK     = re.compile(r"worst slack\s*[:\s]\s*(-?[\d.]+)", re.IGNORECASE)
# LVS
_LVS_PASS   = re.compile(r"Circuits match uniquely", re.IGNORECASE)
_LVS_FAIL   = re.compile(r"\*\*\* MISMATCH \*\*\*")
_LVS_DEV    = re.compile(r"Circuit \d+ contains\s+(\d+)\s+devices")
_LVS_NET    = re.compile(r"Circuit \d+ contains\s+(\d+)\s+nets")


def _read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def write_summary(run_dir: str, design_name: str, clock_period_ns: float) -> None:
    root = Path(run_dir)

    data: dict = {
        "synth_area_um2": None,
        "synth_cells": None,
        "layout_area_um2": None,
        "utilization_pct": None,
        "wns_ns": None,
        "tns_ns": None,
        "lvs_pass": None,
        "lvs_devices": [],   # [c1, c2]
        "lvs_nets": [],      # [c1, c2]
        "area_source": None,
        "timing_source": None,
    }

    # Walk step dirs in sorted order so later (post-route) values win.
    step_dirs = sorted(
        (d for d in root.iterdir() if d.is_dir() and d.name[0].isdigit()),
        key=lambda d: d.name,
    )

    for step_dir in step_dirs:
        is_synth = "synth" in step_dir.name.lower() or "yosys" in step_dir.name.lower()
        is_lvs   = "lvs"   in step_dir.name.lower() or "netgen" in step_dir.name.lower()

        for ext in ("*.rpt", "*.log", "*.txt"):
            for f in sorted(step_dir.rglob(ext)):
                text = _read(f)
                if not text:
                    continue

                # Yosys area + cell count (only from synthesis step)
                if is_synth:
                    if m := _AREA_YS.search(text):
                        data["synth_area_um2"] = float(m.group(1))
                    if m := _CELLS.search(text):
                        data["synth_cells"] = int(m.group(1))

                # OpenROAD layout area (take last occurrence across all steps)
                if m := _AREA_OR.search(text):
                    data["layout_area_um2"] = float(m.group(1))
                    data["utilization_pct"]  = float(m.group(2))
                    data["area_source"] = step_dir.name

                # Timing — prefer explicit "wns/tns" lines, fall back to "worst slack"
                for pat in (_WNS, _WSLACK):
                    for m in pat.finditer(text):
                        data["wns_ns"] = float(m.group(1))
                        data["timing_source"] = step_dir.name
                for m in _TNS.finditer(text):
                    data["tns_ns"] = float(m.group(1))

                # LVS (only from LVS step)
                if is_lvs:
                    if _LVS_PASS.search(text):
                        data["lvs_pass"] = True
                    if _LVS_FAIL.search(text):
                        data["lvs_pass"] = False
                    devs = _LVS_DEV.findall(text)
                    nets = _LVS_NET.findall(text)
                    if len(devs) >= 2:
                        data["lvs_devices"] = [int(devs[0]), int(devs[1])]
                    if len(nets) >= 2:
                        data["lvs_nets"] = [int(nets[0]), int(nets[1])]

    # ------------------------------------------------------------------
    # Format
    # ------------------------------------------------------------------
    lines = [
        "=" * 60,
        f"  LibreLane Flow Summary — {design_name}",
        f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
        "--- Synthesis ---",
    ]

    if data["synth_cells"] is not None:
        lines.append(f"  Cell count  : {data['synth_cells']:,}")
    else:
        lines.append("  Cell count  : (not found)")

    if data["synth_area_um2"] is not None:
        lines.append(f"  Yosys area  : {data['synth_area_um2']:,.2f} um^2  (pre-placement estimate)")
    else:
        lines.append("  Yosys area  : (not found)")

    lines += ["", "--- Layout ---"]

    if data["layout_area_um2"] is not None:
        lines.append(f"  Design area : {data['layout_area_um2']:,.2f} um^2")
        lines.append(f"  Utilization : {data['utilization_pct']:.2f}%")
        lines.append(f"  (from step  : {data['area_source']})")
    else:
        lines.append("  Design area : (not found)")

    lines += ["", "--- Timing (post-route) ---"]
    lines.append(f"  Clock period: {clock_period_ns:.2f} ns")

    if data["wns_ns"] is not None:
        slack_ok = data["wns_ns"] >= 0.0
        flag = "MET" if slack_ok else "VIOLATED"
        lines.append(f"  WNS         : {data['wns_ns']:+.3f} ns  [{flag}]")
    else:
        lines.append("  WNS         : (not found)")

    if data["tns_ns"] is not None:
        lines.append(f"  TNS         : {data['tns_ns']:+.3f} ns")
    else:
        lines.append("  TNS         : (not found)")

    if data["timing_source"]:
        lines.append(f"  (from step  : {data['timing_source']})")

    lines += ["", "--- LVS ---"]

    if data["lvs_pass"] is True:
        lines.append("  Status      : PASS")
    elif data["lvs_pass"] is False:
        lines.append("  Status      : FAIL  *** MISMATCH ***")
        if data["lvs_devices"]:
            c1d, c2d = data["lvs_devices"]
            match = "matched" if c1d == c2d else "MISMATCH"
            lines.append(f"  Devices     : layout={c1d:,}  schematic={c2d:,}  [{match}]")
        if data["lvs_nets"]:
            c1n, c2n = data["lvs_nets"]
            match = "matched" if c1n == c2n else "MISMATCH"
            lines.append(f"  Nets        : layout={c1n:,}  schematic={c2n:,}  [{match}]")
    else:
        lines.append("  Status      : (LVS report not found)")

    lines += ["", "=" * 60]

    out_path = root / "summary.txt"
    out_path.write_text("\n".join(lines) + "\n")
    print(f"\n[summary] Written to {out_path}")
    print("\n".join(lines))


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    fresh = "--fresh" in sys.argv
    run_dir = "build/flow"
    has_previous = os.path.isdir(run_dir) and any(
        d.startswith(("0", "1", "2", "3"))
        for d in os.listdir(run_dir)
    ) if os.path.isdir(run_dir) else False

    flow = MyFlow("config.yaml", pdk_root=get_pdk_root())

    if not fresh and has_previous:
        flow.start(_force_run_dir=run_dir, last_run=True, overwrite=True)
    else:
        flow.start(_force_run_dir=run_dir, overwrite=True)

    write_summary(run_dir, design_name="Proj2Xcel", clock_period_ns=10.0)[summary] Written to build/flow/summary.txt
============================================================
  LibreLane Flow Summary — Proj2Xcel
  Generated: 2026-05-07 00:28:20
============================================================

--- Synthesis ---
  Cell count  : (not found)
  Yosys area  : 19,228.44 um^2  (pre-placement estimate)

--- Layout ---
  Design area : (not found)

--- Timing (post-route) ---
  Clock period: 10.00 ns
  WNS         : (not found)
  TNS         : (not found)

--- LVS ---
  Status      : FAIL  *** MISMATCH ***
  Devices     : layout=16,329  schematic=15,886  [MISMATCH]
  Nets        : layout=14,367  schematic=15,894  [MISMATCH]

============================================================