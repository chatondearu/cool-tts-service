#!/usr/bin/env python3
"""
Experimental WAV → embedding placeholder for Kokoro-ONNX.

Writes a single-voice bundle as an NPZ archive (same format as ``extract_voice.py`` /
``merge_voice_bundles.py``): use ``KOKORO_VOICES_BIN_PATH`` or merge with the official
pack. Embeddings are still random until a real encoder is wired in.

np.savez is used with an explicit binary file handle so the output path is honored
exactly (no extra ``.npz`` / ``.npy`` suffix from NumPy).
"""

from __future__ import annotations

import argparse
import re
import sys
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

    print("Generating vocal vector (512D embedding)...")

    # Placeholder for Kokoro's StyleTTS2 encoder logic
    # Replace with: embedding = kokoro_encoder(waveform) when fully implementing the extraction model
    embedding = np.random.randn(512).astype(np.float32)

    key = _voice_bundle_key(voice_key) if voice_key else _voice_bundle_key(wav_path.stem)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as f:
        np.savez(f, **{key: embedding})
    print(f"Success! Bundle saved at: {output_path} (voice key: {key})")


def main() -> None:
    mod = _module_dir()
    repo = _repo_root()
    default_wav = mod / "raw_audios" / "my_target_voice.wav"
    default_out = repo / "production_api" / "voices" / "custom_from_wav.bin"

    parser = argparse.ArgumentParser(
        description="Placeholder WAV → Kokoro-compatible .bin bundle (npz)",
    )
    parser.add_argument(
        "--wav",
        type=Path,
        default=default_wav,
        help=f"Input WAV (default: {default_wav})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_out,
        help=f"Output bundle path (default: {default_out})",
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
