# Configuration

## Environment variables

### Read by the application

| Variable | Default | Where | Purpose |
|----------|---------|-------|---------|
| `VOICES_DIR` | `/app/voices` | `app/main.py` | Root directory for voice assets. `GET /voices` lists `{VOICES_DIR}/default/*.wav`. |
| `MODEL_NAME` | `mistralai/Voxtral-Mini-3B-TTS-2603` | `app/model.py` | Hugging Face model id passed to `OmniModel.from_pretrained`. |
| `CACHE_DIR` | _(unset)_ | `app/model.py` | When set, directory is created if needed and `HF_HOME` is defaulted to this path so hub/model caches use the mounted volume (e.g. `/app/cache` in Compose). |
| `LOG_LEVEL` | `INFO` | `app/main.py` | Log level for stdlib `logging` and loguru (`DEBUG`, `INFO`, `WARNING`, `ERROR`, …). Invalid values fall back to `INFO`. |

Always re-check `grep` / settings modules when syncing this table with the repo.

---

## Voices layout

- **Default voices**: place `*.wav` files under `{VOICES_DIR}/default/`. Each file stem becomes a voice id (e.g. `fr_female_1.wav` → `fr_female_1`).
- **Custom voices**: project convention is to use `app/voices/custom/` on the host (documented in the root README). The HTTP layer passes `voice` through to the model; ensure samples and model expectations stay aligned.

---

## Application constants (code)

- Default voice if omitted in JSON: **`fr_female_1`** (`app/main.py`).
