"""FastAPI entrypoint: Kokoro ONNX TTS.

Exposes two API surfaces that share the same synthesis engine:
- Internal routes used by the Nuxt UI: POST /generate, GET /voices, GET /health
- OpenAI-compatible routes for Open WebUI / Home Assistant:
  POST /v1/audio/speech, GET /v1/audio/voices, GET /v1/models
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import soundfile as sf
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from tts_engine import KokoroTTS

logger = logging.getLogger("cool-tts")

_PACKAGE_DIR = Path(__file__).resolve().parent
_API_TOKEN = os.environ.get("API_TOKEN", "")
_ROOT_PATH = os.environ.get("ROOT_PATH", "")

_MODEL_ID = "kokoro-v1.0"

# Kokoro voice prefix → language code used by misaki / espeak-ng.
_VOICE_PREFIX_TO_LANG: dict[str, str] = {
    "a": "en-us",
    "b": "en-gb",
    "j": "ja",
    "z": "cmn",
    "e": "es",
    "f": "fr-fr",
    "h": "hi",
    "i": "it",
    "p": "pt-br",
}

_DEFAULT_LANG = "en-us"


def _infer_language(voice_id: str, explicit: Optional[str] = None) -> str:
    """Return *explicit* when provided, otherwise guess from the voice prefix."""
    if explicit:
        return explicit
    prefix = voice_id[:1] if voice_id else ""
    return _VOICE_PREFIX_TO_LANG.get(prefix, _DEFAULT_LANG)


class _BearerTokenMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid Bearer token when API_TOKEN is set."""

    OPEN_PATHS = {
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/v1/models",
        "/v1/audio/voices",
    }

    async def dispatch(self, request: Request, call_next):
        if not _API_TOKEN or request.url.path in self.OPEN_PATHS:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {_API_TOKEN}":
            return JSONResponse({"detail": "Invalid or missing token"}, status_code=401)
        return await call_next(request)


def _default_model_path() -> Path:
    return _PACKAGE_DIR / "models" / "kokoro-v1.0.onnx"


def _default_voices_bin_path() -> Path:
    return _PACKAGE_DIR / "models" / "voices-v1.0.bin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = Path(os.environ.get("KOKORO_MODEL_PATH", str(_default_model_path())))
    voices_bin_path = Path(
        os.environ.get("KOKORO_VOICES_BIN_PATH", str(_default_voices_bin_path()))
    )
    logger.info("Loading model from %s", model_path)
    logger.info("Loading voices from %s", voices_bin_path)
    tts = KokoroTTS(model_path, voices_bin_path)
    app.state.tts = tts
    logger.info("TTS ready — %d voices available", len(tts.list_voices()))
    yield


app = FastAPI(title="Cool TTS Service", lifespan=lifespan, root_path=_ROOT_PATH)

if _API_TOKEN:
    app.add_middleware(_BearerTokenMiddleware)
    logger.info("Bearer token authentication enabled")


# ---------------------------------------------------------------------------
# Internal routes (used by the Nuxt UI)
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/voices")
async def voices(request: Request) -> dict[str, list[str]]:
    """List all available voice ids from the loaded bundle."""
    tts: KokoroTTS = request.app.state.tts
    return {"voices": tts.list_voices()}


class GenerateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: str = Field(
        ...,
        min_length=1,
        description="Language code for Kokoro (e.g. fr-fr, en-us).",
    )
    voice_id: str = Field(
        ...,
        min_length=1,
        description="Bundled Kokoro voice id (e.g. af_sarah).",
    )
    speed: float = Field(
        1.0,
        gt=0,
        le=5.0,
        description="Playback speed multiplier (0 < speed <= 5).",
    )


def _synthesize_wav_bytes(
    tts: KokoroTTS, text: str, voice_id: str, lang: str, speed: float
) -> bytes:
    samples = tts.generate_audio(text=text, voice_id=voice_id, lang=lang, speed=speed)
    buf = io.BytesIO()
    sf.write(buf, samples, tts.sample_rate, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


@app.post("/generate")
async def generate(request: Request, body: GenerateRequest) -> StreamingResponse:
    tts: KokoroTTS = request.app.state.tts

    available = tts.list_voices()
    if body.voice_id not in available:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown voice_id '{body.voice_id}'. "
            f"Use GET /voices for the list ({len(available)} available).",
        )

    wav_bytes = await asyncio.to_thread(
        _synthesize_wav_bytes,
        tts,
        body.text,
        body.voice_id,
        body.language,
        body.speed,
    )
    return StreamingResponse(
        iter([wav_bytes]),
        media_type="audio/wav",
        headers={"Content-Disposition": 'attachment; filename="speech.wav"'},
    )


# ---------------------------------------------------------------------------
# OpenAI-compatible routes (Open WebUI, Home Assistant openai_tts, etc.)
# ---------------------------------------------------------------------------

_SUPPORTED_RESPONSE_FORMATS = {"wav"}


class OpenAISpeechRequest(BaseModel):
    model: str = Field(..., min_length=1)
    input: str = Field(..., min_length=1)
    voice: str = Field(..., min_length=1)
    response_format: str = Field("wav")
    speed: float = Field(1.0, ge=0.25, le=4.0)
    language: Optional[str] = Field(
        None,
        description="Optional Kokoro language code (e.g. fr-fr). "
        "When omitted the language is inferred from the voice prefix.",
    )


@app.post("/v1/audio/speech")
async def openai_speech(
    request: Request, body: OpenAISpeechRequest,
) -> StreamingResponse:
    """OpenAI-compatible speech synthesis endpoint."""
    if body.response_format not in _SUPPORTED_RESPONSE_FORMATS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported response_format '{body.response_format}'. "
            f"Supported: {', '.join(sorted(_SUPPORTED_RESPONSE_FORMATS))}.",
        )

    tts: KokoroTTS = request.app.state.tts

    available = tts.list_voices()
    if body.voice not in available:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown voice '{body.voice}'. "
            f"Use GET /v1/audio/voices for the list ({len(available)} available).",
        )

    lang = _infer_language(body.voice, body.language)

    wav_bytes = await asyncio.to_thread(
        _synthesize_wav_bytes, tts, body.input, body.voice, lang, body.speed,
    )
    return StreamingResponse(
        iter([wav_bytes]),
        media_type="audio/wav",
        headers={"Content-Disposition": 'attachment; filename="speech.wav"'},
    )


@app.get("/v1/audio/voices")
async def openai_voices(request: Request) -> list[dict[str, str]]:
    """List voices in OpenAI-compatible format."""
    tts: KokoroTTS = request.app.state.tts
    return [{"id": v, "name": v} for v in tts.list_voices()]


@app.get("/v1/models")
async def openai_models() -> dict:
    """Minimal OpenAI-compatible models listing."""
    return {
        "object": "list",
        "data": [
            {
                "id": _MODEL_ID,
                "object": "model",
                "owned_by": "cool-tts",
            }
        ],
    }
