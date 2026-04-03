# Deployment

See the root [`README.md`](../README.md) for project goals and layout.

- **[`doc/development.md`](development.md)** — local development **with Nix** or **without Nix**, UI `.env`, and **smoke tests**.
- **[`doc/home-assistant.md`](home-assistant.md)** — Home Assistant **HACS** `openai_tts` setup (URL, API token, first profile, `response_format`).
- **This document** — API reference, NixOS `LD_LIBRARY_PATH` notes, Docker / Coolify / Traefik.

## API behavior (models and startup)

Starting **uvicorn** attempts to load Kokoro. If the `.onnx` and `voices-*.bin` files are **missing or invalid**, the API **still starts**: synthesis returns **503** with a `detail`, while `GET /health` stays **200** and includes `app_version` (SemVer from the repo `VERSION` file), `tts_ready`, and `tts_error` when the engine is not loaded.

Place assets under `generator/models/` or set `KOKORO_MODEL_PATH` / `KOKORO_VOICES_BIN_PATH`. Optional first-boot download: `KOKORO_AUTO_DOWNLOAD=1` and `KOKORO_ONNX_VARIANT` (`f32`, `int8`, `fp16`) — see [`development.md`](development.md). Docker Compose can pass these from the host `.env`.

### API endpoints

#### Internal (used by the Nuxt UI)


| Method | Path        | Description                                                     |
| ------ | ----------- | --------------------------------------------------------------- |
| `GET`  | `/health`   | Liveness probe; JSON includes `app_version`, `tts_ready`, and optional `tts_error` |
| `GET`  | `/voices`   | List voice ids (empty list if TTS is not loaded)                |
| `POST` | `/generate` | Synthesize text → WAV (`text`, `language`, `voice_id`, `speed`); **503** if TTS is not loaded |

#### Admin (when `API_TOKEN` is set, use `Authorization: Bearer …`)

| Method | Path                     | Description |
| ------ | ------------------------ | ----------- |
| `GET`  | `/admin/models/status`   | Resolved paths, file presence, sizes, `tts_ready` |
| `POST` | `/admin/models/upload`   | Multipart: optional `onnx` and/or `voices_bin` (writes to configured paths) |
| `POST` | `/admin/models/reload`   | Reload Kokoro from disk into the running process |


#### OpenAI-compatible (Open WebUI, Home Assistant, etc.)

These routes let external tools that speak the OpenAI TTS protocol use the same Kokoro engine without any adapter:


| Method | Path               | Description                                                                     |
| ------ | ------------------ | ------------------------------------------------------------------------------- |
| `GET`  | `/v1/models`       | List models (`kokoro-v1.0` when loaded; **empty** `data` if TTS is not ready)      |
| `GET`  | `/v1/audio/voices` | List voices as `[{"id", "name"}]`                                               |
| `POST` | `/v1/audio/speech` | Synthesize text → WAV (`model`, `input`, `voice`, `speed`, optional `language`); **503** if TTS is not loaded |


When `language` is omitted from `/v1/audio/speech`, it is inferred from the voice prefix (e.g. `af_` → `en-us`, `ff_` → `fr-fr`). Only `response_format=wav` is supported for now.

**Open WebUI** — set the custom TTS base URL to `http://<host>:9000/v1` (local) or `https://<domain>/tts-server/v1` (Coolify) and optionally provide the `API_TOKEN` as API key.

**Home Assistant** (`openai_tts` HACS integration) — use the full speech URL (`…/v1/audio/speech`), optional Bearer token when `API_TOKEN` is set, model `kokoro-v1.0`, and **Extra payload** `{"response_format":"wav"}` (the integration defaults to `mp3`, which this API rejects). Step-by-step: [`doc/home-assistant.md`](home-assistant.md).

### LD_LIBRARY_PATH on NixOS/Linux

On **NixOS/Linux**, PyPI wheels (`onnxruntime`, native extensions, `**soundfile`** → `libsndfile`) need the dev shell `LD_LIBRARY_PATH`. The flake prepends `**pkgs.stdenv.cc.cc.lib**` (GCC 14 on **nixpkgs 25.11**), then `**zlib`** / `**libsndfile**`.

