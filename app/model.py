"""
TTS Model Wrapper for Voxtral
"""

import os
from vllm_omni import OmniModel
from loguru import logger

_DEFAULT_MODEL = "mistralai/Voxtral-Mini-3B-TTS-2603"


def _apply_cache_dir_env() -> None:
    """Point Hugging Face caches at CACHE_DIR when set (Docker volume)."""
    cache_dir = os.getenv("CACHE_DIR", "").strip()
    if not cache_dir:
        return
    os.makedirs(cache_dir, exist_ok=True)
    # HF libraries resolve hub and transformers assets under HF_HOME by default
    os.environ.setdefault("HF_HOME", cache_dir)


class TTSModel:
    """Wrapper for Voxtral TTS model."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.getenv("MODEL_NAME", _DEFAULT_MODEL)
        self.model = None

    def load(self):
        """Load the TTS model."""
        if self.model is None:
            try:
                _apply_cache_dir_env()
                logger.info(f"Loading model: {self.model_name}")
                self.model = OmniModel.from_pretrained(self.model_name)
                logger.info("Model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise

    def generate(self, text: str, voice: str = "fr_female_1", response_format: str = "wav") -> bytes:
        """Generate speech from text."""
        if self.model is None:
            self.load()
        
        try:
            logger.info(f"Generating TTS for text: '{text[:50]}...' with voice: {voice}")
            audio = self.model.generate(
                input=text,
                voice=voice,
                response_format=response_format
            )
            return audio
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            raise