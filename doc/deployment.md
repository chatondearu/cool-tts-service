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

Python dependencies are **not** installed from Nixpkgs for the app; use **`uv`** into a project virtualenv. The shell sets **`UV_PYTHON`** to the Nix `python3` so `uv` does not pick a host interpreter by mistake.

```bash
uv venv --python "${UV_PYTHON:-python3}" .venv
uv pip install --python .venv/bin/python -r production_api/requirements_api.txt
source .venv/bin/activate
```

### Smoke-test without running inference

From the repo root (with deps installed):

```bash
cd production_api && python -c "from main import app; print(app.title)"
```

Starting **`uvicorn`** loads Kokoro on startup and **requires** the `.onnx` and `voices-*.bin` files (see below).

Place Kokoro assets under `production_api/models/` (e.g. `kokoro-v1.0.onnx`, `voices-v1.0.bin`) or set `KOKORO_MODEL_PATH` / `KOKORO_VOICES_BIN_PATH`.

Run the API:

```bash
cd production_api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness/readiness probe |
| `GET` | `/voices` | List available voice ids from the loaded bundle |
| `POST` | `/generate` | Synthesize text → WAV (`text`, `language`, `voice_id`, `speed`) |

### LD_LIBRARY_PATH on NixOS/Linux

On **NixOS/Linux**, PyPI wheels (`onnxruntime`, native extensions, **`soundfile`** → `libsndfile`) need the dev shell `LD_LIBRARY_PATH`. The flake prepends **`pkgs.stdenv.cc.cc.lib`** (GCC 14 on **nixpkgs 25.11**), then **`zlib`** / **`libsndfile`**.

If **`nix develop`** or **`nix`** fails with `CXXABI_1.3.15` **before** the shell starts, the **parent** process is picking a bad `libstdc++` from `LD_LIBRARY_PATH`. Use **`direnv reload`** after updating the flake, or run **`env -u LD_LIBRARY_PATH nix develop`** once.

## Production (Docker)

Build and run from the repository root:

```bash
docker compose build
docker compose up
```

Host directories **`production_api/models/`** and **`production_api/voices/`** are mounted read-only into the container (`/app/models`, `/app/voices`). Put `kokoro-v1.0.onnx` and `voices-v1.0.bin` in `models/`.

For a **merged** voice bundle, build it with `voice_prep_module/merge_voice_bundles.py`, place it under `voices/`, and set **`KOKORO_VOICES_BIN_PATH`** (see commented example in `docker-compose.yml`).

The image exposes port **8000** and uses **`GET /health`** for the Docker healthcheck.
