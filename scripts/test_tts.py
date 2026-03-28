#!/usr/bin/env python3
"""
Smoke-test the TTS HTTP API (health, voices list, POST /tts).
Run from anywhere: python scripts/test_tts.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for cool-tts-service HTTP API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Server base URL")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("output.wav"),
        help="Where to write synthesized audio (default: output.wav)",
    )
    parser.add_argument(
        "--text",
        default="Bonjour, ceci est un test de synthèse vocale.",
        help="Text sent to POST /tts",
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="Voice id (default: first from GET /voices, or fr_female_1)",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    try:
        with urllib.request.urlopen(f"{base}/health", timeout=30) as r:
            if r.status != 200:
                print(f"Unexpected /health status: {r.status}", file=sys.stderr)
                return 1
            body = json.loads(r.read().decode())
        print("/health:", body)

        with urllib.request.urlopen(f"{base}/voices", timeout=30) as r:
            if r.status != 200:
                print(f"Unexpected /voices status: {r.status}", file=sys.stderr)
                return 1
            voices = json.loads(r.read().decode()).get("voices", [])
        print("/voices:", voices)

        voice = args.voice or (voices[0] if voices else "fr_female_1")
        payload = json.dumps({"text": args.text, "voice": voice}).encode("utf-8")
        req = urllib.request.Request(
            f"{base}/tts",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as r:
            if r.status != 200:
                print(f"Unexpected /tts status: {r.status}", file=sys.stderr)
                return 1
            data = r.read()
        args.output.write_bytes(data)
        print(f"Wrote {args.output} ({len(data)} bytes), voice={voice!r}")
    except urllib.error.HTTPError as e:
        print(f"HTTP error: {e.code} {e.reason}", file=sys.stderr)
        if e.fp:
            print(e.fp.read().decode(errors="replace"), file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
