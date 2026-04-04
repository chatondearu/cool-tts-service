# LiteLLM proxy (OpenAI-compatible TTS)

[LiteLLM](https://docs.litellm.ai/) can expose an OpenAI-style **`POST /v1/audio/speech`** endpoint and forward requests to this service using the **`openai/`** provider with a custom **`api_base`**. The same contract as in [`deployment.md`](deployment.md) applies: model id **`kokoro-v1.0`**, voice ids from **`GET /v1/audio/voices`**, and **`response_format`** may be **`wav`**, **`mp3`**, or **`opus`** (mp3/opus require **`ffmpeg`** on the Cool TTS API host).

Official LiteLLM references:

- [Text-to-speech / `/audio/speech`](https://docs.litellm.ai/docs/text_to_speech)
- [OpenAI-compatible endpoints (`api_base`)](https://docs.litellm.ai/docs/providers/openai_compatible)
- [Model management (YAML + `/model/new`)](https://docs.litellm.ai/docs/proxy/model_management)
- [Admin UI](https://docs.litellm.ai/docs/proxy/ui)

## `api_base` URL

LiteLLM’s OpenAI client expects a base URL that includes the **`/v1`** suffix; it then calls **`/audio/speech`** on that base (see LiteLLM’s OpenAI-compatible docs).

| Deployment | Example `api_base` |
| ---------- | ------------------ |
| Cool TTS on host port 9000 | `http://127.0.0.1:9000/v1` |
| Cool TTS API container on the same Docker network as LiteLLM (this repo’s compose service name `api`) | `http://api:9000/v1` |
| Behind Coolify / Traefik with path prefix | `https://tts.example.com/tts-server/v1` |

Adjust hostnames and TLS to match your environment.

## Authentication

- If **Cool TTS** has **`API_TOKEN` unset**, no Bearer token is required; you can still set a placeholder **`api_key`** in LiteLLM if the OpenAI client or your LiteLLM version requires a non-empty value (e.g. `dummy` or `""` per [OpenAI-compatible endpoints](https://docs.litellm.ai/docs/providers/openai_compatible)).
- If **`API_TOKEN` is set**, use the **same value** as **`api_key`** (or `os.environ/…`) so LiteLLM sends `Authorization: Bearer …` to Cool TTS.

## YAML configuration (`config.yaml`)

Add a **`model_list`** entry. **`model_name`** is the alias clients use when calling the **LiteLLM proxy**; **`litellm_params.model`** must be **`openai/kokoro-v1.0`** so LiteLLM routes the call as OpenAI-compatible TTS to your **`api_base`**.

```yaml
model_list:
  - model_name: kokoro-tts
    litellm_params:
      model: openai/kokoro-v1.0
      api_base: http://127.0.0.1:9000/v1
      api_key: os.environ/COOL_TTS_API_TOKEN
    model_info:
      description: "Cool TTS Service (Kokoro ONNX) via OpenAI-compatible /v1/audio/speech"
```

- If Cool TTS does not use a token, you can use `api_key: ""` or a dummy string, depending on what your LiteLLM/OpenAI client accepts.
- Point **`api_base`** at your real host, port, and optional **`/tts-server`** prefix.

Start the proxy as usual, for example:

```bash
litellm --config /path/to/config.yaml
```

### Optional: add the same model without editing YAML

LiteLLM supports **`POST /model/new`** on the proxy (see [Model management](https://docs.litellm.ai/docs/proxy/model_management)). Example payload (master/proxy auth as required by your setup):

```bash
curl -sS -X POST "http://localhost:4000/model/new" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "kokoro-tts",
    "litellm_params": {
      "model": "openai/kokoro-v1.0",
      "api_base": "http://127.0.0.1:9000/v1",
      "api_key": "os.environ/COOL_TTS_API_TOKEN"
    },
    "model_info": {
      "description": "Cool TTS Service (Kokoro ONNX)"
    }
  }'
```

## Admin UI configuration

When the [LiteLLM Admin UI](https://docs.litellm.ai/docs/proxy/ui) is enabled (proxy with DB, master key, `UI_USERNAME` / `UI_PASSWORD` as in the LiteLLM docs):

1. Open **`http://<proxy-host>:<port>/ui`** (or your configured URL).
2. Sign in with the UI credentials.
3. Use **Model management** → **Add model** (wording may vary slightly by version).
4. Enter the same logical fields as in **`litellm_params`** above:
   - **Model name** (proxy alias): e.g. `kokoro-tts`
   - **LiteLLM model** / provider model: `openai/kokoro-v1.0`
   - **API base**: your Cool TTS **`…/v1`** URL (see table above)
   - **API key**: environment reference like `os.environ/COOL_TTS_API_TOKEN`, or empty/dummy if Cool TTS has no token

If the UI shows separate fields for “custom headers” or “extra params”, you usually do **not** need them for Cool TTS; **`response_format`** is set by the **client** of the proxy (next section).

## Calling the proxy: `response_format` and `voice`

Clients that use **`POST /v1/audio/speech`** through LiteLLM should send **`response_format`** explicitly when needed: **`wav`**, **`mp3`**, or **`opus`**. Unsupported values return **422**; mp3/opus without **`ffmpeg`** on Cool TTS return **503**.

Example via the LiteLLM proxy (use your proxy key if configured):

```bash
curl -sS "http://localhost:4000/v1/audio/speech" \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro-tts",
    "input": "Hello from LiteLLM.",
    "voice": "af_sarah",
    "response_format": "wav"
  }' \
  --output speech.wav
```

- **`model`**: the **`model_name`** you configured on the proxy (`kokoro-tts` in the examples above), not necessarily the upstream id.
- **`voice`**: a valid id from Cool TTS (`GET http://<cool-tts>/v1/audio/voices`).

Optional **`language`** (e.g. `"fr-fr"`) is supported by Cool TTS when you need to override inference from the voice prefix; see [`deployment.md`](deployment.md).

## Troubleshooting

| Issue | What to check |
| ----- | ------------- |
| **404** / **Not Found** on upstream | **`api_base`** must end with **`/v1`** (LiteLLM appends **`/audio/speech`**). |
| **422** `Unsupported response_format` | Use **`wav`**, **`mp3`**, or **`opus`** only. |
| **422** `Unknown voice` | **`voice`** must match Cool TTS exactly (see **`GET /v1/audio/voices`**). |
| **401** from Cool TTS | Align **`api_key`** in LiteLLM with **`API_TOKEN`** on Cool TTS. |
| **503** from Cool TTS | Kokoro not loaded, or mp3/opus requested without **`ffmpeg`**; check **`GET /health`** on Cool TTS (`ffmpeg_available`). |

## See also

- [`deployment.md`](deployment.md) — OpenAI routes, Traefik prefix, **`API_TOKEN`**
- [`home-assistant.md`](home-assistant.md) — OpenAI-style **`response_format`** for Home Assistant **`openai_tts`**
