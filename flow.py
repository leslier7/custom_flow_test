import os
import glob
import re
import json
from datetime import datetime
from pathlib import Path
from librelane.flows import SequentialFlow
from librelane.steps.yosys import Synthesis
from librelane.steps.openroad import (
    Floorplan, IOPlacement,
    GlobalPlacement, DetailedPlacement,
    CTS, GlobalRouting, DetailedRouting,
    FillInsertion, STAMidPNR, WriteViews,
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
        FillInsertion, STAMidPNR, WriteViews, StreamOut, SpiceExtraction, LVS,
    ]


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# OpenROAD: "Design area 123456.78 u^2 45.60% utilization."
_AREA_OR    = re.compile(r"Design area\s+([0-9,]+(?:\.\d+)?)\s+u\^2\s+([0-9,]+(?:\.\d+)?)%")
# Yosys: "Chip area for module '\Proj2Xcel': 123456.78"
_AREA_YS    = re.compile(r"Chip area for (?:module|top)\s+'\\?\w+':\s*([0-9,]+(?:\.\d+)?)")
# Yosys: "Number of cells: 1234"
_CELLS      = re.compile(r"Number of cells:\s*([0-9,]+)")
# Yosys stat.rpt table row: "15695 1.58E+05 cells"
_CELLS_ALT  = re.compile(r"^\s*([0-9,]+)\s+[0-9.Ee+\-]+\s+cells\s*$", re.MULTILINE)
# OpenROAD STA: "wns -0.123" / "tns -4.56" (standalone lines)
_WNS        = re.compile(r"^\s*wns\s+(-?[\d.]+)", re.MULTILINE)
_TNS        = re.compile(r"^\s*tns\s+(-?[\d.]+)", re.MULTILINE)
# Also catch "worst slack" phrasing
_WSLACK     = re.compile(r"worst slack\s*[:\s]\s*(-?[\d.]+)", re.IGNORECASE)
# LVS
_LVS_PASS   = re.compile(r"Circuits match uniquely", re.IGNORECASE)
_LVS_FAIL   = re.compile(r"\*\*\* MISMATCH \*\*\*")
_LVS_DEV    = re.compile(r"Circuit \d+ contains\s+([0-9,]+)\s+devices")
_LVS_NET    = re.compile(r"Circuit \d+ contains\s+([0-9,]+)\s+nets")


def _read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""

def _num_int(s: str) -> int:
    return int(s.replace(",", "").strip())

def _num_float(s: str) -> float:
    return float(s.replace(",", "").strip())

def _read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return None

def _latest_step_dir(root: Path, token: str) -> Path | None:
    candidates = []
    for d in root.iterdir():
        if not d.is_dir():
            continue
        if token not in d.name.lower():
            continue
        try:
            ordinal = int(d.name.split("-", 1)[0])
        except (ValueError, IndexError):
            continue
        candidates.append((ordinal, d))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]

def _extract_last_float(text: str) -> float | None:
    vals = re.findall(r"(-?\d+(?:\.\d+)?)", text)
    if not vals:
        return None
    try:
        return float(vals[-1])
    except ValueError:
        return None

def _update_timing_from_mapping(mapping, data: dict, source: str) -> bool:
    """
    Extract timing values from arbitrary JSON mappings by key name.
    """
    if not isinstance(mapping, dict):
        return False

    updated = False
    for key, value in mapping.items():
        if not isinstance(value, (int, float)):
            continue
        k = str(key).lower()
        if "wns" in k:
            data["wns_ns"] = float(value)
            data["timing_source"] = source
            updated = True
        elif "tns" in k:
            data["tns_ns"] = float(value)
            data["timing_source"] = source
            updated = True
        elif ("worst" in k and "slack" in k) or k.endswith("slack"):
            data["wns_ns"] = float(value)
            data["timing_source"] = source
            updated = True
    return updated

def _has_step_directories(path: Path) -> bool:
    try:
        return any(
            entry.is_dir() and entry.name and entry.name[0].isdigit()
            for entry in path.iterdir()
        )
    except OSError:
        return False

def _resolve_run_directory(run_root: Path) -> Path | None:
    """
    Return the directory that contains numbered flow step folders.
    Supports both layouts:
      - build/flow/<step folders>
      - build/flow/<run name>/<step folders>
    """
    if not run_root.is_dir():
        return None

    if _has_step_directories(run_root):
        return run_root

    candidates = [child for child in run_root.iterdir() if child.is_dir()]
    run_candidates = [child for child in candidates if _has_step_directories(child)]
    if not run_candidates:
        return None
    return max(run_candidates, key=lambda p: p.stat().st_mtime)

def _load_clock_period_ns(config_path: Path, default: float = 10.0) -> float:
    """
    Read CLOCK_PERIOD from config.yaml without extra dependencies.
    """
    text = _read(config_path)
    if not text:
        return default
    m = re.search(r"^\s*CLOCK_PERIOD\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*$", text, re.MULTILINE)
    if not m:
        return default
    try:
        return float(m.group(1))
    except ValueError:
        return default

