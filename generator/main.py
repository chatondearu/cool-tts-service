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
from typing import Any, Optional

import soundfile as sf
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

import model_bootstrap
from tts_engine import KokoroTTS

logger = logging.getLogger("cool-tts")

_PACKAGE_DIR = Path(__file__).resolve().parent
_API_TOKEN = os.environ.get("API_TOKEN", "")
_ROOT_PATH = os.environ.get("ROOT_PATH", "")

_MODEL_ID = "kokoro-v1.0"

_MAX_ONNX_BYTES = 400 * 1024 * 1024
_MAX_VOICES_BIN_BYTES = 64 * 1024 * 1024

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


def _resolved_model_path() -> Path:
    return Path(os.environ.get("KOKORO_MODEL_PATH", str(_default_model_path())))


def _resolved_voices_bin_path() -> Path:
    return Path(os.environ.get("KOKORO_VOICES_BIN_PATH", str(_default_voices_bin_path())))


def _tts_unavailable_message(
    model_path: Path,
    voices_bin_path: Path,
    technical: Optional[str] = None,
) -> str:
    parts = [
        "TTS engine is not loaded: Kokoro model files are missing or invalid.",
        f"Expected ONNX at {model_path} and voices bundle at {voices_bin_path}.",
        "Add files from https://github.com/thewh1teagle/kokoro-onnx/releases (tag model-files-v1.0), "
        "or set KOKORO_AUTO_DOWNLOAD=1 with a writable models directory (see deployment docs).",
    ]
    if technical:
        parts.append(f"Details: {technical}")
    return " ".join(parts)


def _try_load_tts(model_path: Path, voices_bin_path: Path) -> tuple[Optional[KokoroTTS], Optional[str]]:
    try:
        return KokoroTTS(model_path, voices_bin_path), None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Kokoro load failed: %s", exc)
        return None, str(exc)


async def _bootstrap_and_load(app: FastAPI) -> None:
    model_path = _resolved_model_path()
    voices_bin_path = _resolved_voices_bin_path()
    logger.info("Model path: %s", model_path)
    logger.info("Voices path: %s", voices_bin_path)

    dl_ok, dl_err = await asyncio.to_thread(
        model_bootstrap.ensure_kokoro_files,
        model_path,
        voices_bin_path,
    )
    if not dl_ok and dl_err:
        logger.warning("KOKORO_AUTO_DOWNLOAD: %s", dl_err)

    tts, load_err = await asyncio.to_thread(_try_load_tts, model_path, voices_bin_path)
    app.state.tts = tts
    if tts is not None:
        app.state.tts_error = None
        logger.info("TTS ready — %d voices available", len(tts.list_voices()))
    else:
        app.state.tts_error = _tts_unavailable_message(
            model_path,
            voices_bin_path,
            load_err,
        )
        logger.warning("TTS not loaded — %s", app.state.tts_error)


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
    await _bootstrap_and_load(app)
    yield


app = FastAPI(title="Cool TTS Service", lifespan=lifespan, root_path=_ROOT_PATH)

if _API_TOKEN:
    app.add_middleware(_BearerTokenMiddleware)
    logger.info("Bearer token authentication enabled")


def _require_tts(request: Request) -> KokoroTTS:
    tts: KokoroTTS | None = getattr(request.app.state, "tts", None)
    if tts is None:
        detail = getattr(request.app.state, "tts_error", None) or _tts_unavailable_message(
            _resolved_model_path(),
            _resolved_voices_bin_path(),
        )
        raise HTTPException(status_code=503, detail=detail)
    return tts


# ---------------------------------------------------------------------------
# Internal routes (used by the Nuxt UI)
# ---------------------------------------------------------------------------


@app.get("/health")
async def health(request: Request) -> dict[str, Any]:
    tts: KokoroTTS | None = getattr(request.app.state, "tts", None)
    body: dict[str, Any] = {"status": "ok", "tts_ready": tts is not None}
    err = getattr(request.app.state, "tts_error", None)
    if err:
        body["tts_error"] = err
    return body


