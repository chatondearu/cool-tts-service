# Configuration

## Environment variables

### Read by the application

| Variable | Default | Where | Purpose |
|----------|---------|-------|---------|
| `VOICES_DIR` | `/app/voices` | `app/main.py` | Root directory for voice assets. `GET /voices` lists `{VOICES_DIR}/default/*.wav`. |
| `MODEL_NAME` | `mistralai/Voxtral-4B-TTS-2603` | `app/model.py` | Hugging Face model id passed to `Omni(model=...)`. |
| `HF_TOKEN` / `HUGGING_FACE_HUB_TOKEN` | _(unset)_ | Hugging Face Hub (tokenizer + weights) | Read token when the Hub requires it (**gated** or private repos). Omit for fully public weights. Must not be set to a blank string (causes **401**). When set, the two names are mirrored if only one is set. |
| `CACHE_DIR` | _(unset)_ | `app/model.py` | When set, directory is created if needed and `HF_HOME` is defaulted to this path so hub/model caches use the mounted volume (e.g. `/app/cache` in Compose). |
| `LOG_LEVEL` | `INFO` | `app/main.py` | Log level for stdlib `logging` and loguru (`DEBUG`, `INFO`, `WARNING`, `ERROR`, …). Invalid values fall back to `INFO`. |

### Docker entrypoint (`app/ensure_model.py`)

The container **entrypoint** runs **`ensure_model.py`** before **`uvicorn`**. It reads **`MODEL_NAME`**, **`CACHE_DIR`**, **`HF_TOKEN`** / **`HUGGING_FACE_HUB_TOKEN`** the same way as the app (see `app/model.py` for token blank-stripping). If the Hub download or local snapshot validation fails, the script exits non-zero and the container does not keep serving HTTP.

Always re-check `grep` / settings modules when syncing this table with the repo.

---

## Voices layout

- **Default voices**: place `*.wav` files under `{VOICES_DIR}/default/`. Each file stem becomes a voice id (e.g. `generate_0_FR.wav` → `generate_0_FR`).
- **Custom voices**: project convention is to use `app/voices/custom/` on the host (documented in the root README). The HTTP layer passes `voice` through to the model; ensure samples and model expectations stay aligned.

---

## Application constants (code)

- Default voice if omitted in JSON: **`generate_0_FR`** (`app/main.py`).