If `**nix develop**` or `**nix**` fails with `CXXABI_1.3.15` **before** the shell starts, the **parent** process is picking a bad `libstdc++` from `LD_LIBRARY_PATH`. Use `**direnv reload`** after updating the flake, or run `**env -u LD_LIBRARY_PATH nix develop**` once.

## Web UI (local)

Run the Nuxt app with Node 22 + npm; full **Nix vs non-Nix** steps and `ui/.env` are in [`development.md`](development.md).

## Production (Docker)

### Pre-built images (install without building)

Published on **GitHub Container Registry** when you push a Git tag `v*` (see `.github/workflows/release.yml`):

- `ghcr.io/chatondearu/cool-tts-service-api:<tag>`
- `ghcr.io/chatondearu/cool-tts-service-ui:<tag>`

Use the same tag for both services (e.g. `v1.0.0` or `latest`). From a repo checkout (for `docker-compose.image.yml` paths and host volumes):

1. Copy `.env.example` to `.env` and set secrets as below.
2. Set `COOL_TTS_IMAGE_TAG` in `.env` (e.g. `v1.0.0` or `latest`).
3. Run:

```bash
docker compose -f docker-compose.image.yml up -d
```

For **local ports**, layer `docker-compose.local.yml` as with the build-based stack:

```bash
docker compose -f docker-compose.image.yml -f docker-compose.local.yml up -d
```

Images do **not** bundle Kokoro ONNX/voices; keep using `generator/models/` (and optional `generator/voices/`) on the host, or enable `KOKORO_AUTO_DOWNLOAD` as documented below.

On first use, open the **Packages** settings for your GitHub org/user and set each package visibility to **Public** if anonymous `docker pull` should work.

### Build from source (default compose)

Copy `.env.example` to `.env` at the repo root and set at minimum:

- `NUXT_SESSION_PASSWORD` (min 32 chars)
- `ADMIN_PASSWORD`

The main `docker-compose.yml` is configured for **Coolify / Traefik** (labels, `ROOT_PATH=/tts-server`, no host port mapping). It uses **Coolify magic environment variables** so secrets can be generated automatically on deploy (see [Magic Environment Variables](https://coolify.io/docs/knowledge-base/environment-variables#magic-environment-variables-docker-compose)):


| Compose default chain             | Coolify generates                                                                 |
| --------------------------------- | --------------------------------------------------------------------------------- |
| `SERVICE_BASE64_64_API_TOKEN`       | Long random string for `API_TOKEN` / `NUXT_API_TOKEN` |
| `SERVICE_PASSWORD_SESSION` | Random password for `NUXT_SESSION_PASSWORD`                       |
| `SERVICE_PASSWORD_ADMIN`   | Random password for admin login                 |


Coolify detects these names from the compose file and pre-fills them in the UI; values stay stable across redeploys. `**COOLIFY_RESOURCE_UUID`** and other [predefined variables](https://coolify.io/docs/knowledge-base/environment-variables#predefined-variables) remain available if you add your own mappings.

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

- `**api**` (host port `API_PORT`, default 9000) — FastAPI TTS backend. Host directories `**generator/models/**` and `**generator/voices/**` are mounted **read-write** so `KOKORO_AUTO_DOWNLOAD` and `POST /admin/models/upload` can persist files.
- `**ui**` (host port `UI_PORT`, default 3000) — Nuxt web UI. Waits for the API healthcheck before starting.

For Coolify, use the main compose file directly (`docker compose up`); Traefik handles routing — see below.

Put `kokoro-v1.0.onnx` and `voices-v1.0.bin` in `generator/models/`.

For a **merged** voice bundle, build it with `voice_prep_module/merge_voice_bundles.py`, place it under `generator/voices/`, and set `**KOKORO_VOICES_BIN_PATH`** (see commented example in `docker-compose.yml`).

To secure the FastAPI with a Bearer token, set `**API_TOKEN**` in `.env`; the UI will inject it automatically when proxying requests.

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