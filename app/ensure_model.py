#!/usr/bin/env python3
"""
Ensure Hugging Face model files exist before uvicorn starts (Docker entrypoint).

Skips Hub when MODEL_NAME is an existing directory (local snapshot, same rule as vllm-omni).
Does not import model.py (avoids loading torch/vllm for this step).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_DEFAULT_MODEL = "mistralai/Voxtral-4B-TTS-2603"


def _apply_cache_dir_env() -> None:
    cache_dir = os.getenv("CACHE_DIR", "").strip()
    if not cache_dir:
        return
    os.makedirs(cache_dir, exist_ok=True)
    os.environ.setdefault("HF_HOME", cache_dir)


def _normalize_hf_token_env() -> None:
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        raw = os.environ.get(key)
        if raw is not None and not raw.strip():
            del os.environ[key]
    hf = os.environ.get("HF_TOKEN", "").strip()
    hub = os.environ.get("HUGGING_FACE_HUB_TOKEN", "").strip()
    if hf and not hub:
        os.environ["HUGGING_FACE_HUB_TOKEN"] = hf
    elif hub and not hf:
        os.environ["HF_TOKEN"] = hub


def _has_weights(snapshot_root: Path) -> bool:
    if not snapshot_root.is_dir():
        return False
    for pattern in ("*.safetensors", "*.bin"):
        if any(snapshot_root.glob(pattern)):
            return True
    if any(snapshot_root.rglob("*.safetensors")) or any(snapshot_root.rglob("*.bin")):
        return True
    return False


def _has_model_metadata(snapshot_root: Path) -> bool:
    """True if the folder looks like a usable HF model snapshot.

    Transformers repos usually have config.json at the root. Voxtral TTS Hub layouts
    (e.g. mistralai/Voxtral-4B-TTS-2603) ship params.json + tekken.json without config.json.
    """
    if (snapshot_root / "config.json").is_file():
        return True
    if (snapshot_root / "params.json").is_file() and (snapshot_root / "tekken.json").is_file():
        return True
    return False


def main() -> int:
    _apply_cache_dir_env()
    _normalize_hf_token_env()

    model_name = os.getenv("MODEL_NAME", _DEFAULT_MODEL).strip()
    if not model_name:
        print("ensure_model: MODEL_NAME is empty", file=sys.stderr)
        return 1

    # Same heuristic as vllm-omni omni_snapshot_download: existing path => no Hub fetch here.
    if os.path.isdir(model_name):
        root = Path(model_name).resolve()
        if _has_model_metadata(root) and _has_weights(root):
            print(f"ensure_model: using local model directory {root}, skip Hub download.")
            return 0
        print(
            "ensure_model: MODEL_NAME is a directory but missing model metadata "
            "(config.json or params.json+tekken.json) or weight files: "
            f"{root}",
            file=sys.stderr,
        )
        return 1

    token = (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or "").strip() or None

    try:
        from huggingface_hub import snapshot_download
    except ImportError as e:
        print(f"ensure_model: huggingface_hub is required: {e}", file=sys.stderr)
        return 1

    try:
        path_str = snapshot_download(
            repo_id=model_name,
            token=token,
            local_files_only=False,
        )
    except Exception as e:
        print(f"ensure_model: snapshot_download failed: {e}", file=sys.stderr)
        if token is None and ("401" in str(e) or "403" in str(e) or "gated" in str(e).lower()):
            print(
                "ensure_model: this repo may require HF_TOKEN / HUGGING_FACE_HUB_TOKEN in .env.",
                file=sys.stderr,
            )
        return 1

    root = Path(path_str)
    if not _has_model_metadata(root):
        print(
            "ensure_model: snapshot missing model metadata under "
            f"{root} (expected config.json or params.json+tekken.json)",
            file=sys.stderr,
        )
        return 1
    if not _has_weights(root):
        print(f"ensure_model: no weight files found under {root}", file=sys.stderr)
        return 1

    print(f"ensure_model: ready at {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
