from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List


def list_sessions(path: str) -> Dict[str, Any]:
    data = _load_store(Path(path))
    items = data.get("items", [])
    items.sort(key=lambda item: item.get("start_at", ""), reverse=True)
    return {"items": items, "updated_at": data.get("updated_at")}


def add_session(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    start_at = str(payload.get("start_at") or "")
    end_at = str(payload.get("end_at") or "")
    if not start_at or not end_at:
        return {"error": "start_end_required"}
    store = _load_store(Path(path))
    items = store.get("items", [])
    now = _now()
    item = {
        "id": f"focus_{int(time.time())}_{len(items) + 1}",
        "label": str(payload.get("label") or "Focus"),
        "start_at": start_at,
        "end_at": end_at,
        "duration_sec": int(payload.get("duration_sec") or 0),
        "notes": str(payload.get("notes") or ""),
        "created_at": now,
    }
    items.append(item)
    store["items"] = items
    store["updated_at"] = now
    _save_store(Path(path), store)
    return {"session": item}


def _load_store(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"items": [], "updated_at": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("items", [])
            return data
    except Exception:
        return {"items": [], "updated_at": None}
    return {"items": [], "updated_at": None}


def _save_store(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
