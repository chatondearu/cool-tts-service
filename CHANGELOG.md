# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-04-04

### Added

- Audio transcoding: `mp3` (44.1 kHz) and `opus` (48 kHz) output via FFmpeg on `/generate` and `/v1/audio/speech` (`response_format` field).
- Synthesis logging with structured JSON-lines and in-memory ring buffer; new `GET /admin/synthesis-logs` endpoint with `limit`, `errors_only`, `client`, and `route` filters.
- Synthesis logs page in the web UI.
- Home Assistant integration guide (`doc/home-assistant.md`).
- LiteLLM proxy integration guide (`doc/litellm.md`).

### Changed

- Docker Compose: renamed services and environment variables for Coolify compatibility (`SERVICE_URL_COOLTTS_*`).
- README header revamped with badges, screenshot, and highlights section.

### Fixed

- Corrected environment variable syntax in Docker Compose.

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

[1.1.0]: https://github.com/chatondearu/cool-tts-service/releases/tag/v1.1.0
[1.0.0]: https://github.com/chatondearu/cool-tts-service/releases/tag/v1.0.0
