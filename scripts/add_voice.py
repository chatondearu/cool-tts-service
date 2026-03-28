#!/usr/bin/env python3
"""
Copy a WAV sample into app/voices/custom or app/voices/default.
Run from repository root: python scripts/add_voice.py --name my_voice --sample path/to.wav
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Install a voice sample as a .wav under voices/")
    parser.add_argument("--name", required=True, help="Voice id (output file will be <name>.wav)")
    parser.add_argument("--sample", type=Path, required=True, help="Source WAV file")
    parser.add_argument(
        "--target",
        choices=("custom", "default"),
        default="custom",
        help="Subdirectory under voices/ (default: custom)",
    )
    parser.add_argument(
        "--voices-dir",
        type=Path,
        default=Path("app/voices"),
        help="Root voices directory (default: app/voices)",
    )
    args = parser.parse_args()

    if not args.sample.is_file():
        print(f"Error: sample not found: {args.sample}", file=sys.stderr)
        return 1

    dest_dir = args.voices_dir / args.target
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{args.name}.wav"
    shutil.copy2(args.sample, dest)
    print(f"Installed voice sample: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
