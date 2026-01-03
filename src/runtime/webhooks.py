from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request


def send_webhook(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 6
) -> Dict[str, Any]:
    if not url:
        return {"success": False, "error": "url_required"}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if headers:
        for key, value in headers.items():
            req.add_header(str(key), str(value))
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return {"success": True, "status": resp.status, "response": body}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def append_webhook_log(path: str, entry: Dict[str, Any]) -> None:
    record = dict(entry)
    record.setdefault("timestamp", datetime.now().isoformat())
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_webhook_logs(path: str, limit: int = 80) -> List[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    if limit > 0:
        lines = lines[-limit:]
    entries = []
    for line in lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except Exception:
            data = {"raw": line}
        entries.append(data)
    return entries


def clear_webhook_logs(path: str) -> bool:
    file_path = Path(path)
    if not file_path.exists():
        return True
    try:
        file_path.write_text("", encoding="utf-8")
        return True
    except Exception:
        return False
