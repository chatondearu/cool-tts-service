# Deployment

## Requirements

- **Docker** and **Docker Compose** for the supported path below.
- Compose file sets a **4G** memory limit and **2** CPUs max for `tts-server` (see `docker-compose.yml`). Adjust if your model or host differs.

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
docker compose logs -f tts-server
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

Install dependencies:

```bash
pip install -r app/requirements.txt
```

Run with module path pointing at the package layout you use. If running from repo root with `app` as a package directory:

```bash
uvicorn app.main:app --reload --app-dir .
```

Verify `VOICES_DIR` and paths match your machine if you deviate from `/app/voices`.