def write_summary(run_dir: str, design_name: str, clock_period_ns: float) -> None:
    root = Path(run_dir)
    final_metrics = _read_json(root / "final" / "metrics.json")

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
        "used_final_metrics": False,
        "parsed_files": 0,
        "steps_scanned": 0,
    }

    # Prefer final metrics JSON for canonical post-run layout/util/cell count.
    if isinstance(final_metrics, dict):
        if isinstance(final_metrics.get("design__instance__count__stdcell"), (int, float)):
            data["synth_cells"] = int(final_metrics["design__instance__count__stdcell"])
        elif isinstance(final_metrics.get("design__instance__count"), (int, float)):
            data["synth_cells"] = int(final_metrics["design__instance__count"])

        if isinstance(final_metrics.get("design__core__area"), (int, float)):
            data["layout_area_um2"] = float(final_metrics["design__core__area"])
            data["area_source"] = "final/metrics.json:design__core__area"

        if isinstance(final_metrics.get("design__instance__utilization"), (int, float)):
            data["utilization_pct"] = float(final_metrics["design__instance__utilization"]) * 100.0
            if data["area_source"] is None:
                data["area_source"] = "final/metrics.json:design__instance__utilization"

        if data["synth_cells"] is not None or data["layout_area_um2"] is not None or data["utilization_pct"] is not None:
            data["used_final_metrics"] = True

    # Walk step dirs in sorted order so later (post-route) values win.
    step_dirs = sorted(
        (d for d in root.iterdir() if d.is_dir() and d.name[0].isdigit()),
        key=lambda d: d.name,
    )

    for step_dir in step_dirs:
        data["steps_scanned"] += 1
        is_synth = "synth" in step_dir.name.lower() or "yosys" in step_dir.name.lower()
        is_lvs   = "lvs"   in step_dir.name.lower() or "netgen" in step_dir.name.lower()

        for ext in ("*.rpt", "*.log", "*.txt"):
            for f in sorted(step_dir.rglob(ext)):
                text = _read(f)
                if not text:
                    continue
                data["parsed_files"] += 1
                lower_name = f.name.lower()

                # Yosys area + cell count (only from synthesis step)
                if is_synth:
                    if m := _AREA_YS.search(text):
                        data["synth_area_um2"] = _num_float(m.group(1))
                    if m := _CELLS.search(text):
                        data["synth_cells"] = _num_int(m.group(1))
                    elif m := _CELLS_ALT.search(text):
                        data["synth_cells"] = _num_int(m.group(1))

                # OpenROAD layout area (take last occurrence across all steps)
                if m := _AREA_OR.search(text):
                    data["layout_area_um2"] = _num_float(m.group(1))
                    data["utilization_pct"]  = _num_float(m.group(2))
                    data["area_source"] = step_dir.name

                # Timing — prefer explicit "wns/tns" lines, fall back to "worst slack"
                for pat in (_WNS, _WSLACK):
                    for m in pat.finditer(text):
                        data["wns_ns"] = float(m.group(1))
                        data["timing_source"] = str(f.relative_to(root))
                for m in _TNS.finditer(text):
                    data["tns_ns"] = float(m.group(1))
                    data["timing_source"] = str(f.relative_to(root))

                # Handle explicit STA reports such as wns.max.rpt / tns.max.rpt
                if "wns" in lower_name:
                    nums = re.findall(r"(-?\d+(?:\.\d+)?)", text)
                    if nums:
                        data["wns_ns"] = float(nums[-1])
                        data["timing_source"] = str(f.relative_to(root))
                if "tns" in lower_name:
                    nums = re.findall(r"(-?\d+(?:\.\d+)?)", text)
                    if nums:
                        data["tns_ns"] = float(nums[-1])
                        data["timing_source"] = str(f.relative_to(root))

                # LVS (only from LVS step)
                if is_lvs:
                    if _LVS_PASS.search(text):
                        data["lvs_pass"] = True
                    if _LVS_FAIL.search(text):
                        data["lvs_pass"] = False
                    devs = _LVS_DEV.findall(text)
                    nets = _LVS_NET.findall(text)
                    if len(devs) >= 2:
                        data["lvs_devices"] = [_num_int(devs[0]), _num_int(devs[1])]
                    if len(nets) >= 2:
                        data["lvs_nets"] = [_num_int(nets[0]), _num_int(nets[1])]

    # Additional pass: scan generated JSON reports for post-PNR and STA metrics.
    json_files = sorted(root.rglob("*.json"))
    for jf in json_files:
        metrics = _read_json(jf)
        if not isinstance(metrics, dict):
            continue

        # Prefer post-PNR values from any metrics-like report (final and per-step).
        if isinstance(metrics.get("design__core__area"), (int, float)):
            data["layout_area_um2"] = float(metrics["design__core__area"])
            data["area_source"] = str(jf.relative_to(root))
        if isinstance(metrics.get("design__instance__utilization"), (int, float)):
            data["utilization_pct"] = float(metrics["design__instance__utilization"]) * 100.0
            if data["area_source"] is None:
                data["area_source"] = str(jf.relative_to(root))

        # Gather timing from any STA-oriented metric keys.
        _update_timing_from_mapping(metrics, data, str(jf.relative_to(root)))

    # Deterministic overrides from latest explicit step artifacts.
    latest_synth = _latest_step_dir(root, "yosys-synthesis")
    if latest_synth is not None:
        stat_rpt = latest_synth / "reports" / "stat.rpt"
        stat_text = _read(stat_rpt)
        if stat_text:
            if m := _AREA_YS.search(stat_text):
                data["synth_area_um2"] = _num_float(m.group(1))
            if m := _CELLS.search(stat_text):
                data["synth_cells"] = _num_int(m.group(1))
            elif m := _CELLS_ALT.search(stat_text):
                data["synth_cells"] = _num_int(m.group(1))

    latest_fill = _latest_step_dir(root, "openroad-fillinsertion")
    if latest_fill is not None:
        fill_metrics = _read_json(latest_fill / "or_metrics_out.json")
        if isinstance(fill_metrics, dict):
            # Use post-PNR std-cell area for apples-to-apples with synthesis area.
            if isinstance(fill_metrics.get("design__instance__area__stdcell"), (int, float)):
                data["layout_area_um2"] = float(fill_metrics["design__instance__area__stdcell"])
            elif isinstance(fill_metrics.get("design__instance__area"), (int, float)):
                data["layout_area_um2"] = float(fill_metrics["design__instance__area"])
            if isinstance(fill_metrics.get("design__instance__utilization"), (int, float)):
                data["utilization_pct"] = float(fill_metrics["design__instance__utilization"]) * 100.0

    latest_sta = _latest_step_dir(root, "openroad-stamidpnr")
    if latest_sta is not None:
        wns_text = _read(latest_sta / "wns.max.rpt")
        tns_text = _read(latest_sta / "tns.max.rpt")
        if wns_text:
            if v := _extract_last_float(wns_text):
                data["wns_ns"] = v
        if tns_text:
            if v := _extract_last_float(tns_text):
                data["tns_ns"] = v

    # ------------------------------------------------------------------
    # Format
    # ------------------------------------------------------------------
    lines = [
        "=" * 60,
        f"  LibreLane Flow Summary — {design_name}",
        f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
        f"  Run directory: {root}",
        f"  Steps scanned: {data['steps_scanned']}",
        f"  Files parsed : {data['parsed_files']}",
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
        if data["utilization_pct"] is not None:
            lines.append(f"  Utilization : {data['utilization_pct']:.2f}%")
        else:
            lines.append("  Utilization : (not found)")
    else:
        lines.append("  Design area : (not found)")

    lines += ["", "--- Timing (post-route) ---"]
    lines.append(f"  Clock period: {clock_period_ns:.2f} ns")

    if data["wns_ns"] is not None:
        slack_ok = data["wns_ns"] >= 0.0
        flag = "MET" if slack_ok else "VIOLATED"
        lines.append(f"  Worst negative slack : {data['wns_ns']:+.3f} ns  [{flag}]")
    else:
        lines.append("  Worst negative slack : (not found)")

    if data["tns_ns"] is not None:
        lines.append(f"  Total negative slack : {data['tns_ns']:+.3f} ns")
    else:
        lines.append("  Total negative slack : (not found)")

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

def _chip_io_overrides(pdk_root: str) -> dict:
    io_ref = Path(pdk_root) / "sky130A" / "libs.ref" / "sky130_fd_io"
    return {
        "EXTRA_LEFS": [
            str(io_ref / "lef" / "sky130_fd_io.lef"),
            str(io_ref / "lef" / "sky130_ef_io.lef"),
        ],
        "EXTRA_GDS_FILES": [
            str(io_ref / "gds" / "sky130_fd_io.gds"),
        ],
        "VERILOG_FILES_BLACKBOX": [
            str(io_ref / "verilog" / "sky130_fd_io__blackbox.v"),
            str(io_ref / "verilog" / "sky130_ef_io.v"),
        ],
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--chip", action="store_true", help="Build with IO pads (chip-level)")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    pdk_root = get_pdk_root()

    if args.chip:
        config_file = "config_chip.yaml"
        run_root = base_dir / "build" / "flow_chip"
        design_name = "Proj2Xcel_chip"
        config = [config_file, _chip_io_overrides(pdk_root)]
    else:
        config_file = "config.yaml"
        run_root = base_dir / "build" / "flow"
        design_name = "Proj2Xcel"
        config = config_file

    flow = MyFlow(config, pdk_root=pdk_root)
    flow.start(_force_run_dir=str(run_root), overwrite=True)

    summary_dir = _resolve_run_directory(run_root) or run_root
    clock_period_ns = _load_clock_period_ns(base_dir / config_file)
    write_summary(str(summary_dir), design_name=design_name, clock_period_ns=clock_period_ns)
