"""Transcode Kokoro WAV output to mp3/opus via ffmpeg (stdin/stdout)."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Literal

ResponseFormat = Literal["wav", "mp3", "opus"]
ENCODED_FORMATS: frozenset[str] = frozenset({"mp3", "opus"})
SPEECH_RESPONSE_FORMATS: frozenset[str] = frozenset({"wav", "mp3", "opus"})


class AudioEncodeError(Exception):
    """Raised when ffmpeg fails or returns no output."""

    def __init__(self, message: str, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr


@dataclass(frozen=True)
class EncodedAudio:
    data: bytes
    media_type: str
    filename: str


def ffmpeg_on_path() -> bool:
    return shutil.which("ffmpeg") is not None


def _transcode_timeout_seconds(wav_byte_len: int) -> float:
    # Rough upper bound from WAV size (PCM16 mono @ 24kHz ≈ 48000 B/s).
    estimated_sec = max(1.0, wav_byte_len / 48_000.0)
    return min(300.0, max(15.0, estimated_sec * 4.0 + 10.0))


def transcode_wav(wav_bytes: bytes, fmt: Literal["mp3", "opus"]) -> EncodedAudio:
    """
    Encode mono WAV bytes (any sample rate ffmpeg understands) to mp3 or opus.

    - mp3: 44.1 kHz mono, libmp3lame VBR ~q:a 4
    - opus: 48 kHz mono in Ogg (libopus), 64 kb/s
    """
    if fmt == "mp3":
        args = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "wav",
            "-i",
            "pipe:0",
            "-ar",
            "44100",
            "-ac",
            "1",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "4",
            "-f",
            "mp3",
            "pipe:1",
        ]
        media_type = "audio/mpeg"
        filename = "speech.mp3"
    elif fmt == "opus":
        args = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "wav",
            "-i",
            "pipe:0",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-c:a",
            "libopus",
            "-b:a",
            "64k",
            "-f",
            "opus",
            "pipe:1",
        ]
        media_type = "audio/ogg"
        filename = "speech.opus"
    else:
        raise ValueError(f"unsupported encode format: {fmt!r}")

    timeout = _transcode_timeout_seconds(len(wav_bytes))
    try:
        proc = subprocess.run(
            args,
            input=wav_bytes,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioEncodeError("ffmpeg transcoding timed out") from exc
    except FileNotFoundError as exc:
        raise AudioEncodeError("ffmpeg executable not found") from exc

    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise AudioEncodeError(f"ffmpeg exited with code {proc.returncode}", stderr=err)

    out = proc.stdout or b""
    if not out:
        raise AudioEncodeError("ffmpeg produced empty output")

    return EncodedAudio(data=out, media_type=media_type, filename=filename)
