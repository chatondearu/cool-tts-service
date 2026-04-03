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
│   ├── deployment.md          # Nix + Docker + production notes
│   └── voice-preparation.md   # Full voice prep guide (concepts, workflow, FAQ)
├── docker-compose.yml
├── flake.nix / flake.lock / .envrc
├── AGENTS.md
└── README.md
```

## Quick start (local)

### 1. Toolchain

Use **Nix** + **uv** (see [`doc/deployment.md`](doc/deployment.md) for details):

```bash
nix develop
uv venv --python "${UV_PYTHON:-python3}" .venv
uv pip install --python .venv/bin/python -r generator/requirements_api.txt
source .venv/bin/activate
```

Without Nix, use Python **3.10+** and install `generator/requirements_api.txt` into a virtualenv.

### 2. Model files

Download from [kokoro-onnx releases](https://github.com/thewh1teagle/kokoro-onnx/releases) (e.g. `model-files-v1.0`):

- `kokoro-v1.0.onnx`
- `voices-v1.0.bin`

Place them under `generator/models/` **or** set env vars:

- `KOKORO_MODEL_PATH`
- `KOKORO_VOICES_BIN_PATH`

Without these files the API still **starts**; synthesis returns **503** until models are present (or use `KOKORO_AUTO_DOWNLOAD=1` with a writable `generator/models` directory — see [`doc/deployment.md`](doc/deployment.md)).

### 3. Run the API

```bash
cd generator
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Interactive docs: <http://127.0.0.1:8000/docs>

### Example requests

**Generate speech:**

```bash
curl -sS -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Bonjour le monde.","language":"fr-fr","voice_id":"af_sarah","speed":1.0}' \
  -o speech.wav
```

**List available voices:**

```bash
curl -sS http://127.0.0.1:8000/voices
```

JSON body fields for `/generate`: `text`, `language`, `voice_id`, `speed` (optional, default 1.0). See Kokoro [VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) for available voices and languages.

## Voice preparation

Kokoro uses **precomputed style vectors** (not raw audio) to define a voice. The official bundle (`voices-v1.0.bin`) ships ~50 voices; you can add your own by downloading `.pt` packs from [HuggingFace](https://huggingface.co/hexgrad/Kokoro-82M/tree/main/voices) and bundling them with the scripts in `voice_prep_module/`.

**Full step-by-step guide:** [`doc/voice-preparation.md`](doc/voice-preparation.md) — covers concepts, prerequisites, the complete workflow, script reference and FAQ.

Quick summary:

```bash
# 1. Install prep dependencies
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

## Web UI

The Nuxt 4 UI lives in `ui/` and provides a browser interface for TTS generation.

### Local development

```bash
cd ui
nix shell nixpkgs#nodejs_22 --command bash
npm install
npm run dev
```

The UI runs on <http://localhost:3000> and proxies API calls to the FastAPI backend at `API_BASE_URL` (default `http://localhost:8000`).

### Environment variables (UI)

| Variable | Purpose |
|----------|---------|
| `NUXT_SESSION_PASSWORD` | Encryption key for session cookies (min 32 chars; auto-generated in dev) |
| `API_BASE_URL` | FastAPI backend URL (default `http://localhost:8000`) |
| `API_TOKEN` | Optional Bearer token for FastAPI authentication |
| `ADMIN_USER` | Login username (default `admin`) |
| `ADMIN_PASSWORD` | Login password |

## Docker

Copy `.env.example` to `.env` and set at minimum `NUXT_SESSION_PASSWORD` and `ADMIN_PASSWORD`.

Place `kokoro-v1.0.onnx` and `voices-v1.0.bin` under **`generator/models/`** on the host (not baked into the image). Optional voice bundles go under **`generator/voices/`**.

### Local (without Traefik)

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

- UI: <http://localhost:3000>
- API health: `GET http://localhost:8000/health`
- API docs: <http://localhost:8000/docs>

Host ports are configurable via `API_PORT` and `UI_PORT` in `.env` (defaults: 8000 / 3000). The local override disables Traefik labels and sets `ROOT_PATH` to empty (no public path prefix on the API port).

### Coolify / single-domain deployment

The main `docker-compose.yml` ships with **Traefik labels** for single-domain routing: the UI is served at the root (`/`) and the TTS API under `/tts-server`. Assign one domain in the Coolify UI (e.g. `https://tts.example.com`); Traefik handles path-based routing automatically. See [`doc/deployment.md`](doc/deployment.md) for details on Open WebUI / Home Assistant URLs behind the proxy.

To use a merged voices file, uncomment `KOKORO_VOICES_BIN_PATH` in `docker-compose.yml`. To secure the API with a Bearer token, set `API_TOKEN` in `.env`.

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
