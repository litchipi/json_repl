{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-22.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = inputs: inputs.flake-utils.lib.eachDefaultSystem (system: let
    pkgs = import inputs.nixpkgs { inherit system; };
    lib = pkgs.lib;

    python_version = pkgs.python310;
    python_packages_version = pkgs.python310Packages;
    pythonpkg = python_version.withPackages (p: with p; [
    ]);

    repl_script = pkgs.writeShellScript "json_repl" "${pythonpkg}/bin/python3 ${./json_repl.py} $@";
  in {
    # TODO    Add tool to overlay
    # overlays.default = prev: final: {};
    packages.default = repl_script;
    apps.default = { type = "app"; program = "${repl_script}"; };
    devShells.default = pkgs.mkShell {
      buildInputs = [
        pythonpkg
      ];
      PYTHONPATH = "${pythonpkg}/${pythonpkg.sitePackages}:$PYTHONPATH";
      LD_LIBRARY_PATH = "${pkgs.stdenv.cc.cc.lib}/lib$LD_LIBRARY_PATH";
    };
  });
}
