"""
TTS Server - FastAPI

Endpoints:
- POST /tts: Generate speech from text
- GET /health: Health check
- GET /voices: List available voices
"""

import os
import sys
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional
from loguru import logger
from model import TTSModel  # Local model wrapper

# Initialize FastAPI
app = FastAPI(title="TTS Server", version="0.1.0")

# Configure logging (LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, … — logging module names)
_log_name = os.getenv("LOG_LEVEL", "INFO").upper()
try:
    _py_level = getattr(logging, _log_name)
except AttributeError:
    _py_level = logging.INFO
    _log_name = "INFO"
logging.basicConfig(level=_py_level)
logger.remove()
logger.add(sys.stderr, level=_log_name)
logger.add("tts_server.log", rotation="10 MB", level=_log_name)

# Load model (lazy loading)
model = TTSModel()
VOICES_DIR = os.getenv("VOICES_DIR", "/app/voices")
DEFAULT_VOICE = "generate_0_FR"


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = DEFAULT_VOICE
    response_format: Optional[str] = "wav"


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse(content={"status": "healthy"})


@app.get("/voices")
async def list_voices():
    """List available voices."""
    try:
        voices = os.listdir(f"{VOICES_DIR}/default")
        voices = [v.replace(".wav", "") for v in voices if v.endswith(".wav")]
        return JSONResponse(content={"voices": voices})
    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        raise HTTPException(status_code=500, detail="Failed to list voices")


@app.post("/tts")
async def generate_tts(request: TTSRequest):
    """Generate speech from text."""
    try:
        logger.info(f"Generating TTS for text: '{request.text[:50]}...' with voice: {request.voice}")
        
        # Generate audio (return bytes in-process to avoid concurrent /tmp clashes)
        audio = model.generate(
            text=request.text,
            voice=request.voice,
            response_format=request.response_format
        )
        if not isinstance(audio, (bytes, bytearray)):
            audio = bytes(audio)
        return Response(
            content=audio,
            media_type="audio/wav",
            headers={"Content-Disposition": 'attachment; filename="output.wav"'},
        )
        
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)