# cool-tts-service

Open-source **Text-to-Speech HTTP API** aimed at **fast CPU inference**, with a **modular** design so the engine can later be swapped for a heavier GPU-backed model.

## Stack

- **TTS:** [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (ONNX Runtime, lightweight on CPU)
- **API:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **Python:** 3.10+ (recommended: match the Nix dev shell — **3.11**)
- **Containers:** Docker + Compose ([`production_api/Dockerfile`](production_api/Dockerfile), [`docker-compose.yml`](docker-compose.yml))

## Layout

```text
cool-tts-service/
├── production_api/            # HTTP API + Kokoro engine wrapper
│   ├── main.py                # FastAPI app (POST /generate, GET /voices, GET /health)
│   ├── tts_engine.py          # KokoroTTS thin wrapper
│   ├── requirements_api.txt
│   ├── Dockerfile
│   ├── models/                # kokoro-v1.0.onnx, voices-v1.0.bin (not in git)
│   └── voices/                # Custom voice bundles (not in git)
├── voice_prep_module/         # Offline voice preparation
│   ├── extract_voice.py       # Index WAVs + pack .pt files into npz bundle
│   ├── extract_voice_from_wav.py  # [Experimental] WAV -> placeholder embedding
│   ├── merge_voice_bundles.py # Merge official + custom npz bundles
│   ├── requirements_prep.txt
│   └── raw_audios/            # Reference WAV clips
├── doc/
│   └── deployment.md          # Nix + Docker + production notes
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
uv pip install --python .venv/bin/python -r production_api/requirements_api.txt
source .venv/bin/activate
```

Without Nix, use Python **3.10+** and install the same `requirements_api.txt` into a virtualenv.

### 2. Model files

Download from [kokoro-onnx releases](https://github.com/thewh1teagle/kokoro-onnx/releases) (e.g. `model-files-v1.0`):

- `kokoro-v1.0.onnx`
- `voices-v1.0.bin`

Place them under `production_api/models/` **or** set env vars:

- `KOKORO_MODEL_PATH`
- `KOKORO_VOICES_BIN_PATH`

### 3. Run the API

```bash
cd production_api
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

Kokoro's ONNX runtime consumes **precomputed style packs** (the official release uses `voices-v1.0.bin`; upstream also distributes per-voice **`*.pt`** files on Hugging Face). **Arbitrary `.wav` files alone are not converted** into real Kokoro style vectors — keep WAVs as reference recordings and add matching `.pt` sources when you have them.

### Pack .pt files into a custom bundle

```bash
uv pip install --python .venv/bin/python -r voice_prep_module/requirements_prep.txt
python voice_prep_module/extract_voice.py \
  --input-dir voice_prep_module/raw_audios \
  --output-dir production_api/voices
```

- With **only `.wav`**: writes a manifest with metadata and instructions.
- With **`.pt` files** in the input dir: writes `production_api/voices/custom_voices.bin` (npz bundle) plus the manifest.

### Merge official + custom bundles

Combine `voices-v1.0.bin` with `custom_voices.bin`. Overlay keys **replace** same-named keys in the base file.

```bash
python voice_prep_module/merge_voice_bundles.py \
  --base production_api/models/voices-v1.0.bin \
  --overlay production_api/voices/custom_voices.bin \
  --output production_api/voices/merged_voices.bin
```

Then set `KOKORO_VOICES_BIN_PATH` to point at `merged_voices.bin`.

### Experimental: WAV -> placeholder embedding

> **Warning:** this script produces **random** embeddings — the output will NOT sound like the input audio. It exists as a scaffold for when a real encoder becomes available.

```bash
python voice_prep_module/extract_voice_from_wav.py --wav voice_prep_module/raw_audios/nemo_0_FR.wav
```

## Docker

Place `kokoro-v1.0.onnx` and `voices-v1.0.bin` under **`production_api/models/`** on the host (not baked into the image). Optional voice bundles go under **`production_api/voices/`**.

```bash
docker compose build
docker compose up
```

- Health: `GET http://127.0.0.1:8000/health`
- API docs: <http://127.0.0.1:8000/docs>

To use a merged voices file, uncomment `KOKORO_VOICES_BIN_PATH` in `docker-compose.yml`.

## Contributing / agents

For automation and repository conventions, see [`AGENTS.md`](AGENTS.md).

## License

Specify in this file once you choose a license for the service code (Kokoro / kokoro-onnx have their own licenses — check upstream notices).
