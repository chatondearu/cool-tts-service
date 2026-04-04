"""Shared fixtures: fake TTS engine and patched app bootstrap (no real Kokoro files)."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi import FastAPI
from numpy.typing import NDArray


class FakeKokoroTTS:
    """Minimal stand-in for KokoroTTS (sample_rate, list_voices, generate_audio)."""

    sample_rate = 24_000

    def __init__(self, voices: list[str] | None = None) -> None:
        self._voices = voices or ["af_test"]

    def list_voices(self) -> list[str]:
        return list(self._voices)

    def generate_audio(
        self,
        text: str,
        voice_id: str,
        lang: str,
        speed: float = 1.0,
    ) -> NDArray[np.float32]:
        n = max(240, int(0.15 * self.sample_rate))
        return np.zeros(n, dtype=np.float32)


@pytest.fixture
def ffmpeg_available() -> bool:
    import shutil

    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, ffmpeg_available: bool):
    import main as main_mod

    async def fake_bootstrap(app: FastAPI) -> None:
        app.state.tts = FakeKokoroTTS()
        app.state.tts_error = None
        app.state.ffmpeg_available = ffmpeg_available

    monkeypatch.setattr(main_mod, "_bootstrap_and_load", fake_bootstrap)

    from fastapi.testclient import TestClient

    with TestClient(main_mod.app) as c:
        yield c


@pytest.fixture
def client_no_ffmpeg(monkeypatch: pytest.MonkeyPatch):
    import main as main_mod

    async def fake_bootstrap(app: FastAPI) -> None:
        app.state.tts = FakeKokoroTTS()
        app.state.tts_error = None
        app.state.ffmpeg_available = False

    monkeypatch.setattr(main_mod, "_bootstrap_and_load", fake_bootstrap)

    from fastapi.testclient import TestClient

    with TestClient(main_mod.app) as c:
        yield c
