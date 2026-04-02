"""FastAPI entrypoint: Kokoro ONNX TTS with POST /generate -> WAV stream."""

from __future__ import annotations

import asyncio
import io
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import soundfile as sf
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from tts_engine import KokoroTTS

logger = logging.getLogger("cool-tts")

_PACKAGE_DIR = Path(__file__).resolve().parent
_API_TOKEN = os.environ.get("API_TOKEN", "")


class _BearerTokenMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid Bearer token when API_TOKEN is set."""

    OPEN_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if not _API_TOKEN or request.url.path in self.OPEN_PATHS:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {_API_TOKEN}":
            from starlette.responses import JSONResponse

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


app = FastAPI(title="Cool TTS Service", lifespan=lifespan)

if _API_TOKEN:
    app.add_middleware(_BearerTokenMiddleware)
    logger.info("Bearer token authentication enabled")


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
