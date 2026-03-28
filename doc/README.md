# cool-tts-service — documentation

CPU-oriented TTS HTTP service built with **FastAPI**. The runtime loads a **Voxtral Mini 3B**-class model via `vllm_omni.OmniModel` (see `app/model.py`).

## Contents

- [Architecture](architecture.md)
- [HTTP API](api.md)
- [Deployment](deployment.md)
- [Configuration](configuration.md)

## Quick orientation

| Area | Location |
|------|----------|
| API app | `app/main.py` |
| Model wrapper | `app/model.py` |
| Container | `Dockerfile`, `docker-compose.yml` |
| Local dev (Nix) | `flake.nix`, `flake.lock`, optional `.envrc` (direnv) — see [Deployment](deployment.md) |
| Packaged voices | `app/voices/` (mounted as `/app/voices` in Docker) |
| Helper scripts | `scripts/add_voice.py`, `scripts/test_tts.py` |

Start locally or with Docker as described in [Deployment](deployment.md).
