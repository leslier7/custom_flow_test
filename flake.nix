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

    in {
      devShells.${system}.default = pkgs.librelane-shell.override {
        extra-packages = [
          pkgs.haskellPackages.sv2v
          pymtl3Env
          pytestWrapper
        ];
      };
    };
}