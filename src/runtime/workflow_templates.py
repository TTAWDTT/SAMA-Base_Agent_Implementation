from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def list_templates(path: str) -> Dict[str, Any]:
    data = _load_store(Path(path))
    items = data.get("items", [])
    items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return {"items": items, "updated_at": data.get("updated_at")}


def add_template(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    spec = payload.get("spec")
    if not title or not isinstance(spec, dict):
        return {"error": "title_spec_required"}
    store = _load_store(Path(path))
    items = store.get("items", [])
    now = _now()
    template_id = f"wf_{int(time.time())}_{len(items) + 1}"
    item = {
        "id": template_id,
        "title": title,
        "spec": spec,
        "tags": list(payload.get("tags") or []),
        "created_at": now,
        "updated_at": now,
    }
    items.append(item)
    store["items"] = items
    store["updated_at"] = now
    _save_store(Path(path), store)
    return {"template": item}


def update_template(path: str, template_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    store = _load_store(Path(path))
    items = store.get("items", [])
    updated = None
    for item in items:
        if item.get("id") != template_id:
            continue
        for key in ["title", "spec", "tags"]:
            if key in updates:
                item[key] = updates[key]
        item["updated_at"] = _now()
        updated = item
        break
    if updated is None:
        return {"error": "template_not_found"}
    store["items"] = items
    store["updated_at"] = _now()
    _save_store(Path(path), store)
    return {"template": updated}


def remove_template(path: str, template_id: str) -> Dict[str, Any]:
    store = _load_store(Path(path))
    items = store.get("items", [])
    remaining = [item for item in items if item.get("id") != template_id]
    if len(remaining) == len(items):
        return {"error": "template_not_found"}
    store["items"] = remaining
    store["updated_at"] = _now()
    _save_store(Path(path), store)
    return {"removed": True}


def save_template_spec(base_dir: str, template: Dict[str, Any]) -> Optional[str]:
    spec = template.get("spec")
    if not isinstance(spec, dict):
        return None
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    template_id = template.get("id") or f"wf_{int(time.time())}"
    path = base / f"{template_id}.json"
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


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
