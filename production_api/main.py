"""FastAPI entrypoint: Kokoro ONNX TTS with POST /generate -> WAV stream."""

from __future__ import annotations

import asyncio
import io
import os
from contextlib import asynccontextmanager
from pathlib import Path

import soundfile as sf
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from tts_engine import KokoroTTS

_PACKAGE_DIR = Path(__file__).resolve().parent


def _default_model_path() -> Path:
    return _PACKAGE_DIR / "models" / "kokoro-v1.0.onnx"


def _default_voices_bin_path() -> Path:
    return _PACKAGE_DIR / "models" / "voices-v1.0.bin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = Path(os.environ.get("KOKORO_MODEL_PATH", _default_model_path()))
    voices_bin_path = Path(
        os.environ.get("KOKORO_VOICES_BIN_PATH", _default_voices_bin_path())
    )
    app.state.tts = KokoroTTS(model_path, voices_bin_path)
    yield


app = FastAPI(title="Cool TTS Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness/readiness probe (TTS is ready once the process has started)."""
    return {"status": "ok"}


class GenerateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: str = Field(
        ...,
        min_length=1,
        description="Grapheme / language code for Kokoro (e.g. fr-fr, en-us).",
    )
    voice_id: str = Field(
        ...,
        min_length=1,
        description="Bundled Kokoro voice id (e.g. af_sarah).",
    )


def _synthesize_wav_bytes(tts: KokoroTTS, text: str, voice_id: str, lang: str) -> bytes:
    samples = tts.generate_audio(text=text, voice_id=voice_id, lang=lang)
    sample_rate = tts.sample_rate
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return buf.read()


@app.post("/generate")
async def generate(request: Request, body: GenerateRequest) -> StreamingResponse:
    tts: KokoroTTS = request.app.state.tts
    wav_bytes = await asyncio.to_thread(
        _synthesize_wav_bytes,
        tts,
        body.text,
        body.voice_id,
        body.language,
    )
    return StreamingResponse(
        iter([wav_bytes]),
        media_type="audio/wav",
        headers={"Content-Disposition": 'attachment; filename="speech.wav"'},
    )