@app.get("/voices")
async def voices(request: Request) -> dict[str, list[str]]:
    """List all available voice ids from the loaded bundle (empty if TTS is not loaded)."""
    tts: KokoroTTS | None = getattr(request.app.state, "tts", None)
    if tts is None:
        return {"voices": []}
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
    tts = _require_tts(request)

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
# Admin: model files (requires API_TOKEN when set)
# ---------------------------------------------------------------------------


@app.get("/admin/models/status")
async def admin_models_status(request: Request) -> dict[str, Any]:
    model_path = _resolved_model_path()
    voices_bin_path = _resolved_voices_bin_path()
    tts: KokoroTTS | None = getattr(request.app.state, "tts", None)
    out: dict[str, Any] = {
        "tts_ready": tts is not None,
        "tts_error": getattr(request.app.state, "tts_error", None),
        "model_path": str(model_path),
        "model_exists": model_path.is_file(),
        "voices_path": str(voices_bin_path),
        "voices_exists": voices_bin_path.is_file(),
    }
    if model_path.is_file():
        out["model_bytes"] = model_path.stat().st_size
    if voices_bin_path.is_file():
        out["voices_bytes"] = voices_bin_path.stat().st_size
    return out


@app.post("/admin/models/upload")
async def admin_models_upload(
    onnx: UploadFile | None = File(None),
    voices_bin: UploadFile | None = File(None),
) -> dict[str, Any]:
    if (onnx is None or not onnx.filename) and (voices_bin is None or not voices_bin.filename):
        raise HTTPException(
            status_code=422,
            detail="Provide at least one file field: onnx and/or voices_bin.",
        )

    model_path = _resolved_model_path()
    voices_bin_path = _resolved_voices_bin_path()
    saved: list[str] = []

    if onnx is not None and onnx.filename:
        body = await onnx.read()
        if len(body) > _MAX_ONNX_BYTES:
            raise HTTPException(status_code=413, detail="ONNX file exceeds maximum allowed size.")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = model_path.with_suffix(model_path.suffix + ".part")
        tmp.write_bytes(body)
        tmp.replace(model_path)
        saved.append("onnx")

    if voices_bin is not None and voices_bin.filename:
        body = await voices_bin.read()
        if len(body) > _MAX_VOICES_BIN_BYTES:
            raise HTTPException(status_code=413, detail="Voices bundle exceeds maximum allowed size.")
        voices_bin_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = voices_bin_path.with_suffix(voices_bin_path.suffix + ".part")
        tmp.write_bytes(body)
        tmp.replace(voices_bin_path)
        saved.append("voices_bin")

    return {
        "saved": saved,
        "message": "Files written. Call POST /admin/models/reload to load them into the running process.",
    }


@app.post("/admin/models/reload")
async def admin_models_reload(request: Request) -> dict[str, Any]:
    app = request.app
    model_path = _resolved_model_path()
    voices_bin_path = _resolved_voices_bin_path()
    tts, load_err = await asyncio.to_thread(_try_load_tts, model_path, voices_bin_path)
    app.state.tts = tts
    if tts is not None:
        app.state.tts_error = None
        return {"tts_ready": True, "voice_count": len(tts.list_voices())}
    app.state.tts_error = _tts_unavailable_message(model_path, voices_bin_path, load_err)
    return {"tts_ready": False, "error": app.state.tts_error}


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

    tts = _require_tts(request)

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
    tts: KokoroTTS | None = getattr(request.app.state, "tts", None)
    if tts is None:
        return []
    return [{"id": v, "name": v} for v in tts.list_voices()]


@app.get("/v1/models")
async def openai_models(request: Request) -> dict:
    """Minimal OpenAI-compatible models listing (empty when TTS is not loaded)."""
    tts: KokoroTTS | None = getattr(request.app.state, "tts", None)
    if tts is None:
        return {"object": "list", "data": []}
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
