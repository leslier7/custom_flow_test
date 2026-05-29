{
  inputs.librelane.url = "github:librelane/librelane";

  outputs = { self, librelane }:
    let
      system = "x86_64-linux";
      pkgs   = librelane.legacyPackages.${system};

      pymtl3 = pkgs.python311.pkgs.buildPythonPackage {
        pname   = "pymtl3";
        version = "4.0.0-dev";
        pyproject = true;
        build-system = with pkgs.python311.pkgs; [ setuptools setuptools-scm ];
        src = pkgs.fetchFromGitHub {
          owner = "cornell-brg";
          repo  = "pymtl3";
          rev   = "pymtl4.0-dev";
          hash  = "sha256-ZPdWftIzAcNAN/YFQYbsynOPivJRrLrPVezTnGJnEx0=";
        };
        propagatedBuildInputs = with pkgs.python311.pkgs; [
          cffi greenlet hypothesis py pytest fasteners
        ];
        SETUPTOOLS_SCM_PRETEND_VERSION = "4.0.0.dev0";
        doCheck = false;
      };

      pymtl3Env = pkgs.runCommand "python3.11-pymtl3" {} ''
        mkdir -p $out/bin
        ln -s ${pkgs.python311.withPackages (ps: [ pymtl3 ])}/bin/python3.11 \
              $out/bin/python3.11
      '';
      pytestWrapper = pkgs.writeShellScriptBin "pytest" ''
        exec python3.11 -m pytest "$@"
      '';

      # Dedicated interpreter for the pyhflow generator. It only needs pyyaml +
      # jinja2 (NOT librelane), so keep it isolated from the librelane-shell python.
      pyhflowPython = pkgs.python311.withPackages (ps: with ps; [ pyyaml jinja2 ]);
      # `pyhflow <design.yml> [--out-dir DIR]` — runs the repo's pyhflow.py with the
      # jinja2-enabled interpreter. Locates the repo automatically (walking up from the
      # current dir, then from the design YAML's dir), so it can be run from anywhere —
      # e.g. from inside a build dir: `cd build-proj2 && pyhflow ../designs/proj2-xcel.yml`
      # (with no --out-dir it generates into the current directory). Override with
      # PYHFLOW_REPO if needed.
      pyhflow = pkgs.writeShellScriptBin "pyhflow" ''
        set -eo pipefail
        PYTHON="${pyhflowPython}/bin/python3.11"

        find_repo() {
          d="$1"
          while [ -n "$d" ] && [ "$d" != "/" ]; do
            if [ -f "$d/pyhflow.py" ] && [ -d "$d/steps" ]; then
              printf '%s\n' "$d"; return 0
            fi
            d="$(dirname "$d")"
          done
          return 1
        }

        REPO="''${PYHFLOW_REPO:-}"
        if [ -z "$REPO" ]; then REPO="$(find_repo "$PWD" || true)"; fi
        if [ -z "$REPO" ]; then
          for a in "$@"; do
            case "$a" in -*) continue ;; esac
            ad="$(cd "$(dirname "$a")" 2>/dev/null && pwd || true)"
            if [ -n "$ad" ]; then REPO="$(find_repo "$ad" || true)"; fi
            if [ -n "$REPO" ]; then break; fi
          done
        fi
        if [ -z "$REPO" ]; then
          echo "pyhflow: could not find the repo (needs pyhflow.py + steps/). cd into it or set PYHFLOW_REPO." >&2
          exit 1
        fi
        exec "$PYTHON" "$REPO/pyhflow.py" "$@"
      '';

    in {
      devShells.${system}.default = pkgs.librelane-shell.override {
        extra-packages = [
          pkgs.haskellPackages.sv2v
          pymtl3Env
          pytestWrapper
          pyhflow
        ];
      };
    };
}