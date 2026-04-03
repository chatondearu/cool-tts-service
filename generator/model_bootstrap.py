"""Optional download of official Kokoro ONNX + voices bundle on first start."""

from __future__ import annotations

import logging
import os
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger("cool-tts")

_RELEASE_TAG = "model-files-v1.0"
_BASE_URL = f"https://github.com/thewh1teagle/kokoro-onnx/releases/download/{_RELEASE_TAG}"

_ONNX_BY_VARIANT: dict[str, str] = {
    "f32": "kokoro-v1.0.onnx",
    "int8": "kokoro-v1.0.int8.onnx",
    "fp16": "kokoro-v1.0.fp16.onnx",
}

_VOICES_ASSET = "voices-v1.0.bin"


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _onnx_remote_name() -> str:
    variant = os.environ.get("KOKORO_ONNX_VARIANT", "f32").strip().lower()
    return _ONNX_BY_VARIANT.get(variant, _ONNX_BY_VARIANT["f32"])


def _dir_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".cool_tts_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _download_file(url: str, dest: Path, chunk_size: int = 8 * 1024 * 1024) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "cool-tts-service/1.0"})
        with urllib.request.urlopen(request, timeout=600) as response:
            with open(tmp, "wb") as out:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out.write(chunk)
        tmp.replace(dest)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError):
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise


def ensure_kokoro_files(model_path: Path, voices_bin_path: Path) -> tuple[bool, str | None]:
    """
    If KOKORO_AUTO_DOWNLOAD is set and files are missing, try to download from
    kokoro-onnx GitHub releases. Parent directories must be writable.

    Returns (True, None) on success or when nothing to do; (False, message) on failure.
    """
    if not _env_truthy("KOKORO_AUTO_DOWNLOAD"):
        return True, None

    model_path = model_path.resolve()
    voices_bin_path = voices_bin_path.resolve()
    need_onnx = not model_path.is_file()
    need_voices = not voices_bin_path.is_file()
    if not need_onnx and not need_voices:
        return True, None

    errors: list[str] = []

    if need_onnx:
        if not _dir_writable(model_path.parent):
            errors.append(
                f"Cannot download ONNX: directory not writable ({model_path.parent}). "
                "Use a read-write volume or place the file manually.",
            )
        else:
            remote = _onnx_remote_name()
            url = f"{_BASE_URL}/{remote}"
            try:
                logger.info("Auto-download ONNX from %s -> %s", url, model_path)
                _download_file(url, model_path)
            except Exception as exc:  # noqa: BLE001 — surface any network/fs error
                errors.append(f"ONNX download failed: {exc}")

    if need_voices:
        if not _dir_writable(voices_bin_path.parent):
            errors.append(
                f"Cannot download voices bundle: directory not writable ({voices_bin_path.parent}).",
            )
        else:
            url = f"{_BASE_URL}/{_VOICES_ASSET}"
            try:
                logger.info("Auto-download voices from %s -> %s", url, voices_bin_path)
                _download_file(url, voices_bin_path)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Voices download failed: {exc}")

    if errors:
        return False, "; ".join(errors)
    return True, None
