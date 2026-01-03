from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def list_tasks(path: str) -> Dict[str, Any]:
    data = _load_board(Path(path))
    tasks = data.get("tasks", [])
    tasks.sort(key=_task_sort_key, reverse=False)
    return {"tasks": tasks, "updated_at": data.get("updated_at")}


def add_task(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    if not title:
        return {"error": "title_required"}
    board = _load_board(Path(path))
    tasks = board.get("tasks", [])
    now = _now()
    task_id = f"task_{int(time.time())}_{len(tasks) + 1}"
    task = {
        "id": task_id,
        "title": title,
        "project": str(payload.get("project") or ""),
        "status": str(payload.get("status") or "todo"),
        "priority": str(payload.get("priority") or "P2"),
        "tags": list(payload.get("tags") or []),
        "due": payload.get("due"),
        "notes": str(payload.get("notes") or ""),
        "links": list(payload.get("links") or []),
        "order": payload.get("order", (len(tasks) + 1) * 1000),
        "created_at": now,
        "updated_at": now,
        "history": [{"at": now, "action": "created"}],
        "archived": False,
    }
    tasks.append(task)
    board["tasks"] = tasks
    board["updated_at"] = now
    _save_board(Path(path), board)
    return {"task": task}


def update_task(path: str, task_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    board = _load_board(Path(path))
    tasks = board.get("tasks", [])
    now = _now()
    updated = None
    for task in tasks:
        if task.get("id") != task_id:
            continue
        for key in ["title", "project", "status", "priority", "tags", "due", "notes", "links", "archived", "order"]:
            if key in updates:
                task[key] = updates[key]
        task["updated_at"] = now
        task.setdefault("history", []).append({"at": now, "action": "updated"})
        updated = task
        break
    if updated is None:
        return {"error": "task_not_found"}
    board["updated_at"] = now
    _save_board(Path(path), board)
    return {"task": updated}


def remove_task(path: str, task_id: str) -> Dict[str, Any]:
    board = _load_board(Path(path))
    tasks = board.get("tasks", [])
    remaining = [task for task in tasks if task.get("id") != task_id]
    if len(remaining) == len(tasks):
        return {"error": "task_not_found"}
    board["tasks"] = remaining
    board["updated_at"] = _now()
    _save_board(Path(path), board)
    return {"removed": True}


def build_task_stats(path: str) -> Dict[str, Any]:
    data = _load_board(Path(path))
    tasks = data.get("tasks", [])
    counts = {"todo": 0, "doing": 0, "done": 0, "blocked": 0}
    priorities: Dict[str, int] = {}
    tags: Dict[str, int] = {}
    for task in tasks:
        status = str(task.get("status") or "todo").lower()
        counts[status] = counts.get(status, 0) + 1
        priority = str(task.get("priority") or "P2").upper()
        priorities[priority] = priorities.get(priority, 0) + 1
        for tag in task.get("tags") or []:
            tags[str(tag)] = tags.get(str(tag), 0) + 1
    return {
        "counts": counts,
        "priorities": _sort_counter(priorities),
        "tags": _sort_counter(tags),
        "total": len(tasks),
    }


def _load_board(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"tasks": [], "updated_at": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("tasks", [])
            return data
    except Exception:
        return {"tasks": [], "updated_at": None}
    return {"tasks": [], "updated_at": None}


def _save_board(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _task_sort_key(task: Dict[str, Any]) -> str:
    status_order = {"doing": "0", "todo": "1", "blocked": "2", "done": "3"}
    priority = str(task.get("priority") or "P2").upper()
    priority_order = {"P0": "0", "P1": "1", "P2": "2", "P3": "3"}
    status = str(task.get("status") or "todo").lower()
    due = str(task.get("due") or "")
    order_value = task.get("order")
    order_key = "999999999999"
    try:
        order_num = float(order_value)
        order_key = f"{order_num:012.4f}"
    except (TypeError, ValueError):
        order_key = "999999999999"
    return f"{status_order.get(status,'9')}-{order_key}-{priority_order.get(priority,'9')}-{due}-{task.get('updated_at','')}"


def _sort_counter(counter: Dict[str, int]) -> List[Dict[str, Any]]:
    return [
        {"label": label, "count": count}
        for label, count in sorted(counter.items(), key=lambda item: item[1], reverse=True)
    ]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
