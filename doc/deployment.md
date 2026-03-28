# Deployment

## Requirements

- **Docker** and **Docker Compose** for the supported path below.
- Compose file sets a **4G** memory limit and **2** CPUs max for `cool-tts-service` (see `docker-compose.yml`). Adjust if your model or host differs.

## Docker Compose (recommended)

From the repository root:

```bash
docker compose up -d --build
```

Or with legacy CLI:

```bash
docker-compose up -d --build
```

### Ports

- Host `8000` → container `8000` (FastAPI / uvicorn).

### Volumes

| Host path | Container path | Purpose |
|-----------|----------------|---------|
| `./app/voices` | `/app/voices` | Voice samples |
| `./app/cache` | `/app/cache` | Model / cache data |

### Health check

Compose and the `Dockerfile` use:

```yaml
test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
```

The image installs **`curl`** for this probe.

### Logs

```bash
docker compose logs -f cool-tts-service
```

---

## Image build (`Dockerfile`)

- Base: `python:3.11-slim`
- System packages: `curl`, `git`, `ffmpeg`, `libsndfile1`
- Python deps from `app/requirements.txt`
- App copied to `/app`; uvicorn command:

```text
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Working directory in container is `/app` with `main.py` at that level.

---

## Local development (without Docker)

### Option A: Nix dev shell (recommended for host isolation)

The repo provides a **flake** (`flake.nix`) that matches the container’s baseline: **Python 3.11**, **curl**, **git**, **ffmpeg**, **libsndfile** (via `pkgs.libsndfile`), **uv** (fast installer for PyPI), and common build helpers so Python packages can be installed into a project-local `.venv` without relying on system-wide tools outside Nix.

`python311Packages.pip` is intentionally **not** pulled from Nixpkgs here: on some Nixpkgs revisions it fails to evaluate for Python 3.11 (transitive doc-tooling constraints). Use **`uv pip install`** inside the dev shell instead, which still reads `app/requirements.txt` like Docker’s `pip`.

**Requirements:** [Nix](https://nixos.org/) with flakes enabled (`experimental-features = nix-command flakes`).

From the repository root:

```bash
nix develop
```

With **[direnv](https://direnv.net/)**, the repo includes a root `.envrc` that runs `use flake`. After `direnv allow` once in this directory, your shell loads the same environment automatically when you `cd` here.

Inside the shell, optional environment defaults (override if needed):

- `VOICES_DIR` → `<repo>/app/voices` when unset  
- `CACHE_DIR` → `<repo>/app/cache` when unset  

Create a **project-local virtualenv** (ignored by git as `.venv/`) and install PyPI dependencies there — **`vllm-omni` and its stack (e.g. PyTorch) are not packaged in this flake**; they are installed from `app/requirements.txt`, same versions as in Docker:

```bash
uv venv --python python3 .venv
source .venv/bin/activate
uv pip install -r app/requirements.txt
```

Run the API from the repo root:

```bash
uvicorn app.main:app --reload --app-dir .
```

**Notes:**

- First `pip install` can be large (model-related wheels). Use the same Python version as the flake (**3.11**) so wheels align with the Docker image.
- On **aarch64-linux** (e.g. Raspberry Pi), some PyPI wheels may be missing or differ; prefer Docker on device if installs fail.
- Commit **`flake.lock`** with the flake so `nix develop` stays reproducible for the Nixpkgs pin.

---

### Option B: Plain virtualenv / system Python

Install dependencies:

```bash
pip install -r app/requirements.txt
```

Run with module path pointing at the package layout you use. If running from repo root with `app` as a package directory:

```bash
uvicorn app.main:app --reload --app-dir .
```

Verify `VOICES_DIR` and paths match your machine if you deviate from `/app/voices`.
