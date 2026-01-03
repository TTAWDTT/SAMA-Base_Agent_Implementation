from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def list_reminders(path: str) -> Dict[str, Any]:
    data = _load_store(Path(path))
    reminders = data.get("items", [])
    reminders.sort(key=lambda item: item.get("due") or "", reverse=False)
    return {"items": reminders, "updated_at": data.get("updated_at")}


def add_reminder(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    due = str(payload.get("due") or "").strip()
    if not title or not due:
        return {"error": "title_due_required"}
    store = _load_store(Path(path))
    items = store.get("items", [])
    now = _now()
    item = {
        "id": f"rem_{int(time.time())}_{len(items) + 1}",
        "title": title,
        "due": due,
        "notes": str(payload.get("notes") or ""),
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    items.append(item)
    store["items"] = items
    store["updated_at"] = now
    _save_store(Path(path), store)
    return {"reminder": item}


def update_reminder(path: str, reminder_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    store = _load_store(Path(path))
    items = store.get("items", [])
    now = _now()
    updated = None
    for item in items:
        if item.get("id") != reminder_id:
            continue
        for key in ["title", "due", "notes", "status"]:
            if key in updates:
                item[key] = updates[key]
        if item.get("status") == "done" and not item.get("completed_at"):
            item["completed_at"] = now
        item["updated_at"] = now
        updated = item
        break
    if updated is None:
        return {"error": "reminder_not_found"}
    store["items"] = items
    store["updated_at"] = now
    _save_store(Path(path), store)
    return {"reminder": updated}


def remove_reminder(path: str, reminder_id: str) -> Dict[str, Any]:
    store = _load_store(Path(path))
    items = store.get("items", [])
    remaining = [item for item in items if item.get("id") != reminder_id]
    if len(remaining) == len(items):
        return {"error": "reminder_not_found"}
    store["items"] = remaining
    store["updated_at"] = _now()
    _save_store(Path(path), store)
    return {"removed": True}


def mark_reminder_fired(path: str, reminder_id: str) -> Optional[Dict[str, Any]]:
    store = _load_store(Path(path))
    items = store.get("items", [])
    now = _now()
    for item in items:
        if item.get("id") == reminder_id:
            item["status"] = "fired"
            item["updated_at"] = now
            store["updated_at"] = now
            _save_store(Path(path), store)
            return item
    return None


def append_reminder_log(path: str, entry: Dict[str, Any]) -> None:
    record = dict(entry)
    record.setdefault("timestamp", _now())
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_reminder_logs(path: str, limit: int = 80) -> List[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    if limit > 0:
        lines = lines[-limit:]
    items = []
    for line in lines:
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            items.append({"raw": line})
    return items


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
