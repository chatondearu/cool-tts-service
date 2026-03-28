{
  description = "cool-tts-service — dev shell (Python 3.11 + libs aligned with Docker)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSystem = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forEachSystem (pkgs:
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python311
              uv
              curl
              git
              ffmpeg
              libsndfile
              pkg-config
              # Common build deps for pip wheels with native extensions
              openssl
            ];

            shellHook = ''
              _root="$(git rev-parse --show-toplevel 2>/dev/null)" || true
              export REPO_ROOT="''${_root:-$PWD}"
              export VOICES_DIR="''${VOICES_DIR:-$REPO_ROOT/app/voices}"
              export CACHE_DIR="''${CACHE_DIR:-$REPO_ROOT/app/cache}"
              mkdir -p "$CACHE_DIR" "$VOICES_DIR/default" "$VOICES_DIR/custom"
              echo "cool-tts-service (Nix shell): Python $(python3 --version | cut -d' ' -f2), uv $(uv --version | head -1)"
              echo "  VOICES_DIR=$VOICES_DIR  CACHE_DIR=$CACHE_DIR"
              echo "  Venv + deps:  uv venv --python python3 .venv && source .venv/bin/activate && uv pip install -r app/requirements.txt"
            '';
          };
        });
    };
}
