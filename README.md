# cool-tts-service

Open-source **Text-to-Speech HTTP API** aimed at **fast CPU inference**, with a **modular** design so the engine can later be swapped for a heavier GPU-backed model.

## Stack

- **TTS:** [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (ONNX Runtime, lightweight on CPU)
- **API:** [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **Python:** 3.10+ (recommended: match the Nix dev shell — **3.11**)
- **Containers:** Docker / Compose (**planned** — Phase 4)

## Layout

```text
cool-tts-service/
├── voice_prep_module/     # Offline voice prep (Phase 3)
│   ├── extract_voice.py
│   ├── requirements_prep.txt
│   └── raw_audios/
├── production_api/       # HTTP API + Kokoro engine wrapper
│   ├── main.py
│   ├── tts_engine.py
│   ├── requirements_api.txt
│   ├── models/           # kokoro-v1.0.onnx, voices-v1.0.bin (not in git)
│   └── voices/           # Custom voice artifacts (Phase 3+)
├── doc/
│   └── deployment.md     # Nix + production notes
├── flake.nix / flake.lock / .envrc
└── README.md
```

## Quick start (local)

### 1. Toolchain

Use **Nix** + **uv** (see [`doc/deployment.md`](doc/deployment.md) for details):

```bash
nix develop
uv venv --python "${UV_PYTHON:-python3}" .venv
# With this flake, UV_PYTHON points at Nix python — target the venv explicitly:
uv pip install --python .venv/bin/python -r production_api/requirements_api.txt
source .venv/bin/activate
```

Without Nix, use Python **3.10+** and install the same `requirements_api.txt` into a virtualenv.

### 2. Model files

Download from [kokoro-onnx model releases](https://github.com/thewh1teagle/kokoro-onnx/releases) (e.g. `model-files-v1.0`):

- `kokoro-v1.0.onnx`
- `voices-v1.0.bin`

Place them under `production_api/models/` **or** set:

- `KOKORO_MODEL_PATH`
- `KOKORO_VOICES_BIN_PATH`

### 3. Run the API

```bash
cd production_api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Interactive docs: `http://127.0.0.1:8000/docs`

### Example request

```bash
curl -sS -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello.","language":"en-us","voice_id":"af_sarah"}' \
  -o speech.wav
```

JSON body fields: `text`, `language`, `voice_id` (see Kokoro voices / languages, e.g. [VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)).

## Voice preparation (Phase 3)

Kokoro’s ONNX runtime consumes **precomputed style packs** (the official release uses a single `voices-v1.0.bin`; upstream also distributes per-voice **`*.pt`** files on Hugging Face). **Arbitrary `.wav` files alone are not converted** into Kokoro style vectors in this pipeline — keep WAVs as reference recordings and add matching `.pt` sources when you have them.

From the repo root:

```bash
nix develop  # optional
uv pip install --python .venv/bin/python -r voice_prep_module/requirements_prep.txt
python voice_prep_module/extract_voice.py \
  --input-dir voice_prep_module/raw_audios \
  --output-dir production_api/voices
```

- With **only `.wav`**: writes `production_api/voices/voice_prep_manifest.json` (metadata + instructions).
- With **one or more `.pt`** in `raw_audios/`: writes `production_api/voices/custom_voices.bin` (npz bundle) plus the manifest.

Point the API at your bundle:

```bash
export KOKORO_VOICES_BIN_PATH="$PWD/production_api/voices/custom_voices.bin"
```

Use `voice_id` values that match the **stem** of each `.pt` (e.g. `af_sarah` for `af_sarah.pt`). To keep **all** official voices **and** custom names, merge official `.pt` files together in one folder before running the script (large download).

## Roadmap (brief)

| Phase | Status | Content |
|-------|--------|---------|
| 1 | Done | Layout, `tts_engine.py`, `requirements_api.txt` |
| 2 | Done | FastAPI `main.py`, lifespan, `POST /generate` → WAV |
| 3 | In progress | `extract_voice.py`: WAV inventory + pack `*.pt` → `custom_voices.bin` / manifest |
| 4 | Planned | `production_api/Dockerfile`, root `docker-compose.yml` |

## Contributing / agents

For automation and repository conventions, see [`AGENTS.md`](AGENTS.md).

## License

Specify in this file once you choose a license for the service code (Kokoro / kokoro-onnx have their own licenses — check upstream notices).
