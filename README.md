# cool-tts-service

Open-source **Text-to-Speech HTTP API** aimed at **fast CPU inference**, with a **modular** design so the engine can later be swapped for a heavier GPU-backed model. Includes a **Nuxt 4 web UI** for browser-based TTS generation.

## Stack

- **TTS:** [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (ONNX Runtime, lightweight on CPU)
- **API:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **UI:** [Nuxt 4](https://nuxt.com/) + [Nuxt UI v4](https://ui4.nuxt.com/) + [nuxt-auth-utils](https://nuxt.com/modules/auth-utils)
- **Python:** 3.10+ (recommended: match the Nix dev shell — **3.11**)
- **Containers:** Docker + Compose ([`generator/Dockerfile`](generator/Dockerfile), [`ui/Dockerfile`](ui/Dockerfile), [`docker-compose.yml`](docker-compose.yml))

## Layout

```text
cool-tts-service/
├── generator/                 # HTTP API + Kokoro engine wrapper
│   ├── main.py                # FastAPI app (TTS + OpenAI-compatible + admin model routes)
│   ├── model_bootstrap.py     # Optional KOKORO_AUTO_DOWNLOAD from official release
│   ├── tts_engine.py          # KokoroTTS thin wrapper
│   ├── requirements_api.txt
│   ├── Dockerfile
│   ├── models/                # kokoro-v1.0.onnx, voices-v1.0.bin (not in git)
│   └── voices/                # Custom voice bundles (not in git)
├── ui/                        # Nuxt 4 web UI
│   ├── nuxt.config.ts
│   ├── Dockerfile
│   ├── server/api/            # Auth + proxy routes to FastAPI
│   └── app/pages/             # Login, TTS, Voices pages
├── voice_prep_module/         # Offline voice preparation
│   ├── extract_voice.py       # Index WAVs + pack .pt files into npz bundle
│   ├── extract_voice_from_wav.py  # [Experimental] WAV -> placeholder embedding
│   ├── merge_voice_bundles.py # Merge official + custom npz bundles
│   ├── requirements_prep.txt
│   └── raw_audios/            # Reference WAV clips
├── doc/
│   ├── development.md         # Local dev: Nix vs without Nix, UI env, smoke tests
│   ├── deployment.md          # API summary, Docker / Coolify / NixOS library notes
│   ├── home-assistant.md      # HACS OpenAI TTS + Assist setup
│   └── voice-preparation.md   # Full voice prep guide (concepts, workflow, FAQ)
├── scripts/
│   └── dev-local.sh           # Run API + Nuxt together (outside Docker)
├── docker-compose.yml
├── flake.nix / flake.lock / .envrc
├── AGENTS.md
└── README.md
```

## Local development (two setups)

Use **either** the Nix flake **or** a plain Python + Node install. Step-by-step commands, `ui/.env`, and troubleshooting live in **[`doc/development.md`](doc/development.md)**.

**API + UI in one command** (after `.venv` + `ui/node_modules` are ready): [`./scripts/dev-local.sh`](scripts/dev-local.sh) — see [`doc/development.md`](doc/development.md#api--ui-together-one-terminal).

### With Nix

- Enter **`nix develop`** (or use **direnv** with [`.envrc`](.envrc)).
- **Python 3.11**, **`uv`**, **Node.js 22**, and **npm** are on `PATH`.
- Create `.venv`, install `generator/requirements_api.txt`, run API and UI as in [`doc/development.md`](doc/development.md).

### Without Nix

- Install **Python 3.10+** and **Node.js 22** (with npm) yourself.
- Create a venv, install API deps with **`uv`** or **`pip`**, then same API/UI commands as in [`doc/development.md`](doc/development.md).

### Model files (both setups)

Download from [kokoro-onnx releases](https://github.com/thewh1teagle/kokoro-onnx/releases) (tag `model-files-v1.0`), e.g. `kokoro-v1.0.onnx` and `voices-v1.0.bin`, into **`generator/models/`**, or set **`KOKORO_MODEL_PATH`** / **`KOKORO_VOICES_BIN_PATH`**.

Without models the API **still starts**; synthesis returns **503** until files are present (optional **`KOKORO_AUTO_DOWNLOAD=1`** — see [`doc/development.md`](doc/development.md) and [`doc/deployment.md`](doc/deployment.md)).

### Smoke tests (quick checks)

With API dependencies installed and (optionally) the server running:

```bash
# App imports (no inference)
cd generator && python -c "from main import app; print(app.title)"

# With uvicorn on :9000 — health JSON should include tts_ready
curl -sS http://127.0.0.1:9000/health
```

More checks (`/voices`, sample `/generate`) are listed in [`doc/development.md`](doc/development.md). There is no bundled **`pytest`** suite yet.

### Example API usage

**Generate speech:**

```bash
curl -sS -X POST http://127.0.0.1:9000/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Bonjour le monde.","language":"fr-fr","voice_id":"af_sarah","speed":1.0}' \
  -o speech.wav
```

**List voices:**

```bash
curl -sS http://127.0.0.1:9000/voices
```

Interactive docs: <http://127.0.0.1:9000/docs>. JSON body fields for `/generate`: `text`, `language`, `voice_id`, `speed`. See Kokoro [VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) for voice and language hints.

## Voice preparation

Kokoro uses **precomputed style vectors** (not raw audio) to define a voice. The official bundle (`voices-v1.0.bin`) ships ~50 voices; you can add your own by downloading `.pt` packs from [HuggingFace](https://huggingface.co/hexgrad/Kokoro-82M/tree/main/voices) and bundling them with the scripts in `voice_prep_module/`.

**Full step-by-step guide:** [`doc/voice-preparation.md`](doc/voice-preparation.md) — concepts, prerequisites, workflow, script reference and FAQ.

Quick summary:

```bash
# 1. Install prep dependencies (from activated .venv)
uv pip install --python .venv/bin/python -r voice_prep_module/requirements_prep.txt

# 2. Download .pt voice files into voice_prep_module/raw_audios/

# 3. Pack into a custom bundle
python voice_prep_module/extract_voice.py \
  --input-dir voice_prep_module/raw_audios \
  --output-dir generator/voices

# 4. Merge with the official bundle
python voice_prep_module/merge_voice_bundles.py \
  --base generator/models/voices-v1.0.bin \
  --overlay generator/voices/custom_voices.bin \
  --output generator/voices/merged_voices.bin

# 5. Point the API at the merged file
export KOKORO_VOICES_BIN_PATH=generator/voices/merged_voices.bin
```

## Web UI (summary)

From [`doc/development.md`](doc/development.md): configure **`ui/.env`** (copy `ui/.env.example`), then:

```bash
cd ui
npm install
npm run dev
```

Open <http://localhost:3000>. Main variables: `NUXT_SESSION_PASSWORD` (≥32 chars), `ADMIN_PASSWORD`, optional `API_BASE_URL`, `API_TOKEN`, `ADMIN_USER`.

## Docker

Copy `.env.example` to `.env` and set at minimum `NUXT_SESSION_PASSWORD` and `ADMIN_PASSWORD`.

Place `kokoro-v1.0.onnx` and `voices-v1.0.bin` under **`generator/models/`** on the host (not baked into the image). Optional voice bundles go under **`generator/voices/`**.

**Versioning:** the app SemVer lives in the root [`VERSION`](VERSION) file; `GET /health` returns `app_version`. Release notes: [`CHANGELOG.md`](CHANGELOG.md).

### Pre-built images (no `docker build`)

After a Git tag `v*` is pushed, CI publishes images to `ghcr.io/chatondearu/cool-tts-service-api` and `ghcr.io/chatondearu/cool-tts-service-ui`. Pull and run with [`docker-compose.image.yml`](docker-compose.image.yml) (set `COOL_TTS_IMAGE_TAG` in `.env`). See [`doc/deployment.md`](doc/deployment.md#pre-built-images-install-without-building).

### Local (without Traefik)

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

- UI: <http://localhost:3000>
- API health: `GET http://localhost:9000/health`
- API docs: <http://localhost:9000/docs>

Host ports: `API_PORT` and `UI_PORT` in `.env` (defaults: 9000 / 3000). The local override disables Traefik labels and sets `ROOT_PATH` to empty.

### Coolify / single-domain deployment

The main `docker-compose.yml` ships with **Traefik labels** for single-domain routing: UI at `/`, API under `/tts-server`. See [`doc/deployment.md`](doc/deployment.md) for Coolify env vars, Open WebUI / Home Assistant URLs, and merged voice bundles.

## Roadmap / TODO

- [ ] **Kokoro style encoder** — watch upstream [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) for a real WAV → style-vector extractor. Will replace the placeholder `extract_voice_from_wav.py` (random embeddings) and enable zero-shot voice cloning while keeping CPU inference lightweight.
- [ ] **Piper TTS as alternative engine** — if Kokoro voice cloning stays unavailable, consider swapping to [Piper](https://github.com/rhasspy/piper):
  - ONNX models very lightweight (~15–60 MB), CPU friendly (runs on RPi).
  - **Native Home Assistant integration** (primary use-case).
  - Many pre-trained French voices available.
  - Fine-tuning via VITS pipeline (requires GPU + ~30 min of audio).
  - `tts_engine.py` is already designed for a modular engine swap.

## Contributing / agents

For automation and repository conventions, see [`AGENTS.md`](AGENTS.md).

## License

Specify in this file once you choose a license for the service code (Kokoro / kokoro-onnx have their own licenses — check upstream notices).
