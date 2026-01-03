# ==============================================================================
# 本地调度器
# ==============================================================================

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.core.logger import get_logger
from src.utils.helpers import generate_request_id

logger = get_logger("runtime.scheduler")


def _now() -> str:
    return datetime.now().isoformat()


def _parse_time(value: Optional[Any]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
    return None


def _format_time(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    return value.isoformat()


@dataclass
class ScheduleItem:
    schedule_id: str
    prompt: str
    run_at: Optional[str] = None
    interval_seconds: Optional[int] = None
    session_id: Optional[str] = None
    status: str = "pending"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "prompt": self.prompt,
            "run_at": self.run_at,
            "interval_seconds": self.interval_seconds,
            "session_id": self.session_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduleItem":
        return cls(
            schedule_id=str(data.get("schedule_id") or generate_request_id()),
            prompt=str(data.get("prompt") or ""),
            run_at=data.get("run_at"),
            interval_seconds=data.get("interval_seconds"),
            session_id=data.get("session_id"),
            status=str(data.get("status") or "pending"),
            created_at=str(data.get("created_at") or _now()),
            updated_at=str(data.get("updated_at") or _now()),
            last_run=data.get("last_run"),
            next_run=data.get("next_run"),
            metadata=dict(data.get("metadata") or {}),
        )


class TaskScheduler:
    """
    简单轮询式调度器
    """

    def __init__(
        self,
        path: str,
        poll_interval: float,
        max_pending: int,
        executor: Callable[[ScheduleItem], Dict[str, Any]],
        triggers: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self.path = Path(path)
        self.poll_interval = poll_interval
        self.max_pending = max_pending
        self.executor = executor
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.items: List[ScheduleItem] = []
        self.triggers = self._build_triggers(triggers or [])
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        items = data.get("items", [])
        if isinstance(items, list):
            self.items = [ScheduleItem.from_dict(item) for item in items if isinstance(item, dict)]
        self._refresh_next_runs()

    def save(self) -> None:
        payload = {
            "updated_at": _now(),
            "items": [item.to_dict() for item in self.items],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def add_schedule(
        self,
        prompt: str,
        run_at: Optional[Any] = None,
        interval_seconds: Optional[int] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduleItem:
        if not prompt:
            raise ValueError("prompt_required")
        if not run_at and not interval_seconds:
            raise ValueError("schedule_time_required")
        if interval_seconds is not None and interval_seconds <= 0:
            raise ValueError("invalid_interval")

        item = ScheduleItem(
            schedule_id=generate_request_id(),
            prompt=prompt,
            run_at=_format_time(_parse_time(run_at)) if run_at else None,
            interval_seconds=interval_seconds,
            session_id=session_id,
            metadata=metadata or {},
        )
        self._update_next_run(item)
        with self._lock:
            if len(self.items) >= self.max_pending:
                raise ValueError("schedule_queue_full")
            self.items.append(item)
            self.save()
        return item

    def remove_schedule(self, schedule_id: str) -> bool:
        with self._lock:
            for idx, item in enumerate(self.items):
                if item.schedule_id == schedule_id:
                    del self.items[idx]
                    self.save()
                    return True
        return False

    def list_schedules(self) -> List[ScheduleItem]:
        with self._lock:
            return list(self.items)

    def _run_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as exc:
                logger.warning(f"调度器执行异常: {exc}")
            self._stop.wait(self.poll_interval)

    def _tick(self) -> None:
        now = datetime.now()
        due: List[ScheduleItem] = []
        with self._lock:
            for item in self.items:
                if item.status not in {"pending", "running"}:
                    continue
                next_run = _parse_time(item.next_run)
                if next_run and next_run <= now:
                    due.append(item)

        for item in due:
            self._execute_item(item)

        for trigger in self.triggers:
            for item in trigger.check():
                self._execute_item(item)

    def _execute_item(self, item: ScheduleItem) -> None:
        item.status = "running"
        item.updated_at = _now()
        self.save()
        try:
            result = self.executor(item)
            success = bool(result.get("success", False))
            item.status = "completed" if success else "failed"
            item.last_run = _now()
            item.updated_at = _now()
            if item.interval_seconds:
                item.status = "pending"
                self._update_next_run(item)
            else:
                item.next_run = None
        except Exception as exc:
            item.status = "failed"
            item.updated_at = _now()
            item.metadata["last_error"] = str(exc)
        finally:
            self.save()

    def _update_next_run(self, item: ScheduleItem) -> None:
        if item.interval_seconds:
            next_time = datetime.now() + timedelta(seconds=item.interval_seconds)
            item.next_run = _format_time(next_time)
            return
        run_at = _parse_time(item.run_at)
        item.next_run = _format_time(run_at) if run_at else None

    def _refresh_next_runs(self) -> None:
        for item in self.items:
            if item.status in {"completed", "failed"} and not item.interval_seconds:
                continue
            if not item.next_run:
                self._update_next_run(item)

    def _build_triggers(self, entries: List[Dict[str, Any]]):
        triggers = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            trigger_type = str(entry.get("type") or "").lower()
            if trigger_type == "file":
                triggers.append(FileTrigger.from_config(entry))
            elif trigger_type == "clipboard":
                triggers.append(ClipboardTrigger.from_config(entry))
            elif trigger_type == "window":
                triggers.append(WindowTrigger.from_config(entry))
        return triggers


@dataclass
class TriggerBase:
    prompt: str
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    debounce_seconds: int = 2
    last_fire: Optional[datetime] = None

    def should_fire(self) -> bool:
        if not self.debounce_seconds:
            return True
        if not self.last_fire:
            return True
        return (datetime.now() - self.last_fire).total_seconds() >= self.debounce_seconds

    def build_item(self) -> ScheduleItem:
        self.last_fire = datetime.now()
        return ScheduleItem(
            schedule_id=generate_request_id(),
            prompt=self.prompt,
            session_id=self.session_id,
            status="pending",
            metadata=self.metadata,
        )

    def check(self) -> List[ScheduleItem]:
        return []


@dataclass
class FileTrigger(TriggerBase):
    path: str = ""
    last_signature: Optional[str] = None

    @classmethod
    def from_config(cls, data: Dict[str, Any]) -> "FileTrigger":
        return cls(
            prompt=str(data.get("prompt") or "检测到文件变化").strip(),
            session_id=data.get("session_id"),
            metadata={"trigger": "file", "path": data.get("path")},
            debounce_seconds=int(data.get("debounce", 2) or 2),
            path=str(data.get("path") or ""),
        )

    def check(self) -> List[ScheduleItem]:
        if not self.path:
            return []
        path = Path(self.path)
        if not path.exists():
            return []
        signature = self._build_signature(path)
        if not signature:
            return []
        if self.last_signature is None:
            self.last_signature = signature
            return []
        if signature != self.last_signature and self.should_fire():
            self.last_signature = signature
            return [self.build_item()]
        return []

    def _build_signature(self, path: Path) -> Optional[str]:
        try:
            stat = path.stat()
            return f"{stat.st_mtime}:{stat.st_size}"
        except Exception:
            return None


@dataclass
class ClipboardTrigger(TriggerBase):
    last_value: Optional[str] = None

    @classmethod
    def from_config(cls, data: Dict[str, Any]) -> "ClipboardTrigger":
        return cls(
            prompt=str(data.get("prompt") or "剪贴板更新").strip(),
            session_id=data.get("session_id"),
            metadata={"trigger": "clipboard"},
            debounce_seconds=int(data.get("debounce", 2) or 2),
        )

    def check(self) -> List[ScheduleItem]:
        value = _read_clipboard()
        if not value:
            return []
        if self.last_value is None:
            self.last_value = value
            return []
        if value != self.last_value and self.should_fire():
            self.last_value = value
            return [self.build_item()]
        return []


@dataclass
class WindowTrigger(TriggerBase):
    keyword: str = ""
    last_match: bool = False

    @classmethod
    def from_config(cls, data: Dict[str, Any]) -> "WindowTrigger":
        return cls(
            prompt=str(data.get("prompt") or "窗口激活").strip(),
            session_id=data.get("session_id"),
            metadata={"trigger": "window"},
            debounce_seconds=int(data.get("debounce", 2) or 2),
            keyword=str(data.get("keyword") or data.get("title_contains") or "").strip(),
        )

    def check(self) -> List[ScheduleItem]:
        if not self.keyword:
            return []
        title = _get_active_window_title() or ""
        matched = self.keyword.lower() in title.lower()
        if matched and not self.last_match and self.should_fire():
            self.last_match = matched
            return [self.build_item()]
        self.last_match = matched
        return []


def _read_clipboard() -> Optional[str]:
    try:
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        value = root.clipboard_get()
        root.destroy()
        return str(value)
    except Exception:
        return None


def _get_active_window_title() -> Optional[str]:
    try:
        import ctypes
        import ctypes.wintypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return None
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value
    except Exception:
        return None
