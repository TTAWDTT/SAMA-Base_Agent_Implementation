# ==============================================================================
# 通知与回调
# ==============================================================================

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import request


def dispatch_notification(
    event: str,
    config: Any,
    context: Dict[str, Any]
) -> None:
    """
    分发通知事件
    """
    if not config or not getattr(config, "enabled", True):
        return

    event_cfg = _get_event_config(config, event)
    if not event_cfg or not getattr(event_cfg, "enabled", True):
        return

    payload_context = dict(context)
    payload_context.setdefault("event", event)
    payload_context.setdefault("timestamp", datetime.now().isoformat())

    message_template = getattr(event_cfg, "message", "") or ""
    message = _render_message(message_template, payload_context)

    if getattr(event_cfg, "sound", False):
        _emit_beep()

    webhook_url = getattr(event_cfg, "webhook_url", None)
    if webhook_url:
        _send_webhook(
            webhook_url,
            message,
            payload_context,
            headers=getattr(event_cfg, "webhook_headers", None),
            timeout=getattr(event_cfg, "webhook_timeout", 5)
        )

    command = getattr(event_cfg, "command", None)
    if command:
        _run_command(command, payload_context)

    output_file = getattr(event_cfg, "write_file", None)
    if output_file:
        _write_notification_file(output_file, message, payload_context)


def _get_event_config(config: Any, event: str) -> Optional[Any]:
    mapping = {
        "success": "on_success",
        "failure": "on_failure",
        "queue_complete": "on_queue_complete",
    }
    attr = mapping.get(event, event)
    return getattr(config, attr, None)


def _render_message(template: str, context: Dict[str, Any]) -> str:
    if not template:
        return ""
    try:
        return template.format_map(_SafeDict(context))
    except Exception:
        return template


def _emit_beep() -> None:
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        return


def _send_webhook(
    url: str,
    message: str,
    context: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 5
) -> None:
    payload = {
        "event": context.get("event"),
        "message": message,
        "context": context,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if headers:
        for key, value in headers.items():
            req.add_header(str(key), str(value))
    try:
        request.urlopen(req, timeout=timeout)
    except Exception:
        return


def _run_command(command: str, context: Dict[str, Any]) -> None:
    try:
        cmd = command.format_map(_SafeDict(context))
    except Exception:
        cmd = command
    try:
        subprocess.Popen(cmd, shell=True)
    except Exception:
        return


def _write_notification_file(path: str, message: str, context: Dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": context.get("timestamp"),
        "event": context.get("event"),
        "message": message,
        "context": context,
    }
    try:
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        return


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
