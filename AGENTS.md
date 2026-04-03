# AGENTS — repository guide for humans and coding agents

## Where to look first

1. **Root [`README.md`](README.md)** — goals, layout, quick start, API example.
2. **This file** — paths, env vars, and workflow expectations.
3. **[`doc/development.md`](doc/development.md)** — local dev **with Nix** vs **without Nix**, UI `.env`, smoke tests.
4. **[`doc/deployment.md`](doc/deployment.md)** — API summary, Docker / Coolify, `LD_LIBRARY_PATH` on NixOS/Linux.
5. **[`doc/home-assistant.md`](doc/home-assistant.md)** — Home Assistant HACS `openai_tts` (URL, token, profile, `response_format: wav`).
6. **[`doc/litellm.md`](doc/litellm.md)** — LiteLLM proxy integration (`api_base`, `openai/kokoro-v1.0`, YAML + UI).
7. **[`doc/voice-preparation.md`](doc/voice-preparation.md)** — full voice prep guide (concepts, workflow, script reference, FAQ).
8. **[`.cursor/rules/`](.cursor/rules/)** — project rules (Nix discovery, Conventional Commits, doc sync).

Do **not** assume historical layouts (e.g. `app/requirements.txt`). **Infer** dependency and source paths from the tree or these docs.

**Automation / agents:** run project commands inside the Nix dev shell so **Node.js 22**, **npm**, **Python**, and **`uv`** match the flake. From repo root use `nix develop` (interactive) or one-shot `nix develop --command '…'` (e.g. `nix develop --command 'cd ui && npm run build'`). Do not assume a system-wide `node`/`npm` outside the flake unless the user explicitly uses the non-Nix path in [`doc/development.md`](doc/development.md).

## Project shape

| Area | Role |
|------|------|
| [`generator/main.py`](generator/main.py) | FastAPI app, lifespan, internal routes (`POST /generate`, `GET /voices`, `GET /health`) + OpenAI-compatible routes + admin routes (`/admin/models/…`, `/admin/synthesis-logs`) |
| [`generator/synthesis_logging.py`](generator/synthesis_logging.py) | Structured synthesis logs (JSON lines + in-memory ring buffer for the UI) |
| [`generator/model_bootstrap.py`](generator/model_bootstrap.py) | Optional `KOKORO_AUTO_DOWNLOAD` fetch from kokoro-onnx `model-files-v1.0` release |
| [`generator/tts_engine.py`](generator/tts_engine.py) | `KokoroTTS` — thin wrapper (24 kHz, `list_voices`, `generate_audio`) |
| [`generator/requirements_api.txt`](generator/requirements_api.txt) | API + inference dependencies |
| [`generator/models/`](generator/models/) | `kokoro-v1.0.onnx`, `voices-v1.0.bin` (local; large files ignored by git) |
| [`generator/Dockerfile`](generator/Dockerfile) | API image; models/voices mounted at run time |
| [`docker-compose.yml`](docker-compose.yml) | `api` + `ui` services (Coolify magic `SERVICE_URL_COOLTTS_*` for same-host routing) |
| [`docker-compose.local.yml`](docker-compose.local.yml) | Local override: host ports, no Traefik labels, no `ROOT_PATH` |
| [`ui/`](ui/) | Nuxt 4 web UI (Nuxt UI v4, nuxt-auth-utils) |
| [`ui/nuxt.config.ts`](ui/nuxt.config.ts) | Nuxt configuration |
| [`ui/server/api/`](ui/server/api/) | Auth routes + proxy to FastAPI |
| [`ui/app/pages/`](ui/app/pages/) | Login, TTS, Voices, Model files, Synthesis logs |
| [`ui/Dockerfile`](ui/Dockerfile) | UI image (Node 22, multi-stage) |
| [`voice_prep_module/extract_voice.py`](voice_prep_module/extract_voice.py) | Index WAVs + pack `.pt` files into npz bundle |
| [`voice_prep_module/extract_voice_from_wav.py`](voice_prep_module/extract_voice_from_wav.py) | **[Experimental]** WAV → random embedding placeholder |
| [`voice_prep_module/merge_voice_bundles.py`](voice_prep_module/merge_voice_bundles.py) | Merge official + custom npz bundles |
| [`voice_prep_module/requirements_prep.txt`](voice_prep_module/requirements_prep.txt) | Offline prep dependencies (torch, numpy, soundfile) |
| [`voice_prep_module/raw_audios/`](voice_prep_module/raw_audios/) | Reference WAV clips (e.g. `nemo_0_FR.wav`) |
| [`generator/voices/`](generator/voices/) | Generated bundles + manifests (gitignored except `.gitkeep`) |
| [`doc/voice-preparation.md`](doc/voice-preparation.md) | Full voice prep guide (concepts, workflow, script ref, FAQ) |
| [`flake.nix`](flake.nix) / [`flake.lock`](flake.lock) | Dev shell (Python 3.11, `uv`, Node.js 22 + npm, audio libs) |

## Environment variables

