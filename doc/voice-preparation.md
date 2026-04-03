# Voice preparation guide

This guide explains how to select, prepare and deploy custom voices for the cool-tts-service API powered by [Kokoro](https://github.com/thewh1teagle/kokoro-onnx). No prior knowledge of Kokoro or Python is assumed.

## How Kokoro voices work

Kokoro does **not** synthesize speech from raw audio recordings at runtime. Instead it relies on **precomputed style vectors** — small numeric fingerprints (~2 KB each) that encode speaking style, pitch and timbre. At inference time the TTS model reads one of these vectors and generates speech that matches its characteristics.

### Key file types

| File | What it is | Where it comes from |
|------|-----------|---------------------|
| `.pt` | Single voice style vector (PyTorch pickle) | Downloaded from [HuggingFace](https://huggingface.co/hexgrad/Kokoro-82M/tree/main/voices) |
| `.bin` / `.npz` | Bundle of multiple voice vectors packed together | Produced by the scripts in `voice_prep_module/`, or the official `voices-v1.0.bin` |
| `.wav` / `.mp3` | Raw audio recording | Your own recordings — used as **reference** only; not consumed directly by Kokoro |
| `.onnx` | The TTS neural-network model | Downloaded from [kokoro-onnx releases](https://github.com/thewh1teagle/kokoro-onnx/releases) |

### Data flow overview

```text
  HuggingFace .pt files ─┐
                          ├──▶ extract_voice.py ──▶ custom_voices.bin ─┐
  .wav reference clips ───┘          (packs .pt,                       │
                                      inventories .wav)                │
                                                                       ▼
  voices-v1.0.bin (official) ──────▶ merge_voice_bundles.py ──▶ merged_voices.bin
                                                                       │
                                                                       ▼
                                                              Production API
                                                        (KOKORO_VOICES_BIN_PATH)
```

## Prerequisites

### Python

Python **3.10+** is required (3.11 recommended). If you use Nix:

```bash
nix develop          # enters the dev shell with Python 3.11
```

Without Nix, any system Python 3.10+ works.

### Virtual environment and dependencies

```bash
# Create a venv (skip if you already have one)
uv venv --python "${UV_PYTHON:-python3}" .venv
source .venv/bin/activate

# Install voice-prep dependencies (torch, numpy, soundfile)
uv pip install --python .venv/bin/python -r voice_prep_module/requirements_prep.txt
```

> Without `uv`, replace the install command with:
> `pip install -r voice_prep_module/requirements_prep.txt`

### Model files

If you have not done so already, download the model assets from [kokoro-onnx releases](https://github.com/thewh1teagle/kokoro-onnx/releases) (`model-files-v1.0`):

- `kokoro-v1.0.onnx` — the TTS model
- `voices-v1.0.bin` — the official voice bundle (~50 voices)

Place both under `generator/models/`.

## Finding and choosing voices

### Official voice catalogue

Kokoro ships with ~50 pre-trained voices. Browse them at:

<https://huggingface.co/hexgrad/Kokoro-82M/tree/main/voices>

Each `.pt` file is one voice. The filename follows a naming convention:

| Prefix | Meaning | Example |
|--------|---------|---------|
| `af_` | American English, Female | `af_sarah.pt` |
| `am_` | American English, Male | `am_adam.pt` |
| `bf_` | British English, Female | `bf_emma.pt` |
| `bm_` | British English, Male | `bm_george.pt` |
| `ff_` | French, Female | `ff_siwis.pt` |
| `fm_` | French, Male | — |

> Not all combinations exist. Check the HuggingFace listing for the full up-to-date catalogue.

### Supported languages

When calling the API (`POST /generate`), pass one of these language codes:

| Code | Language |
|------|----------|
| `en-us` | American English |
| `en-gb` | British English |
| `fr-fr` | French |
| `ja` | Japanese |
| `ko` | Korean |
| `zh` | Chinese (Mandarin) |

See upstream [VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) for the authoritative voice / language compatibility matrix.

## Step-by-step workflow

### Step 1 — Download the `.pt` files you want

Pick one or more voices from HuggingFace and download the `.pt` files into `voice_prep_module/raw_audios/`:

```bash
# Example: download the French female voice "ff_siwis"
curl -L -o voice_prep_module/raw_audios/ff_siwis.pt \
  "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/voices/ff_siwis.pt"
```

You can also place `.wav` reference clips alongside them — they will not be packed into the bundle but their metadata (duration, sample rate, etc.) will be recorded in the manifest for your records.

### Step 2 — Pack into a custom voice bundle

Run `extract_voice.py` to convert the `.pt` files into a single `.bin` bundle:

```bash
python voice_prep_module/extract_voice.py \
  --input-dir voice_prep_module/raw_audios \
  --output-dir generator/voices
```

This produces:

| Output | Description |
|--------|-------------|
| `generator/voices/custom_voices.bin` | NPZ archive containing all `.pt` voices found in the input directory |
| `generator/voices/voice_prep_manifest.json` | JSON manifest listing packed voices and WAV metadata |

If **no `.pt` files** are found, the script writes only the manifest with instructions explaining what to download.

#### Optional arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--input-dir` | `voice_prep_module/raw_audios` | Directory to scan for `.pt` and `.wav` files |
| `--output-dir` | `generator/voices` | Where to write the bundle and manifest |
| `--output-bundle` | *(auto)* | Full path for the output `.bin`; overrides `--bundle-name` |
| `--bundle-name` | `custom_voices.bin` | Filename when `--output-bundle` is not set |

### Step 3 — Merge with the official voice bundle

The custom bundle only contains the voices you added. To keep **all** official voices **and** your custom ones, merge them:

```bash
python voice_prep_module/merge_voice_bundles.py \
  --base generator/models/voices-v1.0.bin \
  --overlay generator/voices/custom_voices.bin \
  --output generator/voices/merged_voices.bin
```

If a voice key exists in both bundles, the **overlay** version wins (useful for replacing an official voice with your own variant).

The script also writes a `merged_voices.bin.merge-meta.json` file with merge details (voice count, overridden keys, full key list).

### Step 4 — Point the API at the merged bundle

Set the environment variable so the API loads your merged file instead of the default:

```bash
# Local dev
export KOKORO_VOICES_BIN_PATH=generator/voices/merged_voices.bin
cd generator && uvicorn main:app --reload --host 0.0.0.0 --port 9000
```

For **Docker**, uncomment the line in `docker-compose.yml`:

```yaml
environment:
  KOKORO_VOICES_BIN_PATH: /app/voices/merged_voices.bin
```

Then rebuild / restart:

```bash
docker compose up -d
```

### Step 5 — Verify

List available voices to confirm your new entries appear:

```bash
curl -sS http://127.0.0.1:9000/voices | python -m json.tool
```

Generate a test clip:

```bash
curl -sS -X POST http://127.0.0.1:9000/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Bonjour, ceci est un test.","language":"fr-fr","voice_id":"ff_siwis","speed":1.0}' \
  -o test_output.wav
```

Play `test_output.wav` with any audio player to check the result.

## Script reference

### `extract_voice.py`

Packs `.pt` style vectors into a single NPZ bundle and inventories `.wav` clips.

```text
python voice_prep_module/extract_voice.py [OPTIONS]

  --input-dir PATH       Source directory with .pt / .wav files
  --output-dir PATH      Destination for bundle + manifest
  --output-bundle PATH   Explicit bundle path (overrides --bundle-name)
  --bundle-name NAME     Bundle filename (default: custom_voices.bin)
```

**Inputs:** `.pt` files (required for bundle), `.wav` files (optional, metadata only).
**Outputs:** `custom_voices.bin` (NPZ), `voice_prep_manifest.json`.

### `merge_voice_bundles.py`

Merges two NPZ voice bundles. Overlay keys replace same-named base keys.

```text
python voice_prep_module/merge_voice_bundles.py --base BASE --overlay OVERLAY --output OUT

  --base PATH      Primary bundle (e.g. official voices-v1.0.bin)
  --overlay PATH   Second bundle; its keys override same-named base keys
  --output PATH    Merged output path
```

**Outputs:** merged `.bin` (NPZ), `<name>.merge-meta.json` with merge statistics.

### `extract_voice_from_wav.py`

> **Warning:** this script is **experimental**. It produces **random** 512-D embeddings that will NOT sound like the input audio. It exists as a scaffold for when a real upstream encoder becomes available (see [Roadmap](../README.md#roadmap--todo)).

```text
python voice_prep_module/extract_voice_from_wav.py [OPTIONS]

  --wav PATH         Input audio file (default: raw_audios/nemo_0_FR.wav)
  --output PATH      Output bundle path (default: generator/voices/custom_from_wav.bin)
  --voice-key NAME   Key inside the NPZ (default: normalized WAV filename stem)
```

## Frequently asked questions

### I only have WAV/MP3 files, not `.pt` — can I use them?

Not directly. Kokoro requires **precomputed style vectors** (`.pt` files). Raw audio recordings cannot be converted into real style vectors yet — upstream tooling for this is [on the roadmap](../README.md#roadmap--todo).

For now, use the WAV files as **reference recordings** and pick the closest official `.pt` voice from the [HuggingFace catalogue](https://huggingface.co/hexgrad/Kokoro-82M/tree/main/voices).

### My new voice does not appear in `GET /voices`

Check the following:

1. **Was the bundle generated?** Look for `generator/voices/custom_voices.bin` (or your merged file). If missing, re-run `extract_voice.py`.
2. **Is `KOKORO_VOICES_BIN_PATH` set?** The API loads `generator/models/voices-v1.0.bin` by default. Override it to point at your merged bundle.
3. **Did you restart the API?** The voice bundle is loaded once at startup. Restart `uvicorn` or the Docker container after changing the bundle.

### What is inside a `.bin` / `.npz` bundle?

It is a standard NumPy NPZ archive. Each key is a voice id (e.g. `af_sarah`) and the value is a float32 array (the style vector). You can inspect it with Python:

```python
import numpy as np

data = np.load("generator/voices/merged_voices.bin")
print("Voices:", sorted(data.files))
print("Shape of first voice:", data[data.files[0]].shape)
```

### Can I rename a voice?

Yes. The voice id used by the API is the **key** inside the NPZ bundle, which comes from the `.pt` filename stem. Rename the `.pt` file before running `extract_voice.py` and the new name will be used as the voice id.

### How many voices can I bundle?

There is no hard limit. Each voice is ~2 KB, so even hundreds of voices add negligible size to the bundle. The official `voices-v1.0.bin` contains ~50 voices and weighs about 100 KB.
