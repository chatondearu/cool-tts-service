# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-03

### Added

- FastAPI TTS API with Kokoro ONNX (`POST /generate`, `GET /voices`, `GET /health`).
- OpenAI-compatible routes (`POST /v1/audio/speech`, `GET /v1/audio/voices`, `GET /v1/models`) for Open WebUI, Home Assistant, and similar clients.
- Admin model routes (`GET/POST /admin/models/…`) when `API_TOKEN` is set.
- Nuxt 4 web UI (login, TTS, voices) with server-side proxy to the API.
- Docker images for API and UI; Compose stacks for Coolify/Traefik and local development.
- Optional `KOKORO_AUTO_DOWNLOAD` for first-boot model fetch; volume mounts for `models/` and `voices/`.
- Nix dev shell (Python 3.11, uv, Node.js 22) and voice preparation scripts under `voice_prep_module/`.
- Pre-built container images published to GitHub Container Registry; `docker-compose.image.yml` for pull-and-run deployment.

[1.0.0]: https://github.com/chatondearu/cool-tts-service/releases/tag/v1.0.0
