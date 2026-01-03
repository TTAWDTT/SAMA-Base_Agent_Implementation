from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def list_artifact_tags(path: str) -> Dict[str, Any]:
    data = _load_store(Path(path))
    return {"items": data.get("items", {}), "updated_at": data.get("updated_at")}


def update_artifact_tags(path: str, task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not task_id:
        return {"error": "task_id_required"}
    store = _load_store(Path(path))
    items = store.get("items", {})
    items[task_id] = {
        "tags": list(payload.get("tags") or []),
        "notes": str(payload.get("notes") or ""),
        "updated_at": payload.get("updated_at") or _now(),
    }
    store["items"] = items
    store["updated_at"] = _now()
    _save_store(Path(path), store)
    return {"item": items[task_id]}


def remove_artifact_tags(path: str, task_id: str) -> Dict[str, Any]:
    store = _load_store(Path(path))
    items = store.get("items", {})
    if task_id not in items:
        return {"error": "not_found"}
    items.pop(task_id, None)
    store["items"] = items
    store["updated_at"] = _now()
    _save_store(Path(path), store)
    return {"removed": True}


def _load_store(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"items": {}, "updated_at": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("items", {})
            return data
    except Exception:
        return {"items": {}, "updated_at": None}
    return {"items": {}, "updated_at": None}


def _save_store(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S")
