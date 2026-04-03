#!/usr/bin/env python3
"""
Experimental WAV -> embedding placeholder for Kokoro-ONNX.

WARNING: this script produces RANDOM 512-D embeddings — it does NOT extract a
real style vector from the audio.  Replace the placeholder logic with an actual
Kokoro/StyleTTS2 encoder when upstream tooling is available.

Writes a single-voice bundle as an NPZ archive (same format as extract_voice.py /
merge_voice_bundles.py): use KOKORO_VOICES_BIN_PATH or merge with the official pack.
"""

from __future__ import annotations

import argparse
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import torchaudio


def _module_dir() -> Path:
    return Path(__file__).resolve().parent


def _repo_root() -> Path:
    return _module_dir().parent


def _voice_bundle_key(name: str) -> str:
    """Normalize a name for np.savez keyword args and Kokoro-style voice ids."""
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", name).strip("_")
    if s and s[0].isdigit():
        s = "v_" + s
    return s or "voice"


def extract_kokoro_embedding(
    wav_path: Path,
    output_path: Path,
    *,
    voice_key: str | None = None,
) -> None:
    print(f"Processing audio: {wav_path}")

    waveform, sample_rate = torchaudio.load(str(wav_path))
    if sample_rate != 24000:
        resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=24000)
        waveform = resampler(waveform)

    warnings.warn(
        "Generating RANDOM 512-D embedding — this is a placeholder, not a real "
        "voice extraction.  The resulting voice will NOT sound like the input audio.",
        stacklevel=2,
    )
    embedding = np.random.randn(512).astype(np.float32)

    key = _voice_bundle_key(voice_key) if voice_key else _voice_bundle_key(wav_path.stem)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        np.savez(f, **{key: embedding})
    print(f"Bundle saved at: {output_path} (voice key: {key})")


def main() -> None:
    mod = _module_dir()
    repo = _repo_root()
    default_wav = mod / "raw_audios" / "nemo_0_FR.wav"
    default_out = repo / "generator" / "voices" / "custom_from_wav.bin"

    parser = argparse.ArgumentParser(
        description="[EXPERIMENTAL] WAV -> Kokoro-compatible .bin bundle (npz). "
        "Embedding is random — replace with a real encoder.",
    )
    parser.add_argument(
        "--wav",
        type=Path,
        default=default_wav,
        help=f"Input WAV (default: {default_wav.relative_to(repo)})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_out,
        help=f"Output bundle path (default: {default_out.relative_to(repo)})",
    )
    parser.add_argument(
        "--voice-key",
        type=str,
        default=None,
        help="Key inside the npz (default: normalized WAV stem)",
    )
    args = parser.parse_args()

    wav = args.wav
    if not wav.is_file():
        print(f"Input file not found: {wav}", file=sys.stderr)
        print("Place a WAV at that path or pass --wav explicitly.", file=sys.stderr)
        raise SystemExit(1)

    extract_kokoro_embedding(
        wav,
        args.output,
        voice_key=args.voice_key,
    )


if __name__ == "__main__":
    main()
