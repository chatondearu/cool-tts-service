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
uv pip install --python .venv/bin/python -r generator/requirements_api.txt
source .venv/bin/activate
```

### Smoke-test without running inference

From the repo root (with deps installed):

```bash
cd generator && python -c "from main import app; print(app.title)"
```

Starting **`uvicorn`** loads Kokoro on startup and **requires** the `.onnx` and `voices-*.bin` files (see below).

Place Kokoro assets under `generator/models/` (e.g. `kokoro-v1.0.onnx`, `voices-v1.0.bin`) or set `KOKORO_MODEL_PATH` / `KOKORO_VOICES_BIN_PATH`.

Run the API:

```bash
cd generator
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

**Open WebUI** — set the custom TTS base URL to `http://<host>:8000/v1` (local) or `https://<domain>/tts-server/v1` (Coolify) and optionally provide the `API_TOKEN` as API key.

**Home Assistant** (`openai_tts` HACS integration) — set the endpoint URL to `http://<host>:8000/v1/audio/speech` (local) or `https://<domain>/tts-server/v1/audio/speech` (Coolify); leave the API key empty if `API_TOKEN` is not set.

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

The main `docker-compose.yml` is configured for **Coolify / Traefik** (labels, `ROOT_PATH=/tts-server`, no host port mapping). It uses **Coolify magic environment variables** so secrets can be generated automatically on deploy (see [Magic Environment Variables](https://coolify.io/docs/knowledge-base/environment-variables#magic-environment-variables-docker-compose)):

| Compose default chain | Coolify generates |
|----------------------|-------------------|
| `SERVICE_BASE64_64_TTS_API` | Long random string for `API_TOKEN` / `NUXT_API_TOKEN` (when `API_TOKEN` is unset) |
| `SERVICE_PASSWORD_64_TTS_SESSION` | Random password for `NUXT_SESSION_PASSWORD` (when unset) |
| `SERVICE_PASSWORD_64_TTS_ADMIN` | Random password for admin login (when `ADMIN_PASSWORD` is unset) |

Coolify detects these names from the compose file and pre-fills them in the UI; values stay stable across redeploys. **`COOLIFY_RESOURCE_UUID`** and other [predefined variables](https://coolify.io/docs/knowledge-base/environment-variables#predefined-variables) remain available if you add your own mappings.

If you run **only** `docker-compose.yml` outside Coolify (no `.env`), those fallbacks resolve to empty strings—set `NUXT_SESSION_PASSWORD`, `ADMIN_PASSWORD`, and optionally `API_TOKEN` explicitly. **Local development** without a reverse proxy should layer the local override, which keeps strict checks for UI secrets:

For **local development** without a reverse proxy, layer the local override:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

This adds host port mappings and disables Traefik labels / `ROOT_PATH`. Override the host ports in `.env` if the defaults conflict:

```bash
API_PORT=9000
UI_PORT=3001
```

Two services start:

- **`api`** (host port `API_PORT`, default 8000) — FastAPI TTS backend. Host directories **`generator/models/`** and **`generator/voices/`** are mounted read-only.
- **`ui`** (host port `UI_PORT`, default 3000) — Nuxt web UI. Waits for the API healthcheck before starting.

For Coolify, use the main compose file directly (`docker compose up`); Traefik handles routing — see below.

Put `kokoro-v1.0.onnx` and `voices-v1.0.bin` in `generator/models/`.

For a **merged** voice bundle, build it with `voice_prep_module/merge_voice_bundles.py`, place it under `generator/voices/`, and set **`KOKORO_VOICES_BIN_PATH`** (see commented example in `docker-compose.yml`).

To secure the FastAPI with a Bearer token, set **`API_TOKEN`** in `.env`; the UI will inject it automatically when proxying requests.

### Coolify / single-domain deployment

The compose file includes **Traefik labels** for single-domain routing behind Coolify (or any Traefik-managed platform):

- **UI** serves at the domain root (`/`)
- **API** serves under `/tts-server` (Traefik strips the prefix before forwarding to the container)

Coolify detects the labels automatically. In the Coolify UI, assign one domain to the stack (e.g. `https://tts.example.com`). The `ports:` section is **not used** by Traefik — it routes via the internal Docker network. `API_PORT` / `UI_PORT` only matter for local development.

External tools that talk to the API use the `/tts-server` prefix:

- **Open WebUI** — TTS base URL: `https://tts.example.com/tts-server/v1`
- **Home Assistant** (`openai_tts`) — endpoint: `https://tts.example.com/tts-server/v1/audio/speech`
- **Swagger docs** — `https://tts.example.com/tts-server/docs`

The `ROOT_PATH` env var (set to `/tts-server` in docker-compose) tells FastAPI it is served behind a prefix so Swagger UI and OpenAPI schema URLs resolve correctly.
