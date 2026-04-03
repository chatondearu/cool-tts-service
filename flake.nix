{
  description = "cool-tts-service — flake dev shell (uv + Python 3.11, Node.js 22 + npm for UI, audio / PyPI wheels)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python311
              uv
              nodejs_22
              curl
              ffmpeg-headless
              libsndfile
            ];

            shellHook =
              (pkgs.lib.optionalString pkgs.stdenv.isLinux ''
                # PyPI wheels need libstdc++ / zlib / libsndfile on NixOS. Prepend
                # stdenv.cc.cc.lib first: nixpkgs 25.11 ships GCC 14, whose libstdc++
                # satisfies Nix 2.31 (CXXABI_1.3.15). That also wins over a stale inherited
                # gcc-13 path (old direnv cache / other flakes), which used to break `nix`.
                export LD_LIBRARY_PATH="${
                  pkgs.lib.makeLibraryPath [
                    pkgs.stdenv.cc.cc.lib
                    pkgs.zlib
                    pkgs.libsndfile
                  ]
                }''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
              '')
              + ''
                # Prefer the Nix-provided interpreter for uv (avoids picking a host python).
                if command -v python3 >/dev/null 2>&1; then
                  export UV_PYTHON="''${UV_PYTHON:-$(command -v python3)}"
                fi
                echo "cool-tts-service dev shell (Python 3.11, Node.js $(node -v 2>/dev/null || echo '?') + npm — app supports Python 3.10+)"
                echo "  uv venv:  uv venv --python ''${UV_PYTHON:-python3} .venv && source .venv/bin/activate"
                echo "  deps:     uv pip install --python .venv/bin/python -r generator/requirements_api.txt"
                echo "  optional: uv pip install -r voice_prep_module/requirements_prep.txt"
                echo "  API:      cd generator && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
                echo "  UI:       cd ui && npm install && npm run dev"
                echo "  dev docs: doc/development.md (without Nix: same API/UI steps with host Python 3.10+ + Node 22)"
              '';
          };
        }
      );
    };
}
