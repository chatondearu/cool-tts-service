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
uv pip install --python .venv/bin/python -r api/requirements_api.txt
source .venv/bin/activate
```

### Smoke-test without running inference

From the repo root (with deps installed):

```bash
cd api && python -c "from main import app; print(app.title)"
```

Starting **`uvicorn`** loads Kokoro on startup and **requires** the `.onnx` and `voices-*.bin` files (see below).

Place Kokoro assets under `api/models/` (e.g. `kokoro-v1.0.onnx`, `voices-v1.0.bin`) or set `KOKORO_MODEL_PATH` / `KOKORO_VOICES_BIN_PATH`.

Run the API:

```bash
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API endpoints

#### Internal (used by the Nuxt UI)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness/readiness probe |
| `GET` | `/voices` | List available voice ids from the loaded bundle |
| `POST` | `/generate` | Synthesize text → WAV (`text`, `language`, `voice_id`, `speed`) |

#### OpenAI-compatible (Open WebUI, Home Assistant, etc.)

These routes let external tools that speak the OpenAI TTS protocol use the same Kokoro engine without any adapter:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/models` | List models (`kokoro-v1.0`) |
| `GET` | `/v1/audio/voices` | List voices as `[{"id", "name"}]` |
| `POST` | `/v1/audio/speech` | Synthesize text → WAV (`model`, `input`, `voice`, `speed`, optional `language`) |

When `language` is omitted from `/v1/audio/speech`, it is inferred from the voice prefix (e.g. `af_` → `en-us`, `ff_` → `fr-fr`). Only `response_format=wav` is supported for now.

**Open WebUI** — set the custom TTS base URL to `http://<host>:8000/v1` (local) or `https://<domain>/api/v1` (Coolify) and optionally provide the `API_TOKEN` as API key.

**Home Assistant** (`openai_tts` HACS integration) — set the endpoint URL to `http://<host>:8000/v1/audio/speech` (local) or `https://<domain>/api/v1/audio/speech` (Coolify); leave the API key empty if `API_TOKEN` is not set.

### LD_LIBRARY_PATH on NixOS/Linux

On **NixOS/Linux**, PyPI wheels (`onnxruntime`, native extensions, **`soundfile`** → `libsndfile`) need the dev shell `LD_LIBRARY_PATH`. The flake prepends **`pkgs.stdenv.cc.cc.lib`** (GCC 14 on **nixpkgs 25.11**), then **`zlib`** / **`libsndfile`**.

If **`nix develop`** or **`nix`** fails with `CXXABI_1.3.15` **before** the shell starts, the **parent** process is picking a bad `libstdc++` from `LD_LIBRARY_PATH`. Use **`direnv reload`** after updating the flake, or run **`env -u LD_LIBRARY_PATH nix develop`** once.

## Web UI (local)

The Nuxt 4 UI lives in `ui/`. Node.js is not in the Nix dev shell by default; use `nix shell nixpkgs#nodejs_22`:

```bash
cd ui
nix shell nixpkgs#nodejs_22 --command bash
npm install
npm run dev
```

The UI runs on `http://localhost:3000`. Set `API_BASE_URL`, `ADMIN_USER`, and `ADMIN_PASSWORD` in `ui/.env` (copy from `ui/.env.example`).

## Production (Docker)

Copy `.env.example` to `.env` at the repo root and set at minimum:

- `NUXT_SESSION_PASSWORD` (min 32 chars)
- `ADMIN_PASSWORD`

Build and run from the repository root:

```bash
docker compose build
docker compose up
```

Two services start:

- **`api`** (host port `API_PORT`, default 8000) — FastAPI TTS backend. Host directories **`api/models/`** and **`api/voices/`** are mounted read-only.
- **`ui`** (host port `UI_PORT`, default 3000) — Nuxt web UI. Waits for the API healthcheck before starting.

Override the host ports in `.env` if the defaults conflict with other services:

```bash
API_PORT=9000
UI_PORT=3001
```

Put `kokoro-v1.0.onnx` and `voices-v1.0.bin` in `api/models/`.

For a **merged** voice bundle, build it with `voice_prep_module/merge_voice_bundles.py`, place it under `api/voices/`, and set **`KOKORO_VOICES_BIN_PATH`** (see commented example in `docker-compose.yml`).

To secure the FastAPI with a Bearer token, set **`API_TOKEN`** in `.env`; the UI will inject it automatically when proxying requests.

### Coolify / single-domain deployment

The compose file includes **Traefik labels** for single-domain routing behind Coolify (or any Traefik-managed platform):

- **UI** serves at the domain root (`/`)
- **API** serves under `/api` (Traefik strips the prefix before forwarding to the container)

Coolify detects the labels automatically. In the Coolify UI, assign one domain to the stack (e.g. `https://tts.example.com`). The `ports:` section is **not used** by Traefik — it routes via the internal Docker network. `API_PORT` / `UI_PORT` only matter for local development.

External tools that talk to the API use the `/api` prefix:

- **Open WebUI** — TTS base URL: `https://tts.example.com/api/v1`
- **Home Assistant** (`openai_tts`) — endpoint: `https://tts.example.com/api/v1/audio/speech`
- **Swagger docs** — `https://tts.example.com/api/docs`

The `ROOT_PATH` env var (set to `/api` in docker-compose) tells FastAPI it is served behind a prefix so Swagger UI and OpenAPI schema URLs resolve correctly.
