#!/usr/bin/env python3
"""
pyhflow — generate a runnable ASIC build directory from a per-design YAML.

Inspired by Cornell ECE 6745's pyhflow. One shared Nix devshell (flake.nix), one
shared steps/ tree of Jinja2 templates, and one design YAML per project. Running
this renders the templates for the design's steps into an output directory whose
scripts can be run end to end (./run-flow) or one step at a time.

Usage (from the repo root, inside the Nix devshell):
    pyhflow designs/proj2-xcel.yml --out-dir build-proj2
    cd build-proj2 && ./run-flow
"""
import argparse
import glob
import os
import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

# Physical-only cells to drop during LVS, per PDK. Used when a design does not
# specify `lvs_ignore_cells` explicitly.
LVS_DEFAULTS = {
    "sky130A": [
        "sky130_fd_sc_hd__fill_1",
        "sky130_fd_sc_hd__fill_2",
        "sky130_fd_sc_hd__fill_4",
        "sky130_fd_sc_hd__fill_8",
        "sky130_fd_sc_hd__decap_3",
        "sky130_fd_sc_hd__diode_2",
    ],
    "gf180mcuD": [
        "gf180mcu_fd_sc_mcu7t5v0__fill_1",
        "gf180mcu_fd_sc_mcu7t5v0__fill_2",
        "gf180mcu_fd_sc_mcu7t5v0__fill_4",
        "gf180mcu_fd_sc_mcu7t5v0__fill_8",
        "gf180mcu_fd_sc_mcu7t5v0__decap_3",
    ],
}

STEP_SIM = "01-pymtl-sim"
STEP_SV2V = "02-sv2v"
STEP_CORE = "03-librelane-core"
STEP_CHIP = "04-librelane-chip"
STEP_WRAPPER = "05-librelane-wrapper"


def get_pdk_root(pdk):
    """Resolve the ciel PDK root (mirrors flow.get_pdk_root, sans librelane)."""
    if root := os.environ.get("PDK_ROOT"):
        return root
    family = "gf180mcu" if str(pdk).startswith("gf180") else "sky130"
    candidates = sorted(glob.glob(
        os.path.expanduser(f"~/.ciel/ciel/{family}/versions/*/")
    ))
    if candidates:
        return candidates[-1].rstrip("/")
    raise SystemExit(
        f"[pyhflow] Cannot find PDK root for '{pdk}'. Set PDK_ROOT or install it via ciel."
    )


def apply_overrides(design, overrides):
    """Apply --set KEY=VALUE overrides; VALUE is parsed as YAML (int/list/str)."""
    for item in overrides:
        if "=" not in item:
            raise SystemExit(f"[pyhflow] --set expects KEY=VALUE, got: {item}")
        key, raw = item.split("=", 1)
        design[key.strip()] = yaml.safe_load(raw)


