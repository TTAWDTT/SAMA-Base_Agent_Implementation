# ==============================================================================
# 任务队列
# ==============================================================================

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils import generate_request_id


def _now() -> str:
    return datetime.now().isoformat()


@dataclass
class QueueItem:
    task_id: str
    prompt: str
    reference_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    attempts: int = 0
    max_retries: int = 1
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    last_error: Optional[str] = None
    output_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "reference_files": list(self.reference_files),
            "metadata": self.metadata,
            "status": self.status,
            "attempts": self.attempts,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_error": self.last_error,
            "output_dir": self.output_dir,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueItem":
        return cls(
            task_id=str(data.get("task_id") or generate_request_id()),
            prompt=str(data.get("prompt") or ""),
            reference_files=list(data.get("reference_files") or []),
            metadata=dict(data.get("metadata") or {}),
            status=data.get("status", "pending"),
            attempts=int(data.get("attempts", 0) or 0),
            max_retries=int(data.get("max_retries", 1) or 1),
            created_at=str(data.get("created_at") or _now()),
            updated_at=str(data.get("updated_at") or _now()),
            last_error=data.get("last_error"),
            output_dir=data.get("output_dir"),
        )


class TaskQueue:
    def __init__(self, path: str = "outputs/task_queue.json", auto_resume: bool = True) -> None:
        self.path = Path(path)
        self.auto_resume = auto_resume
        self.tasks: List[QueueItem] = []
        self.version = 1
        self.updated_at = _now()
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        tasks = data.get("tasks", [])
        if isinstance(tasks, list):
            self.tasks = [QueueItem.from_dict(item) for item in tasks if isinstance(item, dict)]
        self.version = int(data.get("version", 1) or 1)
        self.updated_at = str(data.get("updated_at") or _now())
        if self.auto_resume:
            self.recover_incomplete()

    def save(self) -> None:
        self.updated_at = _now()
        payload = {
            "version": self.version,
            "updated_at": self.updated_at,
            "tasks": [task.to_dict() for task in self.tasks],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def recover_incomplete(self) -> None:
        changed = False
        for task in self.tasks:
            if task.status == "running":
                task.status = "pending"
                task.updated_at = _now()
                changed = True
        if changed:
            self.save()

    def add_task(
        self,
        prompt: str,
        reference_files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        max_retries: Optional[int] = None
    ) -> QueueItem:
        item = QueueItem(
            task_id=task_id or generate_request_id(),
            prompt=prompt,
            reference_files=list(reference_files or []),
            metadata=dict(metadata or {}),
            max_retries=max_retries if max_retries is not None else 1,
        )
        self.tasks.append(item)
        self.save()
        return item

    def add_items(self, items: List[QueueItem]) -> None:
        self.tasks.extend(items)
        self.save()

    def list_tasks(self, status: Optional[str] = None) -> List[QueueItem]:
        if not status:
            return list(self.tasks)
        return [task for task in self.tasks if task.status == status]

    def get_next_pending(self) -> Optional[QueueItem]:
        for task in self.tasks:
            if task.status == "pending":
                return task
        return None

    def update_status(
        self,
        task_id: str,
        status: str,
        error: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> None:
        task = self._find_task(task_id)
        if not task:
            return
        task.status = status
        task.updated_at = _now()
        if error:
            task.last_error = error
        if output_dir:
            task.output_dir = output_dir
        self.save()

    def mark_running(self, task_id: str) -> None:
        task = self._find_task(task_id)
        if not task:
            return
        task.status = "running"
        task.attempts += 1
        task.updated_at = _now()
        self.save()

    def mark_completed(self, task_id: str, output_dir: Optional[str] = None) -> None:
        self.update_status(task_id, "completed", output_dir=output_dir)

    def mark_failed(self, task_id: str, error: Optional[str] = None) -> None:
        self.update_status(task_id, "failed", error=error)

    def retry_failed(self, max_retries: Optional[int] = None) -> int:
        changed = 0
        for task in self.tasks:
            limit = max_retries if max_retries is not None else task.max_retries
            if task.status == "failed" and task.attempts <= limit:
                task.status = "pending"
                task.updated_at = _now()
                changed += 1
        if changed:
            self.save()
        return changed

    def remove_task(self, task_id: str) -> bool:
        for idx, task in enumerate(self.tasks):
            if task.task_id == task_id:
                del self.tasks[idx]
                self.save()
                return True
        return False

    def clear(self, status: Optional[str] = None) -> int:
        if not status:
            count = len(self.tasks)
            self.tasks = []
            self.save()
            return count
        kept = [task for task in self.tasks if task.status != status]
        removed = len(self.tasks) - len(kept)
        self.tasks = kept
        if removed:
            self.save()
        return removed

    def summary(self) -> Dict[str, int]:
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "skipped": 0}
        for task in self.tasks:
            counts[task.status] = counts.get(task.status, 0) + 1
        return counts

    def _find_task(self, task_id: str) -> Optional[QueueItem]:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
