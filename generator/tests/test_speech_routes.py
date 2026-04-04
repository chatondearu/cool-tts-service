"""OpenAI /generate speech routes with fake TTS (no Kokoro model files)."""

from __future__ import annotations

import shutil

import pytest

_SKIP_FFMPEG = not shutil.which("ffmpeg")


def _openai_body(fmt: str) -> dict:
    return {
        "model": "kokoro-v1.0",
        "input": "hello world",
        "voice": "af_test",
        "response_format": fmt,
        "speed": 1.0,
    }


def test_openai_unsupported_response_format_422(client) -> None:
    r = client.post("/v1/audio/speech", json=_openai_body("aac"))
    assert r.status_code == 422


def test_openai_wav_ok(client) -> None:
    r = client.post("/v1/audio/speech", json=_openai_body("wav"))
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("audio/wav")
    assert "speech.wav" in (r.headers.get("content-disposition") or "")
    assert len(r.content) > 100


@pytest.mark.skipif(_SKIP_FFMPEG, reason="ffmpeg not on PATH")
def test_openai_mp3_ok(client) -> None:
    r = client.post("/v1/audio/speech", json=_openai_body("mp3"))
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("audio/mpeg")
    assert "speech.mp3" in (r.headers.get("content-disposition") or "")
    assert len(r.content) > 100


@pytest.mark.skipif(_SKIP_FFMPEG, reason="ffmpeg not on PATH")
def test_openai_opus_ok(client) -> None:
    r = client.post("/v1/audio/speech", json=_openai_body("opus"))
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("audio/ogg")
    assert "speech.opus" in (r.headers.get("content-disposition") or "")
    assert len(r.content) > 50


def test_openai_mp3_503_without_ffmpeg(client_no_ffmpeg) -> None:
    r = client_no_ffmpeg.post("/v1/audio/speech", json=_openai_body("mp3"))
    assert r.status_code == 503


def test_generate_wav_ok(client) -> None:
    r = client.post(
        "/generate",
        json={
            "text": "hi",
            "language": "en-us",
            "voice_id": "af_test",
            "speed": 1.0,
            "response_format": "wav",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("audio/wav")


@pytest.mark.skipif(_SKIP_FFMPEG, reason="ffmpeg not on PATH")
def test_generate_mp3_ok(client) -> None:
    r = client.post(
        "/generate",
        json={
            "text": "hi",
            "language": "en-us",
            "voice_id": "af_test",
            "speed": 1.0,
            "response_format": "mp3",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("audio/mpeg")


def test_generate_invalid_format_422(client) -> None:
    r = client.post(
        "/generate",
        json={
            "text": "hi",
            "language": "en-us",
            "voice_id": "af_test",
            "speed": 1.0,
            "response_format": "aac",
        },
    )
    assert r.status_code == 422
