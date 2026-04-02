"""Kokoro ONNX TTS engine: thin wrapper for modular swap later."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
from kokoro_onnx import Kokoro
from numpy.typing import NDArray

PathLike = Union[str, Path]

KOKORO_SAMPLE_RATE = 24_000


class KokoroTTS:
    """Load Kokoro ONNX + voices bundle once; generate float32 PCM as numpy."""

    def __init__(
        self,
        model_path: PathLike,
        voices_bin_path: PathLike,
    ) -> None:
        self._model_path = Path(model_path)
        self._voices_bin_path = Path(voices_bin_path)
        if not self._model_path.is_file():
            raise FileNotFoundError(f"ONNX model not found: {self._model_path}")
        if not self._voices_bin_path.is_file():
            raise FileNotFoundError(f"Voices bundle not found: {self._voices_bin_path}")

        self._kokoro = Kokoro(
            str(self._model_path),
            str(self._voices_bin_path),
        )

    @property
    def sample_rate(self) -> int:
        return KOKORO_SAMPLE_RATE

    def list_voices(self) -> list[str]:
        """Return sorted list of available voice ids from the loaded bundle."""
        return sorted(self._kokoro.get_voices())

    def generate_audio(
        self,
        text: str,
        voice_id: str,
        lang: str,
        speed: float = 1.0,
    ) -> NDArray[np.float32]:
        """
        Synthesize speech for *text* using bundled voice *voice_id*
        (e.g. ``af_sarah``) and *lang* (e.g. ``en-us``, ``fr-fr``).

        Returns a 1-D float32 numpy array (mono samples at 24 kHz).
        """
        samples, _sr = self._kokoro.create(
            text,
            voice=voice_id,
            speed=speed,
            lang=lang,
        )
        return np.asarray(samples, dtype=np.float32)
