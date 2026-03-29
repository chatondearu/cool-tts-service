# Deployment and local development

See the root [`README.md`](../README.md) for project goals and layout; this file focuses on how to run and ship the service.

## Nix development shell (workstation)

From the repository root:

```bash
nix develop
```

Or with **direnv** (after `direnv allow` once):

```bash
cd /path/to/cool-tts-service
# .envrc loads the flake automatically
```

The dev shell pins **Python 3.11** via Nix (`python311`); the app targets **3.10+**, so you can point `uv` at another interpreter if needed.

Python dependencies are **not** installed from Nixpkgs for the app; use **`uv`** into a project virtualenv. The shell sets **`UV_PYTHON`** to the Nix `python3` when possible so `uv` does not pick a host interpreter by mistake.

```bash
uv venv --python "${UV_PYTHON:-python3}" .venv
# The dev shell sets UV_PYTHON to Nix's python; point uv explicitly at the venv
# (or run `unset UV_PYTHON` after activate) so installs go into `.venv`, not `/nix/store`.
uv pip install --python .venv/bin/python -r production_api/requirements_api.txt
source .venv/bin/activate
```

### Smoke-test without running inference

From the repo root (with deps installed as above):

```bash
cd production_api && python -c "from main import app; print(app.title)"
```

Starting **`uvicorn`** loads Kokoro on startup and **requires** the `.onnx` and `voices-*.bin` files (see below).

Offline voice bundling (`extract_voice.py`, optional torch) is documented in the root [`README.md`](../README.md) under **Voice preparation (Phase 3)**.

Place Kokoro assets under `production_api/models/` (e.g. `kokoro-v1.0.onnx`, `voices-v1.0.bin`) or set `KOKORO_MODEL_PATH` / `KOKORO_VOICES_BIN_PATH`.

Run the API:

```bash
cd production_api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On **NixOS/Linux**, PyPI wheels (`onnxruntime`, native extensions, **`soundfile`** → `libsndfile`) may need the dev shell `LD_LIBRARY_PATH`. The flake prepends **`pkgs.stdenv.cc.cc.lib`** (GCC 14 on **nixpkgs 25.11**), then **`zlib`** / **`libsndfile`** (`flake.nix`). That satisfies Nix 2.31’s `libstdc++` (`CXXABI_1.3.15`) and overrides a stale inherited **`gcc-13.3.0-lib`** segment (old direnv cache / another flake), which would otherwise break **`nix`** inside the shell.

If **`nix develop`** or **`nix`** still fails with `CXXABI_1.3.15` **before** the shell starts, the **parent** process is picking a bad `libstdc++` from `LD_LIBRARY_PATH` and the flake has not run yet. Use **`direnv reload`** after updating the flake, or run **`env -u LD_LIBRARY_PATH nix develop`** once. If a wheel still fails to load, extend `makeLibraryPath` or use **`nix-ld`**.

## Production

The intended production path is **Docker** (`production_api/Dockerfile` and root `docker-compose.yml`). Those files are **not** in the tree until Phase 4 lands; use Nix plus a venv for local development today.
