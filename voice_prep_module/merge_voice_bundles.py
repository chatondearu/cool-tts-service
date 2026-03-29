#!/usr/bin/env python3
"""
Merge two Kokoro voice bundles (numpy npz archives, e.g. voices-v1.0.bin + custom_voices.bin).

Keys from --overlay replace keys with the same name in --base. Use this to keep all
official voices and add or override entries from a custom pack.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def _load_bundle(path: Path) -> dict[str, np.ndarray]:
    data = np.load(path)
    return {k: np.asarray(data[k], dtype=np.float32) for k in data.files}


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge Kokoro npz voice bundles")
    parser.add_argument(
        "--base",
        type=Path,
        required=True,
        help="Primary bundle (e.g. official voices-v1.0.bin)",
    )
    parser.add_argument(
        "--overlay",
        type=Path,
        required=True,
        help="Second bundle; its keys override the same keys in base",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Merged npz path (e.g. production_api/voices/merged_voices.bin)",
    )
    args = parser.parse_args()

    for p in (args.base, args.overlay):
        if not p.is_file():
            print(f"Not a file: {p}", file=sys.stderr)
            raise SystemExit(1)

    base_v = _load_bundle(args.base)
    over_v = _load_bundle(args.overlay)

    collisions = sorted(set(base_v) & set(over_v))
    merged = {**base_v, **over_v}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "wb") as f:
        np.savez(f, **merged)

    meta = {
        "base": str(args.base.resolve()),
        "overlay": str(args.overlay.resolve()),
        "output": str(args.output.resolve()),
        "voice_count": len(merged),
        "keys_overridden": collisions,
        "all_keys": sorted(merged.keys()),
    }
    meta_path = args.output.parent / f"{args.output.name}.merge-meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Wrote {args.output} ({len(merged)} voices)")
    if collisions:
        print(f"Overridden keys ({len(collisions)}): {', '.join(collisions)}")
    print(f"Metadata: {meta_path}")


if __name__ == "__main__":
    main()