| Variable | Purpose |
|----------|---------|
| `KOKORO_MODEL_PATH` | Override path to Kokoro `.onnx` |
| `KOKORO_VOICES_BIN_PATH` | Override path to `voices-*.bin` |
| `KOKORO_AUTO_DOWNLOAD` | If truthy, download missing official ONNX/voices from GitHub when dirs are writable |
| `KOKORO_ONNX_VARIANT` | `f32` (default), `int8`, or `fp16` — which ONNX asset to fetch when auto-download runs |
| `API_TOKEN` | Optional Bearer token to secure the FastAPI (shared with UI) |
| `UV_PYTHON` | Set by Nix shell so `uv` uses the Nix interpreter (optional elsewhere) |
| `NUXT_SESSION_PASSWORD` | Encryption key for UI session cookies (min 32 chars) |
| `API_BASE_URL` | FastAPI URL for the Nuxt server (default `http://localhost:9000`) |
| `ADMIN_USER` | UI login username (default `admin`) |
| `ADMIN_PASSWORD` | UI login password |
| `API_PORT` | Host port for the API container (default `9000`; ignored by Coolify) |
| `UI_PORT` | Host port for the UI container (default `3000`; ignored by Coolify) |
| `ROOT_PATH` | FastAPI root path prefix for reverse-proxy deployments (default empty; set to `/tts-server` in docker-compose) |
| `TTS_SYNTHESIS_LOG_BUFFER_MAX` | Optional: max entries in the in-memory synthesis log ring buffer (default `500`) |

## API endpoints

### Internal (used by the Nuxt UI)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe; includes `app_version`, `tts_ready`, optional `tts_error` |
| `GET` | `/voices` | List voice ids (empty if engine not loaded) |
| `POST` | `/generate` | Synthesize text → WAV; **503** if no engine |
| `GET` | `/admin/models/status` | Model paths, file status (requires `API_TOKEN` when set) |
| `POST` | `/admin/models/upload` | Multipart `onnx` / `voices_bin` |
| `POST` | `/admin/models/reload` | Reload engine from disk |
| `GET` | `/admin/synthesis-logs` | Recent synthesis events (ring buffer); query `limit`, `errors_only`, `client`, `route` |

### OpenAI-compatible (Open WebUI, Home Assistant `openai_tts`, etc.)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/models` | List models (`kokoro-v1.0` when loaded; empty when not) |
| `GET` | `/v1/audio/voices` | List voices as `[{"id": …, "name": …}]` |
| `POST` | `/v1/audio/speech` | Synthesize text → WAV (body: `model`, `input`, `voice`, `speed`, optional `language`, `response_format`); **503** if no engine |

The `language` field on `/v1/audio/speech` is a non-standard extension: when omitted, the language is inferred from the Kokoro voice prefix (e.g. `af_` → `en-us`, `ff_` → `fr-fr`).

## Commands (typical)

From repo root after `nix develop` and `uv venv`:

```bash
uv pip install --python .venv/bin/python -r generator/requirements_api.txt
source .venv/bin/activate
cd generator && uvicorn main:app --reload --host 0.0.0.0 --port 9000
```

**API + UI (local stack, one terminal):** from repo root, `./scripts/dev-local.sh` (requires `.venv` with `uvicorn`, `ui/node_modules`; see [`doc/development.md`](doc/development.md#api--ui-together-one-terminal)).

(`UV_PYTHON` is set in the Nix shell; without `--python .venv/bin/python`, `uv pip` may try to write into the read-only Nix interpreter.)

**Voice prep** (torch + numpy; separate from API venv if you prefer):

```bash
uv pip install --python .venv/bin/python -r voice_prep_module/requirements_prep.txt
python voice_prep_module/extract_voice.py
```

Kokoro ONNX does **not** build new style vectors from raw `.wav` here; the script packs Hugging Face–style `*.pt` clips and inventories WAV metadata. Set `KOKORO_VOICES_BIN_PATH` to `generator/voices/custom_voices.bin` when using a custom bundle.

**Experimental WAV → embedding** (random placeholder — NOT a real extraction):

```bash
python voice_prep_module/extract_voice_from_wav.py --wav voice_prep_module/raw_audios/nemo_0_FR.wav
```

**Merge official + custom bundles** (numpy only):

```bash
python voice_prep_module/merge_voice_bundles.py \
  --base generator/models/voices-v1.0.bin \
  --overlay generator/voices/custom_voices.bin \
  --output generator/voices/merged_voices.bin
```

**Docker (local):** `docker compose -f docker-compose.yml -f docker-compose.local.yml up --build` from repo root; probe `GET /health`.

**Docker (Coolify):** `docker compose up` — Traefik routes `/tts-server` to the API and `/` to the UI.

After changing flake **inputs**, run `nix flake lock` and commit **`flake.lock`** with **`flake.nix`**.

## Commits

Follow **Conventional Commits** (see [`.cursor/rules/conventional-commits.mdc`](.cursor/rules/conventional-commits.mdc)): English, imperative subject, optional scope (`api`, `nix`, `tts`, …).

## Editing Nix

See [`.cursor/rules/nix-development.mdc`](.cursor/rules/nix-development.mdc): prefer README / AGENTS / scanned layout over copy-pasting patterns from other repos.

## Out of scope unless requested

- Do not commit large `.onnx` / `.bin` assets; `.gitignore` covers `generator/models/*.onnx`, `generator/models/*.bin`, and `generator/voices/*.bin`.
