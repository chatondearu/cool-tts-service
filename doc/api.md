# HTTP API

Base URL in local / default Docker setup: `http://localhost:8000`.

## `GET /health`

Returns service liveness.

**Response** `200` — `application/json`:

```json
{"status": "healthy"}
```

**Example:**

```bash
curl -s http://localhost:8000/health
```

---

## `GET /voices`

Lists **default** voice IDs derived from `{VOICES_DIR}/default/*.wav` (stem of the filename, without `.wav`).

**Response** `200` — `application/json`:

```json
{"voices": ["generate_0_FR"]}
```

**Errors:**

- `500` — if listing fails (e.g. missing directory); detail: `"Failed to list voices"`.

**Example:**

```bash
curl -s http://localhost:8000/voices
```

---

## `POST /tts`

Generates speech and returns a **WAV** file by default.

**Request** `application/json` body (Pydantic `TTSRequest`):

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|--------|
| `text` | string | yes | — | Input text |
| `voice` | string | no | `generate_0_FR` | Voice id (must match available samples / model expectations) |
| `response_format` | string | no | `wav` | Passed through to the model wrapper |

**Response** `200` — `audio/wav`:

- `Content-Disposition: attachment; filename="output.wav"`
- Body: binary WAV bytes (served in memory; no shared temp path on disk)

**Errors:**

- `500` — generation failure; `detail` contains the exception message string.

**Example:**

```bash
curl -s -X POST "http://localhost:8000/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour, ceci est un test.", "voice": "generate_0_FR"}' \
  --output output.wav
```

---

## OpenAPI

FastAPI exposes interactive docs at:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- Schema: `/openapi.json`
