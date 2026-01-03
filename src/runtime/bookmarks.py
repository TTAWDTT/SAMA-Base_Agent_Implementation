from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List


def list_bookmarks(path: str) -> Dict[str, Any]:
    data = _load_store(Path(path))
    items = data.get("items", [])
    items.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {"items": items, "updated_at": data.get("updated_at")}


def add_bookmark(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    url = str(payload.get("url") or "").strip()
    if not title or not url:
        return {"error": "title_url_required"}
    store = _load_store(Path(path))
    items = store.get("items", [])
    now = _now()
    item = {
        "id": f"bm_{int(time.time())}_{len(items) + 1}",
        "title": title,
        "url": url,
        "source": str(payload.get("source") or ""),
        "tags": list(payload.get("tags") or []),
        "notes": str(payload.get("notes") or ""),
        "pinned": bool(payload.get("pinned", False)),
        "created_at": now,
        "updated_at": now,
    }
    items.append(item)
    store["items"] = items
    store["updated_at"] = now
    _save_store(Path(path), store)
    return {"item": item}


def update_bookmark(path: str, item_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    store = _load_store(Path(path))
    items = store.get("items", [])
    updated = None
    for item in items:
        if item.get("id") != item_id:
            continue
        for key in ["title", "url", "source", "tags", "notes", "pinned"]:
            if key in updates:
                item[key] = updates[key]
        item["updated_at"] = _now()
        updated = item
        break
    if updated is None:
        return {"error": "bookmark_not_found"}
    store["items"] = items
    store["updated_at"] = _now()
    _save_store(Path(path), store)
    return {"item": updated}


def remove_bookmark(path: str, item_id: str) -> Dict[str, Any]:
    store = _load_store(Path(path))
    items = store.get("items", [])
    remaining = [item for item in items if item.get("id") != item_id]
    if len(remaining) == len(items):
        return {"error": "bookmark_not_found"}
    store["items"] = remaining
    store["updated_at"] = _now()
    _save_store(Path(path), store)
    return {"removed": True}


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