def build_context(design, repo_root, out_dir):
    """Translate the design YAML into the Jinja render context (all paths absolute)."""
    def repo_path(p):
        return str((repo_root / p).resolve())

    steps = design["steps"]
    design_name = design["design_name"]
    pdk = design.get("pdk", "sky130A")

    has_sim = STEP_SIM in steps
    has_sv2v = STEP_SV2V in steps
    has_chip = STEP_CHIP in steps
    has_wrapper = STEP_WRAPPER in steps

    # --- core source pipeline ------------------------------------------------
    sv2v_in = None
    if has_sim:
        sv2v_in = str(out_dir / STEP_SIM / f"{design_name}_noparam__pickled.v")
    elif design.get("sv2v_in"):
        sv2v_in = repo_path(design["sv2v_in"])

    sv2v_out = str(out_dir / STEP_SV2V / f"{design_name}.v")

    if has_sv2v:
        core_verilog_files = [sv2v_out]
    else:
        core_verilog_files = [repo_path(p) for p in design.get("verilog_files", [])]

    include_dirs = [
        str(repo_root.resolve()) if d in (".", "dir::.") else repo_path(d)
        for d in design.get("verilog_include_dirs", ["."])
    ]

    lvs_cells = design.get("lvs_ignore_cells") or LVS_DEFAULTS.get(pdk, [])

    ctx = {
        "repo_root": str(repo_root.resolve()),
        "design_name": design_name,
        "pdk": pdk,
        "std_cell_library": design.get("std_cell_library"),
        "clock_port": design.get("clock_port"),
        "clock_period": design.get("clock_period", 10),
        "synth_defines": design.get("synth_defines", []),
        "verilog_files": core_verilog_files,
        "verilog_include_dirs": include_dirs,
        "lvs_ignore_cells_resolved": lvs_cells,
        "has_sim": has_sim,
        "has_sv2v": has_sv2v,
        "has_chip": has_chip,
        "has_wrapper": has_wrapper,
        "pymtl_test": repo_path(design["pymtl_test"]) if has_sim else None,
        "sv2v_in": sv2v_in,
        "sv2v_out": sv2v_out,
    }

    # cross-stage final artifacts produced by LibreLane (run/ inside each step)
    def final(step, kind, name):
        return str(out_dir / step / "run" / "final" / kind / name)

    core_lef = final(STEP_CORE, "lef", f"{design_name}.openroad.lef")
    core_gds = final(STEP_CORE, "gds", f"{design_name}.gds")

    # passthrough files copied verbatim into a step dir (so dir:: paths resolve)
    passthrough = {}

    if has_chip:
        chip = design["chip"]
        chip_name = chip["design_name"]
        ctx["chip"] = {
            "design_name": chip_name,
            "sv2v_top": repo_path(chip["sv2v_top"]),
            "sv2v_define": chip["sv2v_define"],
            "include_dir": repo_path(chip.get("include_dir", ".")),
            "sv2v_out": str(out_dir / STEP_SV2V / chip["sv2v_out"]),
            "die_area": chip["die_area"],
            "core_area": chip["core_area"],
            "macro_placement_cfg": os.path.basename(chip["macro_placement_cfg"]),
            "extra_verilog_models": [sv2v_out],
            "extra_lefs": [core_lef],
            "extra_gds": [core_gds],
        }
        passthrough[STEP_CHIP] = [
            (repo_root / chip["macro_placement_cfg"], os.path.basename(chip["macro_placement_cfg"]))
        ]

    if has_wrapper:
        wrapper = design["wrapper"]
        chip_name = design["chip"]["design_name"]
        chipcore_nl = final(STEP_CHIP, "nl", f"{chip_name}.nl.v")
        chipcore_lef = final(STEP_CHIP, "lef", f"{chip_name}.openroad.lef")
        chipcore_gds = final(STEP_CHIP, "gds", f"{chip_name}.gds")

        pdk_root = get_pdk_root(pdk)
        io_base = Path(pdk_root) / pdk / "libs.ref" / "sky130_fd_io"
        io_verilog = [str(io_base / "verilog" / "sky130_fd_io__blackbox.v"),
                      str(io_base / "verilog" / "sky130_ef_io.v")]
        io_lefs = [str(io_base / "lef" / "sky130_fd_io.lef"),
                   str(io_base / "lef" / "sky130_ef_io.lef")]
        io_gds = [str(io_base / "gds" / "sky130_fd_io.gds")]

        ctx["wrapper"] = {
            "design_name": wrapper["design_name"],
            "verilog_files": [repo_path(p) for p in wrapper["verilog_files"]],
            "die_area": wrapper["die_area"],
            "core_area": wrapper["core_area"],
            "macro_placement_cfg": os.path.basename(wrapper["macro_placement_cfg"]),
            "extra_verilog_models": [chipcore_nl] + io_verilog,
            "extra_lefs": [chipcore_lef] + io_lefs,
            "extra_gds": [chipcore_gds] + io_gds,
        }
        passthrough[STEP_WRAPPER] = [
            (repo_root / wrapper["macro_placement_cfg"],
             os.path.basename(wrapper["macro_placement_cfg"]))
        ]

    return ctx, passthrough


