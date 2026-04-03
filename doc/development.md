# Local development and smoke tests

This guide covers **two ways** to work on the repo on your machine: **with the Nix flake** (recommended for NixOS/Linux wheel compatibility) or **without Nix** (plain Python + Node). For Docker and production, see [`deployment.md`](deployment.md).

## Choose your toolchain

| Piece | With Nix (`nix develop`) | Without Nix |
| ----- | ------------------------ | ----------- |
| **Nix / flake** | Yes — enter dev shell from repo root | Not used |
| **Python** | 3.11 from Nix (`python311` in flake) | **3.10+** from the OS, pyenv, or another manager |
| **Package installer** | **`uv`** into a project `.venv` (recommended) | **`uv`** or `python -m venv` + `pip` |
| **Node (UI)** | **Node.js 22** + **npm** included in the flake | **Node.js 22** + npm (e.g. [nodejs.org](https://nodejs.org/), `nvm`, `fnm`, distro packages) |

Application code targets **Python 3.10+**; the flake pins **3.11** for reproducibility.

---

## Option 1 — With Nix

From the repository root:

```bash
nix develop
```

Or with **direnv** (after `direnv allow` once), the shell loads automatically when you `cd` into the repo (see [`.envrc`](../.envrc)).

Create the API virtualenv and install dependencies:

```bash
uv venv --python "${UV_PYTHON:-python3}" .venv
source .venv/bin/activate
uv pip install --python .venv/bin/python -r generator/requirements_api.txt
```

The flake sets `UV_PYTHON` to the Nix `python3` so `uv` does not pick a random host interpreter.

### NixOS / Linux: native PyPI wheels

On **NixOS** (and some Linux setups), wheels such as `onnxruntime` and `soundfile` need libraries on `LD_LIBRARY_PATH`. The flake **shellHook** prepends the right paths when you use `nix develop`.

If `nix develop` fails with **`CXXABI_1.3.15`** before the shell starts, clear a bad inherited `LD_LIBRARY_PATH` once: `env -u LD_LIBRARY_PATH nix develop`, or run `direnv reload` after updating the flake. More context: **LD_LIBRARY_PATH** subsection in [`deployment.md`](deployment.md).

### Run the API

```bash
cd generator
uvicorn main:app --reload --host 0.0.0.0 --port 9000
```

### Run the UI

Node 22 and npm are already on `PATH`:

```bash
cd ui
cp .env.example .env   # once: set NUXT_SESSION_PASSWORD (≥32 chars), ADMIN_PASSWORD, optional API_BASE_URL / API_TOKEN
npm install
npm run dev
```

Open <http://localhost:3000>.

---

## Option 2 — Without Nix

Install **Python 3.10+** and **Node.js 22** (with npm) yourself, then from the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U uv
uv pip install -r generator/requirements_api.txt
```

(You can use `pip install -r generator/requirements_api.txt` instead of `uv pip` if you prefer.)

Run the API:

```bash
cd generator
uvicorn main:app --reload --host 0.0.0.0 --port 9000
```

Run the UI:

```bash
cd ui
cp .env.example .env
npm install
npm run dev
```

If you use **Nix only for Node**, a one-off shell is enough: `nix shell nixpkgs#nodejs_22`, then the same `npm` commands.

---

## API + UI together (one terminal)

From the **repository root**, after installing API deps into `.venv` and running `npm install` in `ui/`:

```bash
./scripts/dev-local.sh
```

This starts **uvicorn** in the background (`generator/`, default port **9000**) and **Nuxt** in the foreground (`ui/`, default port **3000**). **Ctrl+C** stops the UI and the script tears down the API process.

Custom ports:

```bash
API_PORT=9000 UI_PORT=3001 ./scripts/dev-local.sh
```

If you change `API_PORT`, set **`NUXT_API_BASE_URL`** in `ui/.env` to the same host/port (e.g. `http://127.0.0.1:9000`).

On **Windows**, use **WSL** or run the API and UI in two terminals; the script targets Bash on Linux/macOS.

---

## Shared: Kokoro model files

Download assets from the [kokoro-onnx release `model-files-v1.0`](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0), e.g.:

- `kokoro-v1.0.onnx`
- `voices-v1.0.bin`

Place them under **`generator/models/`**, or set **`KOKORO_MODEL_PATH`** and **`KOKORO_VOICES_BIN_PATH`**.

Without these files the API **still starts**; synthesis returns **503** until models are loaded. Optional: **`KOKORO_AUTO_DOWNLOAD=1`** with a writable `generator/models` directory (see [`deployment.md`](deployment.md)).

---

## UI environment (`ui/.env`)

Copy `ui/.env.example` → `ui/.env` and set at least:

| Variable | Purpose |
| -------- | ------- |
| `NUXT_SESSION_PASSWORD` | Session cookie encryption (min 32 characters) |
| `ADMIN_PASSWORD` | Login password for the UI |

Optional: `NUXT_API_BASE_URL` (default `http://localhost:9000` in `ui/.env.example`), `NUXT_API_TOKEN` if the API uses Bearer auth, `NUXT_ADMIN_USER` (default `admin`).

---

## Smoke tests and quick checks

These help verify the toolchain and HTTP surface **without** requiring a full synthesis run (optional).

### 1. Import the FastAPI app (no inference)

With the venv activated and API deps installed:

```bash
cd generator && python -c "from main import app; print(app.title)"
```

### 2. Health endpoint (API running)

```bash
curl -sS http://127.0.0.1:9000/health
```

Expect JSON with `status` and `tts_ready` (and `tts_error` if models are missing).

### 3. List voices

```bash
curl -sS http://127.0.0.1:9000/voices
```

If `API_TOKEN` is set, add `-H "Authorization: Bearer <token>"`.

### 4. Synthesis (needs loaded models and a valid `voice_id`)

```bash
curl -sS -X POST http://127.0.0.1:9000/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello","language":"en-us","voice_id":"af_sarah","speed":1.0}' \
  -o /tmp/speech.wav
```

Use `GET /voices` (or the UI) to pick a valid `voice_id`.

### Automated test suite

There is **no** bundled `pytest` suite yet; the checks above are the supported manual smoke path. If you add tests, document the command here (e.g. `pytest`).

---

## Optional: voice-prep dependencies

Offline voice bundling uses a separate stack:

```bash
uv pip install --python .venv/bin/python -r voice_prep_module/requirements_prep.txt
```

Workflow: [`voice-preparation.md`](voice-preparation.md).

---

## See also

- [`deployment.md`](deployment.md) — Docker, Coolify, Traefik, API tables, production env
- Root [`README.md`](../README.md) — overview, layout, Docker quick start
