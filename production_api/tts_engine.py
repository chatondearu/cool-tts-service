"""Kokoro ONNX TTS engine: thin wrapper for modular swap later."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np
from numpy.typing import NDArray
from kokoro_onnx import Kokoro

PathLike = Union[str, Path]


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

        # Kokoro loads the graph and voice table at construction time.
        self._kokoro = Kokoro(
            str(self._model_path),
            str(self._voices_bin_path),
        )
        self._sample_rate: int | None = None

    @property
    def sample_rate(self) -> int:
        if self._sample_rate is None:
            raise RuntimeError("Call generate_audio first to set sample_rate.")
        return self._sample_rate

    def generate_audio(
        self,
        text: str,
        voice_id: str,
        lang: str,
        speed: float = 1.0,
    ) -> NDArray[np.float32]:
        """
        Synthesize speech for ``text`` using bundled voice name ``voice_id``
        (e.g. ``af_sarah``) and ``lang`` (e.g. ``en-us``, ``fr-fr`` per Kokoro docs).

        Returns a 1-D float32 numpy array (mono samples). Use ``sample_rate`` after call.
        """
        samples, sr = self._kokoro.create(
            text,
            voice=voice_id,
            speed=speed,
            lang=lang,
        )
        self._sample_rate = int(sr)
        return np.asarray(samples, dtype=np.float32)