def render_steps(env, steps_dir, steps, out_dir, ctx, passthrough):
    generated = []
    for step in steps:
        step_src = steps_dir / step
        if not step_src.is_dir():
            raise SystemExit(f"[pyhflow] No template directory for step '{step}' in {steps_dir}")
        step_out = out_dir / step
        step_out.mkdir(parents=True, exist_ok=True)

        for f in sorted(step_src.iterdir()):
            if f.is_dir():
                continue
            if f.name.endswith(".j2"):
                template = env.get_template(f"{step}/{f.name}")
                out_name = f.name[:-3]
                out_path = step_out / out_name
                out_path.write_text(template.render(**ctx))
                if out_name.endswith(".sh"):
                    out_path.chmod(0o755)
                generated.append(out_path)
            else:
                dst = step_out / f.name
                shutil.copy2(f, dst)
                generated.append(dst)

        for src, dst_name in passthrough.get(step, []):
            if not src.exists():
                raise SystemExit(f"[pyhflow] Passthrough file not found: {src}")
            dst = step_out / dst_name
            shutil.copy2(src, dst)
            generated.append(dst)

    return generated


def write_runner_scripts(out_dir, steps):
    """Emit one `run-<step>` script per stage plus a `run-flow` that runs them all."""
    created = []

    # One convenience script per stage, at the build root.
    for step in steps:
        sp = out_dir / f"run-{step}"
        sp.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            'BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
            f'exec "$BUILD_DIR/{step}/run.sh" "$@"\n'
        )
        sp.chmod(0o755)
        created.append(sp)

    # run-flow: always run every stage, in order.
    rf = out_dir / "run-flow"
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        'BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
        "",
    ]
    for step in steps:
        lines.append(f'echo "===== STEP: {step} ====="')
        lines.append(f'"$BUILD_DIR/run-{step}"')
    rf.write_text("\n".join(lines) + "\n")
    rf.chmod(0o755)
    created.append(rf)

    return created


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate an ASIC build dir from a design YAML.")
    parser.add_argument("design", help="Path to the design YAML")
    parser.add_argument("--out-dir", default=".", help="Output build directory (default: cwd)")
    parser.add_argument("--set", dest="overrides", action="append", default=[],
                        metavar="KEY=VALUE", help="Override a top-level design field (repeatable)")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent
    steps_dir = repo_root / "steps"
    design_path = Path(args.design).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not design_path.is_file():
        raise SystemExit(f"[pyhflow] Design YAML not found: {design_path}")

    design = yaml.safe_load(design_path.read_text()) or {}
    apply_overrides(design, args.overrides)

    for key in ("design_name", "steps"):
        if key not in design:
            raise SystemExit(f"[pyhflow] Design YAML missing required field '{key}'")

    out_dir.mkdir(parents=True, exist_ok=True)
    ctx, passthrough = build_context(design, repo_root, out_dir)

    env = Environment(
        loader=FileSystemLoader(str(steps_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    generated = render_steps(env, steps_dir, design["steps"], out_dir, ctx, passthrough)
    runners = write_runner_scripts(out_dir, design["steps"])

    print(f"[pyhflow] design : {design['design_name']}  (pdk: {ctx['pdk']})")
    print(f"[pyhflow] out-dir: {out_dir}")
    print(f"[pyhflow] steps  : {', '.join(design['steps'])}")
    for p in generated:
        print(f"  + {p.relative_to(out_dir)}")
    for p in runners:
        note = "  (runs every stage)" if p.name == "run-flow" else "  (one stage)"
        print(f"  + {p.name}{note}")
    print(f"[pyhflow] done. Run all: cd {out_dir} && ./run-flow")
    return 0


if __name__ == "__main__":
    sys.exit(main())
