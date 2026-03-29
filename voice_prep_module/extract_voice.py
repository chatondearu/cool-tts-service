#!/usr/bin/env python3
"""
Offline voice preparation for Kokoro + kokoro-onnx.

Kokoro expects *precomputed* style packs (official Hugging Face ``voices/*.pt``).
Those are PyTorch pickles that ``kokoro-onnx`` loads via ``numpy.savez`` bundles
(see upstream ``scripts/fetch_voices.py``). There is no supported path in this
repo to infer new style vectors from arbitrary ``.wav`` alone without upstream
training/extraction tooling.

This script:
- inventories ``.wav`` clips (metadata only) for your records;
- packs every ``.pt`` file found in ``--input-dir`` into a single npz archive
  (``.bin`` / ``.npz`` naming — same format ``kokoro_onnx.Kokoro`` loads with ``numpy.load``);
- writes ``voice_prep_manifest.json`` next to the bundle.

For experimental WAV→embedding (placeholder), see ``extract_voice_from_wav.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _index_wavs(input_dir: Path) -> list[dict]:
    try:
        import soundfile as sf
    except ImportError as e:
        print("Install soundfile to index WAV files: pip install soundfile", file=sys.stderr)
        raise SystemExit(1) from e

    rows: list[dict] = []
    for w in sorted(input_dir.glob("*.wav")):
        info = sf.info(str(w))
        rows.append(
            {
                "path": w.name,
                "samplerate": info.samplerate,
                "channels": info.channels,
                "frames": info.frames,
                "duration_s": round(info.frames / float(info.samplerate), 6),
            }
        )
    return rows


def _pack_pt_files(pt_files: list[Path]) -> dict[str, object]:
    try:
        import numpy as np
        import torch
    except ImportError as e:
        print(
            "Packing .pt requires torch and numpy. "
            "pip install -r voice_prep_module/requirements_prep.txt",
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    voices: dict[str, np.ndarray] = {}
    for p in pt_files:
        name = p.stem
        tensor = torch.load(p, map_location="cpu", weights_only=True)
        arr = tensor.numpy() if hasattr(tensor, "numpy") else np.asarray(tensor)
        voices[name] = np.asarray(arr, dtype=np.float32)
    return voices


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare Kokoro voice artifacts under production_api/voices/",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "raw_audios",
        help="Directory containing .pt (Kokoro voice packs) and/or .wav reference clips",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_repo_root() / "production_api" / "voices",
        help="Where to write the npz bundle and manifest",
    )
    parser.add_argument(
        "--output-bundle",
        type=Path,
        default=None,
        help="Merged voices file (npz). Default: OUTPUT_DIR/custom_voices.bin",
    )
    parser.add_argument(
        "--bundle-name",
        type=str,
        default="custom_voices.bin",
        help="Filename used when --output-bundle is not set",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    if not input_dir.is_dir():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        raise SystemExit(1)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = args.output_bundle or (output_dir / args.bundle_name)

    pt_files = sorted(input_dir.glob("*.pt"))
    wav_files = sorted(input_dir.glob("*.wav"))

    manifest: dict = {
        "version": 1,
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "bundle": None,
        "voice_keys": [],
        "wav_inventory": [],
        "notes": [],
    }

    if wav_files:
        manifest["wav_inventory"] = _index_wavs(input_dir)

    if pt_files:
        voices_obj = _pack_pt_files(pt_files)
        import numpy as np

        voices_dict = {k: voices_obj[k] for k in sorted(voices_obj.keys())}
        with open(bundle_path, "wb") as f:
            np.savez(f, **voices_dict)
        manifest["bundle"] = str(bundle_path)
        manifest["voice_keys"] = list(voices_dict.keys())
        mib = bundle_path.stat().st_size / (1024 * 1024)
        print(f"Wrote bundle {bundle_path} (~{mib:.2f} MiB), voices: {manifest['voice_keys']}")
    else:
        manifest["notes"].append(
            "No .pt files found. Kokoro ONNX needs style packs: download official "
            "`voices/*.pt` from hexgrad/Kokoro-82M (or compatible) into raw_audios, "
            "then re-run this script to produce a npz bundle consumable via "
            "KOKORO_VOICES_BIN_PATH."
        )
        if wav_files:
            print(manifest["notes"][-1])
        else:
            manifest["notes"].append(
                f"No .wav or .pt under {input_dir}. Add reference audio or .pt packs."
            )

    manifest_path = output_dir / "voice_prep_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
