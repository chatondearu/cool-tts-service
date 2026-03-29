# AGENTS — repository guide for humans and coding agents

## Where to look first

1. **Root [`README.md`](README.md)** — goals, layout, quick start, API example.
2. **This file** — paths, env vars, and workflow expectations.
3. **[`doc/deployment.md`](doc/deployment.md)** — Nix shell quirks, `LD_LIBRARY_PATH`, production vs local.
4. **[`.cursor/rules/`](.cursor/rules/)** — project rules (Nix discovery, Conventional Commits, etc.).

Do **not** assume historical layouts (e.g. `app/requirements.txt`). **Infer** dependency and source paths from the tree or these docs.

## Project shape

| Area | Role |
|------|------|
| [`production_api/main.py`](production_api/main.py) | FastAPI app, lifespan, `POST /generate` |
| [`production_api/tts_engine.py`](production_api/tts_engine.py) | `KokoroTTS` — keep thin for engine swap later |
| [`production_api/requirements_api.txt`](production_api/requirements_api.txt) | API + inference dependencies |
| [`production_api/models/`](production_api/models/) | `kokoro-v1.0.onnx`, `voices-v1.0.bin` (local; large files ignored by git) |
| [`voice_prep_module/`](voice_prep_module/) | Offline prep — `extract_voice.py`, `requirements_prep.txt`, `raw_audios/` |
| [`production_api/voices/`](production_api/voices/) | `voice_prep_manifest.json`, optional `custom_voices.bin` (npz; gitignored) |
| [`flake.nix`](flake.nix) / [`flake.lock`](flake.lock) | Dev shell (Python 3.11, `uv`, audio libs) |

## Environment variables

| Variable | Purpose |
|----------|---------|
| `KOKORO_MODEL_PATH` | Override path to Kokoro `.onnx` |
| `KOKORO_VOICES_BIN_PATH` | Override path to `voices-*.bin` |
| `UV_PYTHON` | Set by Nix shell so `uv` uses the Nix interpreter (optional elsewhere) |

## Commands (typical)

From repo root after `nix develop` and `uv venv`:

```bash
uv pip install --python .venv/bin/python -r production_api/requirements_api.txt
source .venv/bin/activate
cd production_api && uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

(`UV_PYTHON` is set in the Nix shell; without `--python .venv/bin/python`, `uv pip` may try to write into the read-only Nix interpreter.)

**Voice prep** (torch + numpy; separate from API venv if you prefer):

```bash
uv pip install --python .venv/bin/python -r voice_prep_module/requirements_prep.txt
python voice_prep_module/extract_voice.py
```

Kokoro ONNX does **not** build new style vectors from raw `.wav` here; the script packs Hugging Face–style `*.pt` clips and inventories WAV metadata. Set `KOKORO_VOICES_BIN_PATH` to `production_api/voices/custom_voices.bin` when using a custom bundle.

After changing flake **inputs**, run `nix flake lock` and commit **`flake.lock`** with **`flake.nix`**.

## Commits

Follow **Conventional Commits** (see [`.cursor/rules/conventional-commits.mdc`](.cursor/rules/conventional-commits.mdc)): English, imperative subject, optional scope (`api`, `nix`, `tts`, …).

## Editing Nix

See [`.cursor/rules/nix-development.mdc`](.cursor/rules/nix-development.mdc): prefer README / AGENTS / scanned layout over copy-pasting patterns from other repos.

## Out of scope unless requested

- Do not add Docker artifacts until Phase 4 is explicitly requested (Dockerfile / compose).
- Do not commit large `.onnx` / `.bin` assets; `.gitignore` covers `production_api/models/` and `production_api/voices/*.bin`.
