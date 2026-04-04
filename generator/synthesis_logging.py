"""Structured synthesis logs: JSON lines to stdout and in-memory ring buffer for admin UI."""

from __future__ import annotations

import json
import logging
import os
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

from starlette.requests import Request

SYNTHESIS_LOGGER = logging.getLogger("cool-tts")

DEBUG_LOG_TEXT_HEADER = "X-Cool-TTS-Debug-Log-Text"
MAX_USER_AGENT_LEN = 200
_DEFAULT_BUFFER_MAX = 500

_LOG_BUFFER: deque[dict[str, Any]] = deque(
    maxlen=int(os.environ.get("TTS_SYNTHESIS_LOG_BUFFER_MAX", _DEFAULT_BUFFER_MAX)),
)
_LOG_LOCK = threading.Lock()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host or ""
    return ""


def truncated_user_agent(request: Request) -> str:
    ua = request.headers.get("user-agent") or ""
    if len(ua) <= MAX_USER_AGENT_LEN:
        return ua
    return ua[: MAX_USER_AGENT_LEN - 3] + "..."


def debug_log_full_text_enabled(request: Request) -> bool:
    v = (request.headers.get(DEBUG_LOG_TEXT_HEADER) or "").strip().lower()
    return v in ("1", "true", "yes")


def http_error_message(detail: Any) -> str:
    if isinstance(detail, str):
        return detail[:4000]
    try:
        return json.dumps(detail, ensure_ascii=False)[:4000]
    except (TypeError, ValueError):
        return str(detail)[:4000]


def build_synthesis_payload(
    *,
    request_id: str,
    route: str,
    request: Request,
    voice_id: str,
    language: str,
    speed: float,
    text: str,
    status_code: int,
    duration_ms: int,
    error: Optional[str] = None,
    wav_bytes: Optional[int] = None,
    response_format: Optional[str] = None,
) -> dict[str, Any]:
    debug = debug_log_full_text_enabled(request)
    text_chars = len(text)
    payload: dict[str, Any] = {
        "event": "synthesis",
        "timestamp": _utc_iso(),
        "request_id": request_id,
        "route": route,
        "client_ip": client_ip(request),
        "user_agent": truncated_user_agent(request),
        "voice_id": voice_id,
        "language": language,
        "speed": speed,
        "text_chars": text_chars,
        "debug_text_logged": debug,
        "status_code": status_code,
        "duration_ms": duration_ms,
    }
    if debug:
        payload["input_text"] = text
    if error is not None:
        payload["error"] = error
    if wav_bytes is not None:
        payload["wav_bytes"] = wav_bytes
    if response_format is not None:
        payload["response_format"] = response_format
    return payload


def emit_synthesis_event(payload: dict[str, Any]) -> None:
    """Emit one JSON log line and append a copy to the ring buffer."""
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    code = int(payload.get("status_code", 200))
    if code >= 500:
        SYNTHESIS_LOGGER.error("%s", line)
    elif code >= 400:
        SYNTHESIS_LOGGER.warning("%s", line)
    else:
        SYNTHESIS_LOGGER.info("%s", line)
    store = dict(payload)
    with _LOG_LOCK:
        _LOG_BUFFER.append(store)


def query_synthesis_logs(
    *,
    limit: int,
    errors_only: bool,
    client_substring: str,
    route_filter: Optional[str],
) -> list[dict[str, Any]]:
    """Return newest-first log entries matching filters (copy of buffered dicts)."""
    needle = client_substring.strip().lower()
    with _LOG_LOCK:
        items = list(_LOG_BUFFER)
    items.reverse()
    out: list[dict[str, Any]] = []
    for entry in items:
        if errors_only and int(entry.get("status_code", 200)) < 400:
            continue
        if route_filter and entry.get("route") != route_filter:
            continue
        if needle:
            ip = str(entry.get("client_ip", "")).lower()
            ua = str(entry.get("user_agent", "")).lower()
            if needle not in ip and needle not in ua:
                continue
        out.append(dict(entry))
        if len(out) >= limit:
            break
    return out


def buffer_capacity() -> int:
    return _LOG_BUFFER.maxlen or _DEFAULT_BUFFER_MAX
