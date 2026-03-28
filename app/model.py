"""
TTS Model Wrapper for Voxtral (vLLM-Omni Omni API).
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from loguru import logger
from mistral_common.protocol.speech.request import SpeechRequest
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from vllm import SamplingParams
from vllm_omni.entrypoints.omni import Omni

_DEFAULT_MODEL = "mistralai/Voxtral-4B-TTS-2603"

# Voxtral offline example uses 24 kHz (see vllm-omni voxtral_tts/end2end.py)
_TTS_SAMPLE_RATE_HZ = 24000

_tokenizer_cache: dict[str, MistralTokenizer] = {}


def _apply_cache_dir_env() -> None:
    """Point Hugging Face caches at CACHE_DIR when set (Docker volume)."""
    cache_dir = os.getenv("CACHE_DIR", "").strip()
    if not cache_dir:
        return
    os.makedirs(cache_dir, exist_ok=True)
    os.environ.setdefault("HF_HOME", cache_dir)


def _normalize_hf_token_env() -> None:
    """Drop blank HF tokens so the hub client does not send invalid Authorization (401)."""
    cleared: list[str] = []
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        raw = os.environ.get(key)
        if raw is not None and not raw.strip():
            del os.environ[key]
            cleared.append(key)
    if cleared:
        logger.warning(
            "Removed empty Hugging Face token env var(s) {}: they cause 401 Invalid username or password. "
            "For gated Mistral models, set a valid read token (see doc/configuration.md).",
            ", ".join(cleared),
        )
    hf = os.environ.get("HF_TOKEN", "").strip()
    hub = os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    if hf and not hub:
        os.environ["HUGGING_FACE_HUB_TOKEN"] = hf
    elif hub and not hf:
        os.environ["HF_TOKEN"] = hub


def _get_mistral_tokenizer(model_name: str) -> MistralTokenizer:
    if model_name not in _tokenizer_cache:
        path = Path(model_name)
        if path.is_dir():
            _tokenizer_cache[model_name] = MistralTokenizer.from_file(str(path / "tekken.json"))
        else:
            _tokenizer_cache[model_name] = MistralTokenizer.from_hf_hub(model_name)
    return _tokenizer_cache[model_name]


def _build_voxtral_inputs(model_name: str, text: str, voice: str) -> dict:
    """Build Omni inputs for Voxtral TTS (voice id), mirroring upstream end2end example."""
    instruct_tok = _get_mistral_tokenizer(model_name).instruct_tokenizer
    tokenized = instruct_tok.encode_speech_request(SpeechRequest(input=text, voice=voice))
    return {
        "additional_information": {"voice": [voice]},
        "prompt_token_ids": tokenized.tokens,
    }


class TTSModel:
    """Wrapper for Voxtral TTS via vLLM-Omni ``Omni``."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.getenv("MODEL_NAME", _DEFAULT_MODEL)
        self.model: Omni | None = None

    def load(self) -> None:
        """Load the TTS model."""
        if self.model is None:
            try:
                os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
                _apply_cache_dir_env()
                _normalize_hf_token_env()
                logger.info(f"Loading model: {self.model_name}")
                self.model = Omni(model=self.model_name)
                logger.info("Model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise

    def generate(self, text: str, voice: str = "fr_female_1", response_format: str = "wav") -> bytes:
        """Generate speech from text; returns WAV bytes (PCM)."""
        if response_format.lower() != "wav":
            raise ValueError(f"Unsupported response_format: {response_format!r} (only 'wav' is supported)")

        if self.model is None:
            self.load()
        assert self.model is not None

        try:
            logger.info(f"Generating TTS for text: '{text[:50]}...' with voice: {voice}")
            inputs = _build_voxtral_inputs(self.model_name, text, voice)
            sp = SamplingParams(max_tokens=2500)
            sampling_params_list = [sp, sp]
            outputs = self.model.generate(inputs, sampling_params_list)
            if not outputs:
                raise RuntimeError("TTS generation returned no outputs")
            mm = outputs[0].multimodal_output
            if not mm or "audio" not in mm:
                raise RuntimeError("TTS output missing multimodal audio")
            audio_tensor = torch.cat(mm["audio"])
            audio_np = audio_tensor.float().detach().cpu().numpy().astype(np.float32).flatten()
            buf = io.BytesIO()
            sf.write(buf, audio_np, _TTS_SAMPLE_RATE_HZ, format="WAV", subtype="PCM_16")
            return buf.getvalue()
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            raise
