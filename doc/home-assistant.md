# Home Assistant (OpenAI TTS HACS)

This guide uses the **[OpenAI TTS](https://github.com/sfortis/openai_tts)** custom integration (**HACS**). That integration speaks the same **OpenAI-compatible** `POST /v1/audio/speech` protocol as this service.

Also read `**[deployment.md](deployment.md)`** for URLs behind Traefik/Coolify (`/tts-server` prefix) and `**[development.md](development.md)**` for local smoke tests.

## Prerequisites

- Home Assistant with **[HACS](https://hacs.xyz/)** installed.
- Network reachability from Home Assistant to the Cool TTS API (LAN IP, Docker host, or public HTTPS URL).
- Kokoro **loaded** on the API (`GET /health` → `tts_ready: true`). Otherwise synthesis returns **503**.
- **Home Assistant 2025.7+** if you use the integration’s **profile sub-entries** (current default flow in recent `openai_tts` releases). Older installs may still store model/voice on the main entry; the values below are the same.

## Install the custom integration

1. In Home Assistant, open **HACS** → **Integrations**.
2. Search for **OpenAI TTS** (repository: `[sfortis/openai_tts](https://github.com/sfortis/openai_tts)`).
3. **Download** the integration, then **restart** Home Assistant.

## Step 1 — Add the integration (API URL and optional key)

1. Go to **Settings** → **Devices & services** → **Add integration**.
2. Choose **OpenAI TTS**.
3. Fill in:
  - **URL** — full speech endpoint (include path):
    - Local API: `http://<host>:9000/v1/audio/speech`
    - Behind Coolify/Traefik (example): `https://tts.example.com/tts-server/v1/audio/speech`
  - **API key** — leave **empty** if the API does not use `API_TOKEN`. If you set `API_TOKEN` on the Cool TTS stack, enter the **same value** here (the integration sends `Authorization: Bearer …` only when a key is present; Cool TTS requires that header for `POST /v1/audio/speech` when `API_TOKEN` is set).

Submit the form to create the **main** config entry (connection + credentials only in the modern flow).

## Step 2 — First profile (model, voice, and `wav`)

Recent `openai_tts` versions attach **model**, **voice**, and related options to a **profile** (sub-entry), not to that first screen.

1. Open **Settings** → **Devices & services** → **OpenAI TTS** (the entry you just created).
2. Use the control that adds a **profile** / **sub-entry** for this integration (wording varies slightly by Home Assistant version; it is the flow that asks for **profile name**, **model**, and **voice**).

Configure the **first profile** roughly as follows:


| Field                   | Value                        | Notes                                                                                                                                                                                                                            |
| ----------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Profile name**        | Any label (e.g. `Kokoro`)    | Shown in the UI only.                                                                                                                                                                                                            |
| **Model**               | `kokoro-v1.0`                | Use **custom** input if it is not in the dropdown. This must match the model id returned by `GET /v1/models` when TTS is ready.                                                                                                  |
| **Voice**               | A voice id from your server  | Must match an id from `GET /v1/audio/voices` (same ids as `GET /voices`). Examples used elsewhere in this repo’s docs include `af_sarah` (en-us) and `ff_siwis` (fr-fr) — use **custom** input if the id is not in the dropdown. |
| **Speed**               | `1.0` (default)              | Allowed range on the API is **0.25–4.0**.                                                                                                                                                                                        |
| **Extra payload**       | Optional JSON                | The integration often defaults to **`response_format`: `mp3`**, which Cool TTS supports when **`ffmpeg`** is available (Docker API image includes it). You may set **`response_format`** to `wav`, `mp3`, or `opus` explicitly. The integration merges this JSON into the request body.   |
| **Language** (optional) | —                            | The API infers language from the voice prefix when omitted. To force a locale, extend **Extra payload**, e.g. `{"response_format": "mp3", "language": "fr-fr"}`.                                                                 |


Optional fields (chime, normalization, instructions) are integration-specific; they do not change the Cool TTS HTTP contract except via merged **Extra payload** keys.

## Step 3 — Use it in Home Assistant

- **Developer tools** → **Services** → `tts.speak` (or the integration’s `openai_tts.say` if you use it): select the **TTS entity** created for your profile and run a short test message.
- **Voice assistant**: in your assistant pipeline, set the **Text-to-speech** engine to the **OpenAI TTS** entity that corresponds to this profile.

## Troubleshooting


| Symptom                               | Likely cause                                                                                                                                                        |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **401** from the API                  | `API_TOKEN` is set on Cool TTS but the integration **API key** is empty or wrong.                                                                                   |
| **422** `Unsupported response_format` | Use **`wav`**, **`mp3`**, or **`opus`** only.                                                                                            |
| **422** `Unknown voice`               | **Voice** does not exactly match an id from `GET /v1/audio/voices`.                                                                                                 |
| **503**                               | Engine not loaded (`tts_ready`), or mp3/opus without **`ffmpeg`**. Check `GET /health` (`tts_error`, `ffmpeg_available`).                                                                       |
| No audio / wrong host                 | URL must be the **full** `…/v1/audio/speech` path; behind a reverse proxy, include the same **prefix** as in `[deployment.md](deployment.md)` (e.g. `/tts-server`). |


## References

- Upstream integration: [sfortis/openai_tts](https://github.com/sfortis/openai_tts)
- API surface in this repo: `POST /v1/audio/speech`, `GET /v1/audio/voices`, `GET /v1/models` in `[generator/main.py](../generator/main.py)`

