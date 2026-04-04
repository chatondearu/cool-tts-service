"""ffmpeg transcoding: sample rates for mp3 (44.1 kHz) and opus (48 kHz)."""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile

import numpy as np
import pytest
import soundfile as sf

import audio_encode

_SKIP_FFMPEG = not (shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _minimal_wav_bytes() -> bytes:
    sr = 24_000
    samples = np.zeros(int(0.2 * sr), dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _ffprobe_sample_rate(path: str) -> int:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        text=True,
    )
    return int(out.strip())


@pytest.mark.skipif(_SKIP_FFMPEG, reason="ffmpeg or ffprobe not on PATH")
def test_transcode_mp3_sample_rate_44100() -> None:
    wav = _minimal_wav_bytes()
    enc = audio_encode.transcode_wav(wav, "mp3")
    assert enc.media_type == "audio/mpeg"
    assert enc.filename == "speech.mp3"
    assert len(enc.data) > 100
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(enc.data)
        path = tmp.name
    try:
        assert _ffprobe_sample_rate(path) == 44_100
    finally:
        import os

        os.unlink(path)


@pytest.mark.skipif(_SKIP_FFMPEG, reason="ffmpeg or ffprobe not on PATH")
def test_transcode_opus_sample_rate_48000() -> None:
    wav = _minimal_wav_bytes()
    enc = audio_encode.transcode_wav(wav, "opus")
    assert enc.media_type == "audio/ogg"
    assert enc.filename == "speech.opus"
    assert len(enc.data) > 50
    with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as tmp:
        tmp.write(enc.data)
        path = tmp.name
    try:
        assert _ffprobe_sample_rate(path) == 48_000
    finally:
        import os

        os.unlink(path)
