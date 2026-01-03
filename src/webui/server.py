# ==============================================================================
# 赛博像素聊天前端服务
# ==============================================================================

from __future__ import annotations

import json
import mimetypes
import queue
import shlex
import threading
import time
import uuid
import webbrowser
import zipfile
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from types import SimpleNamespace
from urllib.parse import urlparse, parse_qs

from src import BaseAgent, get_config
from src.agents.base import AgentCancelled
from src.core.config import Config
from src.core.memory import ConversationMemory
from src.core.logger import get_logger
from src.runtime import (
    TaskRunner,
    TaskSpec,
    save_task_result,
    load_task_index,
    get_task_record,
    list_task_artifacts,
    create_task_archive,
    cleanup_task_outputs,
    save_session_snapshot,
    load_session_snapshot,
    append_audit_event,
    run_news_digest,
    list_news_digests,
    load_news_digest,
    run_media_hub,
    list_media_items,
    update_media_item,
    add_manual_item,
    list_media_briefs,
    load_media_brief,
    list_media_sources,
    update_media_sources,
    list_media_alerts,
    update_media_alerts,
    build_media_stats,
    send_webhook,
    append_webhook_log,
    load_webhook_logs,
    clear_webhook_logs,
    list_tasks,
    add_task,
    update_task,
    remove_task,
    build_task_stats,
    list_bookmarks,
    add_bookmark,
    update_bookmark,
    remove_bookmark,
    list_reminders,
    add_reminder,
    update_reminder,
    remove_reminder,
    mark_reminder_fired,
    append_reminder_log,
    load_reminder_logs,
    collect_metrics,
    review_paths,
    review_text,
    preview_csv,
    transform_csv,
    build_knowledge_map,
    list_templates,
    add_template,
    update_template,
    remove_template,
    save_template_spec,
    list_artifact_tags,
    update_artifact_tags,
    remove_artifact_tags,
    list_sessions,
    add_session,
    load_combined_logs,
)
from src.runtime.scheduler import TaskScheduler, ScheduleItem
from src.runtime.workflows import run_workflow
from src.runtime.knowledge_base import search as kb_search, index_paths, clear_index, load_entry as kb_load_entry
from src.core.profiles import list_profiles, resolve_profile, apply_profile_to_agent
from src.tools.registry import build_plugin_catalog
from src.utils.helpers import truncate_text, redact_sensitive_payload
from src.utils.document_processor import generate_document
from src.dashboard import run_dashboard

logger = get_logger("chat_ui")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
WEBHOOK_LOG_PATH = "outputs/webhooks/webhook_log.jsonl"
TASK_BOARD_PATH = "outputs/task_board.json"
BOOKMARKS_PATH = "outputs/bookmarks.json"
REMINDERS_PATH = "outputs/reminders/reminders.json"
REMINDER_LOG_PATH = "outputs/reminders/reminders_log.jsonl"
WORKFLOW_TEMPLATE_STORE = "outputs/workflow_templates.json"
WORKFLOW_TEMPLATE_DIR = "outputs/workflow_templates"
ARTIFACT_TAGS_PATH = "outputs/artifact_tags.json"
FOCUS_SESSIONS_PATH = "outputs/focus_sessions.json"

ALLOWED_CONFIG_FIELDS = {
    "agent": {"max_iterations"},
    "memory": {
        "max_entries",
        "max_context_tokens",
        "type",
        "system_token_ratio",
        "history_token_ratio",
        "file_context_token_ratio",
        "file_context_chunk_size",
        "file_context_max_chunks_per_file",
        "file_context_min_score",
        "file_context_query_messages",
        "history_retrieval_enabled",
        "history_retrieval_token_ratio",
        "history_retrieval_max_messages",
        "history_retrieval_min_score",
        "history_retrieval_query_messages",
        "history_retrieval_include_roles",
        "project_notes_enabled",
        "project_notes_max",
        "long_term_enabled",
        "long_term_max",
        "notes_max_tokens",
        "pins_enabled",
        "pins_max",
        "search_max_results",
    },
    "model": {"temperature", "max_tokens", "model_name", "main_model_name", "base_url"},
    "plugins": {"enabled"},
    "scheduler": {"enabled", "poll_interval"},
    "news_digest": {
        "enabled",
        "schedule_time",
        "topics",
        "output_dir",
        "obsidian_enabled",
        "obsidian_dir",
        "obsidian_filename",
        "max_items",
        "per_topic_limit",
        "sources",
    },
    "media_hub": {
        "enabled",
        "schedule_time",
        "output_dir",
        "sources_file",
        "items_file",
        "alerts_file",
        "brief_dir",
        "obsidian_enabled",
        "obsidian_dir",
        "obsidian_filename",
        "max_items",
        "per_source_limit",
        "sources",
        "alerts",
    },
}

PRESET_OVERRIDES = {
    "engineer": {"agent": {"max_iterations": 160}, "memory": {"max_entries": 140}, "model": {"temperature": 0.4}},
    "writer": {"agent": {"max_iterations": 120}, "memory": {"max_entries": 100}, "model": {"temperature": 0.85}},
    "planner": {"agent": {"max_iterations": 140}, "memory": {"max_entries": 120}, "model": {"temperature": 0.6}},
}


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并配置字典
    """
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _filter_overrides(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    过滤允许的配置字段
    """
    filtered: Dict[str, Any] = {}
    for section, fields in ALLOWED_CONFIG_FIELDS.items():
        if section not in payload or not isinstance(payload.get(section), dict):
            continue
        filtered[section] = {k: v for k, v in payload[section].items() if k in fields}
    return filtered


def _safe_config_view(config: Config) -> Dict[str, Any]:
    """
    生成可暴露给前端的配置快照
    """
    data = config.model_dump() if hasattr(config, "model_dump") else config.dict()
    if "model" in data and isinstance(data["model"], dict):
        data["model"].pop("api_key", None)
    return data


class ConfigOverrides:
    """
    WebUI 配置覆盖存储
    """

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.overrides: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.overrides = {}
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.overrides = data
            else:
                self.overrides = {}
        except Exception:
            self.overrides = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.overrides, ensure_ascii=False, indent=2), encoding="utf-8")

    def apply(self, base_config: Config) -> Config:
        base_data = base_config.model_dump() if hasattr(base_config, "model_dump") else base_config.dict()
        merged = _deep_merge_dict(base_data, self.overrides)
        return Config(**merged)

    def update(self, payload: Dict[str, Any], base_config: Config) -> Config:
        filtered = _filter_overrides(payload)
        if not filtered:
            return self.apply(base_config)
        self.overrides = _deep_merge_dict(self.overrides, filtered)
        self.save()
        return self.apply(base_config)


@dataclass
class ChatSession:
    session_id: str
    agent: BaseAgent
    lock: threading.Lock
    created_at: float
    last_active: float
    participants: Dict[str, float] = field(default_factory=dict)
    cancel_event: threading.Event = field(default_factory=threading.Event)
    last_user_message: str = ""
    last_partial_reply: str = ""
    last_reply: str = ""

    def touch(self) -> None:
        self.last_active = time.time()

    def touch_client(self, client_id: Optional[str], timeout_seconds: int) -> None:
        if not client_id:
            return
        now = time.time()
        self.participants[client_id] = now
        if timeout_seconds <= 0:
            return
        stale = [cid for cid, ts in self.participants.items() if now - ts > timeout_seconds]
        for cid in stale:
            self.participants.pop(cid, None)


class ChatSessionManager:
    def __init__(self, profile: Optional[str] = None, override_path: Optional[str] = None) -> None:
        self.profile = profile
        self.base_config = get_config()
        override_path = override_path or "outputs/chat_ui_overrides.json"
        self.overrides = ConfigOverrides(override_path)
        self.config = self.overrides.apply(self.base_config)
        self._lock = threading.Lock()
        self._sessions: Dict[str, ChatSession] = {}
        self.scheduler: Optional[TaskScheduler] = None
        self.dashboard_server = None
        self.collaboration_timeout = getattr(self.config.chat_ui, "collaboration_timeout", 300)
        self.session_store_enabled = getattr(self.config.chat_ui, "session_store_enabled", True)
        self.session_store_dir = getattr(self.config.chat_ui, "session_store_dir", "outputs/sessions")
        self.audit_enabled = getattr(self.config.audit, "enabled", True)
        self.audit_path = getattr(self.config.audit, "file_path", "outputs/audit.log")
        self.audit_redact = getattr(self.config.audit, "redact_enabled", True)
        self._artifact_cache: Dict[str, Any] = {"mtime": 0.0, "data": []}

    def create_session(self) -> ChatSession:
        with self._lock:
            session = self._create_session_locked()
        return session

    def get_session(self, session_id: Optional[str], client_id: Optional[str] = None) -> Tuple[str, ChatSession]:
        normalized = self._normalize_session_id(session_id)
        with self._lock:
            if normalized and normalized in self._sessions:
                session = self._sessions[normalized]
                session.touch()
                if self.config.chat_ui.collaboration_enabled:
                    session.touch_client(client_id, self.collaboration_timeout)
                return normalized, session
            if normalized and self.session_store_enabled:
                snapshot = load_session_snapshot(normalized, self.session_store_dir)
                if snapshot:
                    session = self._create_session_from_snapshot(normalized, snapshot)
                    if self.config.chat_ui.collaboration_enabled:
                        session.touch_client(client_id, self.collaboration_timeout)
                    return session.session_id, session
            session = self._create_session_locked()
            if self.config.chat_ui.collaboration_enabled:
                session.touch_client(client_id, self.collaboration_timeout)
            return session.session_id, session

    def reset_session(self, session_id: str) -> bool:
        normalized = self._normalize_session_id(session_id)
        if not normalized:
            return False
        with self._lock:
            session = self._sessions.get(normalized)
        if not session:
            return False
        with session.lock:
            session.agent.memory.create_snapshot(label="reset")
            session.agent.reset()
            session.touch()
            session.last_user_message = ""
            session.last_partial_reply = ""
            session.last_reply = ""
            session.cancel_event.clear()
        return True

    def update_config(self, overrides: Dict[str, Any]) -> Config:
        self.config = self.overrides.update(overrides, self.base_config)
        self.collaboration_timeout = getattr(self.config.chat_ui, "collaboration_timeout", 300)
        self.session_store_enabled = getattr(self.config.chat_ui, "session_store_enabled", True)
        self.session_store_dir = getattr(self.config.chat_ui, "session_store_dir", "outputs/sessions")
        self.audit_enabled = getattr(self.config.audit, "enabled", True)
        self.audit_path = getattr(self.config.audit, "file_path", "outputs/audit.log")
        self.audit_redact = getattr(self.config.audit, "redact_enabled", True)
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            with session.lock:
                session.agent.config = self.config
                if getattr(session.agent, "memory", None):
                    session.agent.memory.apply_config(self.config.memory)
                if self.config.plugins.auto_reload:
                    session.agent.reload_tools()
                if hasattr(session.agent, "_init_client"):
                    session.agent._init_client()
                session.agent._refresh_system_message()
        return self.config

    def attach_scheduler(self, scheduler: TaskScheduler) -> None:
        self.scheduler = scheduler

    def get_status(self, session_id: str, client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        normalized = self._normalize_session_id(session_id)
        if not normalized:
            return None
        with self._lock:
            session = self._sessions.get(normalized)
        if not session:
            return None
        if self.config.chat_ui.collaboration_enabled:
            session.touch_client(client_id, self.collaboration_timeout)
        status = session.agent.get_status()
        status["session_id"] = session.session_id
        status["collaborators"] = len(session.participants)
        status["active_clients"] = list(session.participants.keys())
        return status

    def reload_plugins(self) -> Dict[str, Any]:
        """
        重新加载插件
        """
        with self._lock:
            sessions = list(self._sessions.values())
        for session in sessions:
            with session.lock:
                session.agent.reload_tools()
                session.agent._refresh_system_message()
        return {"reloaded": True, "sessions": len(sessions)}

    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        获取插件索引
        """
        plugin_config = getattr(self.config, "plugins", None)
        if not plugin_config:
            return []
        return build_plugin_catalog(
            plugin_paths=getattr(plugin_config, "tool_paths", []) or [],
            catalog_files=getattr(plugin_config, "catalog_files", []) or [],
            allow_unsigned=getattr(plugin_config, "allow_unsigned", True),
        )

    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        获取模板列表
        """
        profiles = list_profiles(self.config)
        return [
            {
                "name": profile.name,
                "description": profile.description,
            }
            for profile in profiles
        ]

    def apply_profile(self, session: ChatSession, profile_name: str) -> bool:
        """
        应用模板到会话
        """
        profile = resolve_profile(self.config, profile_name)
        if not profile:
            return False
        apply_profile_to_agent(session.agent, profile)
        return True

    def ensure_dashboard(self) -> Optional[str]:
        """
        确保仪表盘服务启动
        """
        dashboard_config = getattr(self.config, "dashboard", None)
        if dashboard_config and not getattr(dashboard_config, "enabled", True):
            return None
        with self._lock:
            if self.dashboard_server:
                return getattr(self.dashboard_server, "dashboard_url", None)
            output_dir = getattr(getattr(self.config, "artifacts", None), "output_dir", "outputs")
            host = getattr(dashboard_config, "host", "127.0.0.1")
            port = getattr(dashboard_config, "port", 8765)
            title = getattr(dashboard_config, "title", "SAMA Dashboard")
            self.dashboard_server = run_dashboard(
                output_dir=output_dir,
                host=host,
                port=port,
                title=title,
                background=True,
                auto_open=False,
                quiet=True
            )
            return getattr(self.dashboard_server, "dashboard_url", f"http://{host}:{port}")

    def get_artifact_index(self) -> List[Dict[str, Any]]:
        output_dir = getattr(self.config.artifacts, "output_dir", "outputs")
        index_path = Path(output_dir) / "task_index.json"
        if not index_path.exists():
            self._artifact_cache = {"mtime": 0.0, "data": []}
            return []
        try:
            mtime = index_path.stat().st_mtime
        except OSError:
            return load_task_index(output_dir=output_dir)
        cached = self._artifact_cache
        if cached.get("mtime") == mtime and isinstance(cached.get("data"), list):
            return cached["data"]
        data = load_task_index(output_dir=output_dir)
        self._artifact_cache = {"mtime": mtime, "data": data}
        return data

    def _create_session_locked(self) -> ChatSession:
        session_id = uuid.uuid4().hex
        memory = ConversationMemory()
        memory.apply_config(self.config.memory)
        agent = BaseAgent(config=self.config, profile=self.profile, memory=memory)
        now = time.time()
        session = ChatSession(
            session_id=session_id,
            agent=agent,
            lock=threading.Lock(),
            created_at=now,
            last_active=now
        )
        self._sessions[session_id] = session
        return session

    def _create_session_from_snapshot(self, session_id: str, snapshot: Dict[str, Any]) -> ChatSession:
        memory = ConversationMemory()
        memory.apply_config(self.config.memory)
        memory.load_snapshot_payload(snapshot)
        agent = BaseAgent(config=self.config, profile=self.profile, memory=memory)
        now = time.time()
        session = ChatSession(
            session_id=session_id,
            agent=agent,
            lock=threading.Lock(),
            created_at=now,
            last_active=now
        )
        self._sessions[session_id] = session
        return session

    @staticmethod
    def _normalize_session_id(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = str(value).strip()
        if len(value) > 64:
            return None
        return value


def run_chat_ui(
    host: str = "127.0.0.1",
    port: int = 8790,
    title: str = "sama",
    static_dir: Optional[str] = None,
    background: bool = False,
    auto_open: bool = False,
    max_port_tries: int = 10,
    max_body_size: int = 20000,
    profile: Optional[str] = None,
    quiet: bool = False
) -> ThreadingHTTPServer:
    """
    启动聊天前端服务
    """
    config = get_config()
    profile = profile or getattr(config, "active_profile", None)
    manager = ChatSessionManager(profile=profile)
    handler = _build_handler(
        manager=manager,
        title=title,
        static_dir=Path(static_dir) if static_dir else _default_static_dir(),
        max_body_size=max_body_size,
        model_name=config.model.effective_model_name,
        base_url=config.model.base_url,
        profile=profile,
    )

    scheduler_config = getattr(config, "scheduler", None)
    if scheduler_config and getattr(scheduler_config, "enabled", False):
        scheduler = TaskScheduler(
            path=scheduler_config.schedule_file,
            poll_interval=scheduler_config.poll_interval,
            max_pending=scheduler_config.max_pending,
            executor=lambda item: _execute_scheduled_task(item, manager),
            triggers=getattr(scheduler_config, "triggers", []) or [],
        )
        scheduler.start()
        manager.attach_scheduler(scheduler)
        _sync_news_schedule(manager)
        _sync_media_schedule(manager)

    server = _create_server(host, port, handler, max_port_tries=max_port_tries)
    actual_port = server.server_address[1]
    display_host = _resolve_display_host(host)
    url = _build_url(display_host, actual_port)
    server.chat_url = url
    server.display_host = display_host
    server.display_port = actual_port

    if port != 0 and actual_port != port:
        message = f"端口 {port} 被占用，已切换到 {actual_port}"
        if not quiet:
            print(message)
        logger.warning(message)

    if not quiet:
        print(f"聊天前端已启动: {url}")
    logger.info(f"聊天前端已启动: {url}")

    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    if background:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    else:
        server.serve_forever()
    return server


def _default_static_dir() -> Path:
    return Path(__file__).parent / "assets"


def _resolve_display_host(host: str) -> str:
    if not host or host in {"0.0.0.0", "::"}:
        return "localhost" if host == "::" else "127.0.0.1"
    return host


def _build_url(host: str, port: int) -> str:
    display = host
    if ":" in host and not host.startswith("["):
        display = f"[{host}]"
    return f"http://{display}:{port}"


def _create_server(host: str, port: int, handler, max_port_tries: int = 10) -> ThreadingHTTPServer:
    if max_port_tries < 1:
        max_port_tries = 1
    last_error: Optional[Exception] = None
    for offset in range(max_port_tries):
        try_port = 0 if port == 0 else port + offset
        try:
            return ThreadingHTTPServer((host, try_port), handler)
        except OSError as exc:
            last_error = exc
            if port == 0:
                break
    if last_error:
        raise last_error
    raise OSError("无法启动聊天前端服务")


def _execute_scheduled_task(item: ScheduleItem, manager: ChatSessionManager) -> Dict[str, Any]:
    """
    执行调度任务
    """
    if item.metadata.get("job") == "news_digest":
        result = run_news_digest(getattr(manager.config, "news_digest", None))
        if manager.audit_enabled:
            event = {
                "type": "news_digest",
                "schedule_id": item.schedule_id,
                "success": bool(result.get("success", False)),
                "date": result.get("date"),
            }
            if manager.audit_redact:
                event = redact_sensitive_payload(event)
            append_audit_event(event, manager.audit_path)
        return {
            "success": bool(result.get("success", False)),
            "output_dir": result.get("output_dir"),
            "session_id": None,
        }
    if item.metadata.get("job") == "media_hub":
        result = run_media_hub(getattr(manager.config, "media_hub", None))
        if manager.audit_enabled:
            event = {
                "type": "media_hub",
                "schedule_id": item.schedule_id,
                "success": bool(result.get("success", False)),
                "date": result.get("date"),
            }
            if manager.audit_redact:
                event = redact_sensitive_payload(event)
            append_audit_event(event, manager.audit_path)
        return {
            "success": bool(result.get("success", False)),
            "output_dir": result.get("output_dir"),
            "session_id": None,
        }
    if item.metadata.get("job") == "reminder":
        reminder_id = item.metadata.get("reminder_id")
        reminder = mark_reminder_fired(REMINDERS_PATH, reminder_id) if reminder_id else None
        append_reminder_log(REMINDER_LOG_PATH, {
            "type": "reminder_fired",
            "reminder_id": reminder_id,
            "title": reminder.get("title") if reminder else None,
            "due": reminder.get("due") if reminder else None,
        })
        if manager.audit_enabled:
            event = {
                "type": "reminder",
                "schedule_id": item.schedule_id,
                "reminder_id": reminder_id,
                "success": True,
            }
            if manager.audit_redact:
                event = redact_sensitive_payload(event)
            append_audit_event(event, manager.audit_path)
        return {"success": True, "output_dir": None, "session_id": None}

    session_id = item.session_id
    output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
    metadata = {"source": "schedule", "schedule_id": item.schedule_id}
    rollback_enabled = getattr(manager.config.scheduler, "rollback_on_failure", True)

    if session_id:
        session_id, session = manager.get_session(session_id)
        with session.lock:
            snapshot_id = None
            if rollback_enabled:
                snapshot = session.agent.memory.create_snapshot(label="schedule")
                snapshot_id = snapshot.get("snapshot_id") if snapshot else None
            runner = TaskRunner(session.agent, logger=logger, output_dir=output_dir)
            task = TaskSpec(task_id=item.schedule_id, prompt=item.prompt, metadata=metadata)
            result = runner.run_task(task, preprocess=False)
            out = runner.save_result(result, print_result=False)
            if rollback_enabled and not getattr(result.response, "success", False) and snapshot_id:
                session.agent.memory.restore_snapshot(snapshot_id)
            if manager.audit_enabled:
                event = {
                    "type": "schedule_run",
                    "session_id": session_id,
                    "schedule_id": item.schedule_id,
                    "success": getattr(result.response, "success", False),
                }
                if manager.audit_redact:
                    event = redact_sensitive_payload(event)
                append_audit_event(event, manager.audit_path)
            return {
                "success": getattr(result.response, "success", False),
                "output_dir": out,
                "session_id": session_id,
            }

    memory = ConversationMemory()
    memory.apply_config(manager.config.memory)
    agent = BaseAgent(config=manager.config, profile=manager.profile, memory=memory)
    runner = TaskRunner(agent, logger=logger, output_dir=output_dir)
    task = TaskSpec(task_id=item.schedule_id, prompt=item.prompt, metadata=metadata)
    result = runner.run_task(task, preprocess=False)
    out = runner.save_result(result, print_result=False)
    if manager.audit_enabled:
        event = {
            "type": "schedule_run",
            "session_id": None,
            "schedule_id": item.schedule_id,
            "success": getattr(result.response, "success", False),
        }
        if manager.audit_redact:
            event = redact_sensitive_payload(event)
        append_audit_event(event, manager.audit_path)
    return {
        "success": getattr(result.response, "success", False),
        "output_dir": out,
        "session_id": None,
    }


def _parse_schedule_time(value: str) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parts = text.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        now = datetime.now()
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate
    except Exception:
        return None


def _parse_due_time(value: str) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= 5 and ":" in text:
        return _parse_schedule_time(text)
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _remove_reminder_schedules(scheduler: Optional[TaskScheduler], reminder_id: str) -> List[str]:
    if not scheduler or not reminder_id:
        return []
    removed: List[str] = []
    for item in scheduler.list_schedules():
        if item.metadata.get("job") == "reminder" and item.metadata.get("reminder_id") == reminder_id:
            if scheduler.remove_schedule(item.schedule_id):
                removed.append(item.schedule_id)
    return removed


def _collect_review_entries(paths: List[str], text: Optional[str], name: Optional[str]) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    if text:
        entries.append({"path": name or "snippet", "content": text})
        return entries
    for raw in paths:
        path = Path(raw)
        if not path.exists() or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        entries.append({"path": str(path), "content": content})
    return entries


def _build_review_prompt(entries: List[Dict[str, str]]) -> str:
    lines = [
        "You are a senior code reviewer performing static analysis only.",
        "Review for bugs, risks, edge cases, logic flaws, and missing tests.",
        "Return Markdown with sections: Summary, Issues (severity + file + line if possible), Suggestions, Tests.",
        "",
    ]
    for entry in entries:
        path = entry.get("path") or "snippet"
        content = entry.get("content") or ""
        content = truncate_text(content, max_length=12000)
        lines.append(f"File: {path}")
        lines.append("```")
        lines.append(content)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def _run_code_review_agent(manager: ChatSessionManager, entries: List[Dict[str, str]]) -> Optional[str]:
    if not entries:
        return None
    memory = ConversationMemory()
    memory.apply_config(manager.config.memory)
    agent = BaseAgent(config=manager.config, profile=manager.profile, memory=memory)
    prompt = _build_review_prompt(entries)
    try:
        response = agent.run(prompt, stream=False)
        return getattr(response, "final_answer", None)
    except Exception as exc:
        return f"Review failed: {exc}"


def _find_news_schedule(manager: ChatSessionManager) -> Optional[ScheduleItem]:
    if not manager.scheduler:
        return None
    for item in manager.scheduler.list_schedules():
        if item.metadata.get("job") == "news_digest":
            return item
    return None


def _sync_news_schedule(manager: ChatSessionManager) -> None:
    config = getattr(manager.config, "news_digest", None)
    if not manager.scheduler or not config:
        return
    existing = _find_news_schedule(manager)
    if not getattr(config, "enabled", False):
        if existing:
            manager.scheduler.remove_schedule(existing.schedule_id)
        return
    schedule_time = getattr(config, "schedule_time", "12:00")
    next_run = _parse_schedule_time(schedule_time)
    if existing:
        if next_run:
            existing.next_run = next_run.isoformat()
            existing.updated_at = datetime.now().isoformat()
        existing.interval_seconds = 24 * 60 * 60
        existing.metadata["job"] = "news_digest"
        manager.scheduler.save()
        return

    try:
        item = manager.scheduler.add_schedule(
            prompt="news_digest",
            interval_seconds=24 * 60 * 60,
            session_id=None,
            metadata={"job": "news_digest"},
        )
        if next_run:
            item.next_run = next_run.isoformat()
            item.updated_at = datetime.now().isoformat()
            manager.scheduler.save()
    except Exception as exc:
        logger.warning(f"新闻摘要调度创建失败: {exc}")


def _find_media_schedule(manager: ChatSessionManager) -> Optional[ScheduleItem]:
    if not manager.scheduler:
        return None
    for item in manager.scheduler.list_schedules():
        if item.metadata.get("job") == "media_hub":
            return item
    return None


def _sync_media_schedule(manager: ChatSessionManager) -> None:
    config = getattr(manager.config, "media_hub", None)
    if not manager.scheduler or not config:
        return
    existing = _find_media_schedule(manager)
    if not getattr(config, "enabled", False):
        if existing:
            manager.scheduler.remove_schedule(existing.schedule_id)
        return
    schedule_time = getattr(config, "schedule_time", "12:00")
    next_run = _parse_schedule_time(schedule_time)
    if existing:
        if next_run:
            existing.next_run = next_run.isoformat()
            existing.updated_at = datetime.now().isoformat()
        existing.interval_seconds = 24 * 60 * 60
        existing.metadata["job"] = "media_hub"
        manager.scheduler.save()
        return

    try:
        item = manager.scheduler.add_schedule(
            prompt="media_hub",
            interval_seconds=24 * 60 * 60,
            session_id=None,
            metadata={"job": "media_hub"},
        )
        if next_run:
            item.next_run = next_run.isoformat()
            item.updated_at = datetime.now().isoformat()
            manager.scheduler.save()
    except Exception as exc:
        logger.warning(f"媒体中心调度创建失败: {exc}")


def _build_handler(
    manager: ChatSessionManager,
    title: str,
    static_dir: Path,
    max_body_size: int,
    model_name: str,
    base_url: str,
    profile: Optional[str]
):
    class ChatHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/" or path == "/index.html":
                return self._send_static_file("index.html", static_dir)
            if path.startswith("/assets/"):
                return self._send_static_file(path[len("/assets/"):], static_dir)
            if path == "/api/health":
                return self._send_json({"status": "ok"})
            if path == "/api/info":
                payload = {
                    "title": title,
                    "model_name": manager.config.model.effective_model_name,
                    "base_url": manager.config.model.base_url,
                    "profile": manager.profile or manager.config.active_profile,
                }
                return self._send_json(payload)
            if path == "/api/status":
                params = parse_qs(parsed.query)
                session_id = (params.get("session_id") or [None])[0]
                client_id = (params.get("client_id") or [None])[0]
                status = manager.get_status(session_id or "", client_id=client_id)
                if not status:
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                return self._send_json(status)
            if path == "/api/config":
                payload = {
                    "config": _safe_config_view(manager.config),
                    "overrides": manager.overrides.overrides,
                }
                return self._send_json(payload)
            if path == "/api/search":
                params = parse_qs(parsed.query)
                session_id = (params.get("session_id") or [None])[0]
                query = (params.get("q") or [""])[0]
                role = (params.get("role") or [None])[0]
                if not session_id or not query:
                    return self._send_json({"error": "missing_params"}, status=HTTPStatus.BAD_REQUEST)
                status = manager.get_status(session_id or "")
                if not status:
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                roles = [role] if role else None
                results = session.agent.memory.search_messages(query, roles=roles)
                return self._send_json({"results": results, "query": query})
            if path == "/api/pins":
                params = parse_qs(parsed.query)
                session_id = (params.get("session_id") or [None])[0]
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                pins = [
                    {
                        "message_id": msg.message_id,
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                    }
                    for msg in session.agent.memory.get_pinned_messages()
                ]
                return self._send_json({"pins": pins})
            if path == "/api/notes":
                params = parse_qs(parsed.query)
                session_id = (params.get("session_id") or [None])[0]
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                payload = {
                    "project": [note.to_dict() for note in session.agent.memory.list_project_notes()],
                    "long_term": [note.to_dict() for note in session.agent.memory.list_long_term_notes()],
                }
                return self._send_json(payload)
            if path == "/api/context":
                params = parse_qs(parsed.query)
                session_id = (params.get("session_id") or [None])[0]
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                report = session.agent.memory.last_context_report or {}
                return self._send_json({"context": report})
            if path == "/api/memory/stats":
                params = parse_qs(parsed.query)
                session_id = (params.get("session_id") or [None])[0]
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                memory = session.agent.memory
                payload = {
                    "dedup": memory.get_dedup_stats(),
                    "messages": len(memory.messages),
                    "pins": len(memory.pinned_ids),
                    "files": len(memory.files),
                    "project_notes": len(memory.project_notes),
                    "long_term_notes": len(memory.long_term_notes),
                }
                return self._send_json(payload)
            if path == "/api/artifacts":
                params = parse_qs(parsed.query)
                task_id = (params.get("task_id") or [None])[0]
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                if task_id:
                    record = get_task_record(task_id, output_dir=output_dir)
                    artifacts = list_task_artifacts(task_id, output_dir=output_dir)
                    return self._send_json({"record": record, "artifacts": artifacts})
                index = manager.get_artifact_index()
                return self._send_json({"tasks": index})
            if path == "/api/artifact":
                params = parse_qs(parsed.query)
                task_id = (params.get("task_id") or [None])[0]
                name = (params.get("name") or [None])[0]
                if not task_id or not name:
                    return self._send_json({"error": "missing_params"}, status=HTTPStatus.BAD_REQUEST)
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                base = Path(output_dir) / task_id
                target = (base / name).resolve()
                if not str(target).startswith(str(base.resolve())):
                    return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)
                if not target.exists() or not target.is_file():
                    return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)
                mime, _ = mimetypes.guess_type(target.name)
                if not mime:
                    mime = "application/octet-stream"
                data = target.read_bytes()
                self.send_response(HTTPStatus.OK)
                if mime.startswith("text/"):
                    self.send_header("Content-Type", f"{mime}; charset=utf-8")
                else:
                    self.send_header("Content-Type", mime)
                disposition = "inline" if mime == "application/pdf" else "attachment"
                safe_name = target.name.replace('"', "")
                self.send_header("Content-Disposition", f"{disposition}; filename=\"{safe_name}\"")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/api/archive":
                params = parse_qs(parsed.query)
                name = (params.get("name") or [None])[0]
                archive_dir = getattr(manager.config.artifacts, "archive_dir", "outputs/archives")
                archive_path = self._resolve_archive_path(name, archive_dir)
                if not archive_path:
                    return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)
                data = archive_path.read_bytes()
                mime, _ = mimetypes.guess_type(archive_path.name)
                if not mime:
                    mime = "application/octet-stream"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/api/schedules":
                if not manager.scheduler:
                    return self._send_json({"error": "scheduler_disabled"}, status=HTTPStatus.BAD_REQUEST)
                schedules = [item.to_dict() for item in manager.scheduler.list_schedules()]
                return self._send_json({"schedules": schedules})
            if path == "/api/plugins":
                plugins = manager.list_plugins()
                loaded = []
                if manager._sessions:
                    _, session = next(iter(manager._sessions.items()))
                    loaded = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "permissions": getattr(tool, "required_permissions", []),
                        }
                        for tool in session.agent.tools.values()
                    ]
                return self._send_json({"plugins": plugins, "loaded": loaded})
            if path == "/api/metrics":
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                metrics = self._load_tool_metrics(output_dir)
                recent = self._load_recent_task_times(output_dir, limit=30)
                return self._send_json({"metrics": metrics, "recent": recent})
            if path == "/api/news":
                params = parse_qs(parsed.query)
                date_key = (params.get("date") or [None])[0]
                news_config = getattr(manager.config, "news_digest", None)
                output_dir = getattr(news_config, "output_dir", "outputs/news") if news_config else "outputs/news"
                if date_key:
                    return self._send_json(load_news_digest(output_dir, date_key))
                return self._send_json(list_news_digests(output_dir))
            if path == "/api/media/items":
                params = parse_qs(parsed.query)
                media_config = getattr(manager.config, "media_hub", None)
                output_dir = getattr(media_config, "output_dir", "outputs/media") if media_config else "outputs/media"
                limit_raw = (params.get("limit") or ["200"])[0]
                try:
                    limit = int(limit_raw)
                except ValueError:
                    limit = 200
                filters = {
                    "q": (params.get("q") or [""])[0],
                    "source": (params.get("source") or [""])[0],
                    "platform": (params.get("platform") or [""])[0],
                    "tag": (params.get("tag") or [""])[0],
                    "saved": (params.get("saved") or [None])[0],
                    "read": (params.get("read") or [None])[0],
                    "alerted": (params.get("alerted") or [None])[0],
                }
                return self._send_json(list_media_items(output_dir, limit=limit, filters=filters))
            if path == "/api/media/briefs":
                media_config = getattr(manager.config, "media_hub", None)
                brief_dir = getattr(media_config, "brief_dir", "outputs/media/briefs") if media_config else "outputs/media/briefs"
                return self._send_json(list_media_briefs(brief_dir))
            if path == "/api/media/brief":
                params = parse_qs(parsed.query)
                date_key = (params.get("date") or [None])[0]
                media_config = getattr(manager.config, "media_hub", None)
                brief_dir = getattr(media_config, "brief_dir", "outputs/media/briefs") if media_config else "outputs/media/briefs"
                if not date_key:
                    return self._send_json({"error": "date_required"}, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(load_media_brief(brief_dir, date_key))
            if path == "/api/media/sources":
                media_config = getattr(manager.config, "media_hub", None)
                sources_file = getattr(media_config, "sources_file", "outputs/media/sources.json") if media_config else "outputs/media/sources.json"
                return self._send_json({"sources": list_media_sources(sources_file)})
            if path == "/api/media/alerts":
                media_config = getattr(manager.config, "media_hub", None)
                alerts_file = getattr(media_config, "alerts_file", "outputs/media/alerts.json") if media_config else "outputs/media/alerts.json"
                return self._send_json({"alerts": list_media_alerts(alerts_file)})
            if path == "/api/media/stats":
                media_config = getattr(manager.config, "media_hub", None)
                output_dir = getattr(media_config, "output_dir", "outputs/media") if media_config else "outputs/media"
                alerts_file = getattr(media_config, "alerts_file", "outputs/media/alerts.json") if media_config else "outputs/media/alerts.json"
                alerts = list_media_alerts(alerts_file)
                return self._send_json(build_media_stats(output_dir, alerts=alerts))
            if path == "/api/tasks":
                return self._send_json(list_tasks(TASK_BOARD_PATH))
            if path == "/api/tasks/stats":
                return self._send_json(build_task_stats(TASK_BOARD_PATH))
            if path == "/api/bookmarks":
                return self._send_json(list_bookmarks(BOOKMARKS_PATH))
            if path == "/api/reminders":
                return self._send_json(list_reminders(REMINDERS_PATH))
            if path == "/api/reminders/logs":
                params = parse_qs(parsed.query)
                limit_raw = (params.get("limit") or ["80"])[0]
                try:
                    limit = int(limit_raw)
                except ValueError:
                    limit = 80
                entries = load_reminder_logs(REMINDER_LOG_PATH, limit=limit)
                return self._send_json({"entries": entries})
            if path == "/api/system/metrics":
                return self._send_json(collect_metrics())
            if path == "/api/kb/map":
                kb_config = manager.config.knowledge_base
                return self._send_json(build_knowledge_map(kb_config.meta_file))
            if path == "/api/workflow/templates":
                return self._send_json(list_templates(WORKFLOW_TEMPLATE_STORE))
            if path == "/api/artifacts/tags":
                return self._send_json(list_artifact_tags(ARTIFACT_TAGS_PATH))
            if path == "/api/focus/sessions":
                return self._send_json(list_sessions(FOCUS_SESSIONS_PATH))
            if path == "/api/logs/combined":
                params = parse_qs(parsed.query)
                limit_raw = (params.get("limit") or ["200"])[0]
                try:
                    limit = int(limit_raw)
                except ValueError:
                    limit = 200
                paths = {
                    "audit": manager.audit_path if manager.audit_enabled else None,
                    "webhook": WEBHOOK_LOG_PATH,
                    "reminder": REMINDER_LOG_PATH,
                    "tasks": str(Path(getattr(manager.config.artifacts, "output_dir", "outputs")) / "task_history.jsonl"),
                }
                return self._send_json(load_combined_logs(paths, limit=limit))
            if path == "/api/triggers":
                scheduler_config = getattr(manager.config, "scheduler", None)
                triggers = getattr(scheduler_config, "triggers", []) if scheduler_config else []
                return self._send_json({"triggers": triggers})
            if path == "/api/webhooks/logs":
                params = parse_qs(parsed.query)
                limit_raw = (params.get("limit") or ["80"])[0]
                try:
                    limit = int(limit_raw)
                except ValueError:
                    limit = 80
                entries = load_webhook_logs(WEBHOOK_LOG_PATH, limit=limit)
                return self._send_json({"entries": entries})
            if path == "/api/audit":
                params = parse_qs(parsed.query)
                limit_raw = (params.get("limit") or ["50"])[0]
                session_id = (params.get("session_id") or [None])[0]
                try:
                    limit = int(limit_raw)
                except ValueError:
                    limit = 50
                entries = self._load_audit_events(limit, session_id)
                return self._send_json({"entries": entries})
            if path == "/api/profiles":
                params = parse_qs(parsed.query)
                session_id = (params.get("session_id") or [None])[0]
                current_profile = None
                if session_id and manager.get_status(session_id):
                    _, session = manager.get_session(session_id)
                    current_profile = getattr(session.agent, "profile_name", None)
                return self._send_json({
                    "profiles": manager.list_profiles(),
                    "active_profile": manager.config.active_profile,
                    "current_profile": current_profile,
                })
            if path == "/api/dashboard":
                params = parse_qs(parsed.query)
                start = (params.get("start") or ["false"])[0].lower() in {"1", "true", "yes"}
                url = manager.ensure_dashboard() if start else None
                if not url and manager.dashboard_server:
                    url = getattr(manager.dashboard_server, "dashboard_url", None)
                if not url:
                    return self._send_json({"error": "dashboard_unavailable"}, status=HTTPStatus.BAD_REQUEST)
                return self._send_json({"url": url, "running": manager.dashboard_server is not None})
            if path == "/api/kb/status":
                kb_config = manager.config.knowledge_base
                if not kb_config.enabled:
                    return self._send_json({"enabled": False, "total_entries": 0, "files": 0})
                index_path = Path(kb_config.index_file)
                meta_path = Path(kb_config.meta_file)
                total_entries = 0
                if index_path.exists():
                    total_entries = len([line for line in index_path.read_text(encoding="utf-8").splitlines() if line.strip()])
                meta = {}
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    except Exception:
                        meta = {}
                files = meta.get("files", {}) if isinstance(meta, dict) else {}
                aliases = meta.get("aliases", {}) if isinstance(meta, dict) else {}
                return self._send_json({
                    "enabled": kb_config.enabled,
                    "total_entries": total_entries,
                    "files": len(files) if isinstance(files, dict) else 0,
                    "index_file": str(index_path),
                    "aliases": aliases if isinstance(aliases, dict) else {},
                })
            if path == "/api/kb/entry":
                if not manager.config.knowledge_base.enabled:
                    return self._send_json({"error": "kb_disabled"}, status=HTTPStatus.BAD_REQUEST)
                params = parse_qs(parsed.query)
                path_value = (params.get("path") or [None])[0]
                chunk_id = (params.get("chunk_id") or [None])[0]
                if not path_value or chunk_id is None:
                    return self._send_json({"error": "missing_params"}, status=HTTPStatus.BAD_REQUEST)
                try:
                    chunk_id_int = int(chunk_id)
                except ValueError:
                    return self._send_json({"error": "invalid_chunk_id"}, status=HTTPStatus.BAD_REQUEST)
                content = kb_load_entry(path_value, chunk_id_int)
                if content is None:
                    return self._send_json({"error": "entry_not_found"}, status=HTTPStatus.NOT_FOUND)
                return self._send_json({"path": path_value, "chunk_id": chunk_id_int, "content": content})
            if path == "/api/memory/archives":
                archives = self._list_memory_archives(manager.config.memory.archive_dir)
                return self._send_json({"archives": archives})
            if path == "/api/memory/snapshots":
                params = parse_qs(parsed.query)
                session_id = (params.get("session_id") or [None])[0]
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                return self._send_json({"snapshots": session.agent.memory.list_snapshots()})

            return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/api/session":
                session = manager.create_session()
                return self._send_json({"session_id": session.session_id})

            payload, error = self._read_json(max_body_size)
            if error:
                return self._send_json({"error": error}, status=HTTPStatus.BAD_REQUEST)

            if path == "/api/config":
                if not manager.config.chat_ui.allow_config_update:
                    return self._send_json({"error": "config_update_disabled"}, status=HTTPStatus.BAD_REQUEST)
                overrides = payload.get("overrides")
                if overrides is None:
                    overrides = payload
                if not isinstance(overrides, dict):
                    return self._send_json({"error": "invalid_overrides"}, status=HTTPStatus.BAD_REQUEST)
                new_config = manager.update_config(overrides)
                if isinstance(overrides, dict):
                    if "news_digest" in overrides:
                        _sync_news_schedule(manager)
                    if "media_hub" in overrides:
                        _sync_media_schedule(manager)
                self._audit_event({
                    "type": "config_update",
                    "overrides": overrides,
                })
                return self._send_json({
                    "config": _safe_config_view(new_config),
                    "overrides": manager.overrides.overrides,
                })

            if path == "/api/news/refresh":
                result = run_news_digest(getattr(manager.config, "news_digest", None))
                if not result.get("success"):
                    return self._send_json({"error": result.get("error") or "news_failed"}, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(result)
            if path == "/api/media/refresh":
                result = run_media_hub(getattr(manager.config, "media_hub", None))
                if not result.get("success"):
                    return self._send_json({"error": result.get("error") or "media_failed"}, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(result)
            if path == "/api/media/item":
                item_id = str(payload.get("id") or "").strip()
                if not item_id:
                    return self._send_json({"error": "id_required"}, status=HTTPStatus.BAD_REQUEST)
                media_config = getattr(manager.config, "media_hub", None)
                output_dir = getattr(media_config, "output_dir", "outputs/media") if media_config else "outputs/media"
                updates = payload.get("updates") if isinstance(payload.get("updates"), dict) else payload
                result = update_media_item(output_dir, item_id, updates)
                if result.get("error"):
                    return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(result)
            if path == "/api/media/add":
                media_config = getattr(manager.config, "media_hub", None)
                output_dir = getattr(media_config, "output_dir", "outputs/media") if media_config else "outputs/media"
                result = add_manual_item(output_dir, payload)
                if result.get("error"):
                    return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(result)
            if path == "/api/media/sources":
                sources = payload.get("sources")
                if not isinstance(sources, list):
                    return self._send_json({"error": "sources_required"}, status=HTTPStatus.BAD_REQUEST)
                media_config = getattr(manager.config, "media_hub", None)
                sources_file = getattr(media_config, "sources_file", "outputs/media/sources.json") if media_config else "outputs/media/sources.json"
                updated = update_media_sources(sources_file, sources)
                return self._send_json({"sources": updated})
            if path == "/api/media/alerts":
                alerts = payload.get("alerts")
                if not isinstance(alerts, list):
                    return self._send_json({"error": "alerts_required"}, status=HTTPStatus.BAD_REQUEST)
                media_config = getattr(manager.config, "media_hub", None)
                alerts_file = getattr(media_config, "alerts_file", "outputs/media/alerts.json") if media_config else "outputs/media/alerts.json"
                updated = update_media_alerts(alerts_file, alerts)
                return self._send_json({"alerts": updated})
            if path == "/api/webhooks/send":
                url = str(payload.get("url") or "").strip()
                body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload.get("payload")
                headers = payload.get("headers") if isinstance(payload.get("headers"), dict) else None
                timeout = payload.get("timeout", 6)
                try:
                    timeout = int(timeout)
                except (TypeError, ValueError):
                    timeout = 6
                if not isinstance(body, dict):
                    body = {"message": str(body or "").strip()}
                result = send_webhook(url, body, headers=headers, timeout=timeout)
                self._log_webhook({
                    "type": "outbound",
                    "url": url,
                    "payload": body,
                    "result": result,
                })
                if not result.get("success"):
                    return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(result)
            if path == "/api/webhooks/inbound":
                self._log_webhook({"type": "inbound", "payload": payload})
                actions: Dict[str, Any] = {}
                media_item = payload.get("media_item")
                if isinstance(media_item, dict):
                    media_config = getattr(manager.config, "media_hub", None)
                    output_dir = getattr(media_config, "output_dir", "outputs/media") if media_config else "outputs/media"
                    actions["media_item"] = add_manual_item(output_dir, media_item)
                prompt = str(payload.get("prompt") or "").strip()
                session_id = payload.get("session_id")
                if prompt:
                    actions["prompt"] = self._enqueue_webhook_prompt(prompt, session_id)
                return self._send_json({"received": True, "actions": actions})
            if path == "/api/webhooks/clear":
                ok = clear_webhook_logs(WEBHOOK_LOG_PATH)
                return self._send_json({"cleared": ok})

            if path == "/api/documents/generate":
                content = str(payload.get("content") or "").strip()
                if not content:
                    return self._send_json({"error": "content_required"}, status=HTTPStatus.BAD_REQUEST)
                doc_type = str(payload.get("format") or "pdf").strip().lower()
                title = str(payload.get("title") or "").strip()
                filename = str(payload.get("filename") or "").strip()
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                try:
                    document = generate_document(
                        content=content,
                        doc_type=doc_type,
                        output_dir=output_dir,
                        title=title or None,
                        filename=filename or None,
                    )
                except ValueError as exc:
                    return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                except ImportError as exc:
                    return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                summary = truncate_text(content, 1600)
                response = SimpleNamespace(
                    success=True,
                    final_answer=summary,
                    total_iterations=0,
                    execution_time=0,
                    error_message=None,
                )
                metadata = {
                    "source": "document",
                    "format": document.get("format"),
                    "title": document.get("title"),
                    "file": document.get("file_name"),
                    "tags": [document.get("format")],
                }
                save_task_result(
                    task_id=document["task_id"],
                    prompt=f"Document export ({document.get('format')})",
                    response=response,
                    output_dir=output_dir,
                    print_result=False,
                    record_history=True,
                    record_index=True,
                    metadata=metadata,
                )
                self._audit_event({
                    "type": "document_generate",
                    "session_id": payload.get("session_id"),
                    "task_id": document.get("task_id"),
                    "format": document.get("format"),
                    "title": document.get("title"),
                })
                document_url = f"/api/artifact?task_id={document['task_id']}&name={document['file_name']}"
                return self._send_json({
                    "document": {
                        "task_id": document.get("task_id"),
                        "name": document.get("file_name"),
                        "format": document.get("format"),
                        "title": document.get("title"),
                        "url": document_url,
                    }
                })

            if path == "/api/tasks":
                action = str(payload.get("action") or "add").lower()
                if action == "add":
                    result = add_task(TASK_BOARD_PATH, payload)
                elif action == "update":
                    task_id = str(payload.get("id") or payload.get("task_id") or "").strip()
                    if not task_id:
                        return self._send_json({"error": "task_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    updates = payload.get("updates") if isinstance(payload.get("updates"), dict) else payload
                    result = update_task(TASK_BOARD_PATH, task_id, updates)
                elif action == "remove":
                    task_id = str(payload.get("id") or payload.get("task_id") or "").strip()
                    if not task_id:
                        return self._send_json({"error": "task_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    result = remove_task(TASK_BOARD_PATH, task_id)
                else:
                    return self._send_json({"error": "invalid_action"}, status=HTTPStatus.BAD_REQUEST)
                if result.get("error"):
                    return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(result)

            if path == "/api/bookmarks":
                action = str(payload.get("action") or "add").lower()
                if action == "add":
                    result = add_bookmark(BOOKMARKS_PATH, payload)
                elif action == "update":
                    item_id = str(payload.get("id") or payload.get("item_id") or "").strip()
                    if not item_id:
                        return self._send_json({"error": "item_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    updates = payload.get("updates") if isinstance(payload.get("updates"), dict) else payload
                    result = update_bookmark(BOOKMARKS_PATH, item_id, updates)
                elif action == "remove":
                    item_id = str(payload.get("id") or payload.get("item_id") or "").strip()
                    if not item_id:
                        return self._send_json({"error": "item_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    result = remove_bookmark(BOOKMARKS_PATH, item_id)
                else:
                    return self._send_json({"error": "invalid_action"}, status=HTTPStatus.BAD_REQUEST)
                if result.get("error"):
                    return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(result)

            if path == "/api/reminders":
                action = str(payload.get("action") or "add").lower()
                if action == "add":
                    result = add_reminder(REMINDERS_PATH, payload)
                    if result.get("error"):
                        return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                    reminder = result.get("reminder")
                    schedule_payload = None
                    if manager.scheduler and reminder:
                        due_time = _parse_due_time(reminder.get("due"))
                        if due_time:
                            schedule_payload = manager.scheduler.add_schedule(
                                prompt=f"Reminder: {reminder.get('title')}",
                                run_at=due_time,
                                session_id=payload.get("session_id"),
                                metadata={"job": "reminder", "reminder_id": reminder.get("id")},
                            ).to_dict()
                    if schedule_payload:
                        result["schedule"] = schedule_payload
                    return self._send_json(result)
                if action == "update":
                    reminder_id = str(payload.get("id") or payload.get("reminder_id") or "").strip()
                    if not reminder_id:
                        return self._send_json({"error": "reminder_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    updates = payload.get("updates") if isinstance(payload.get("updates"), dict) else payload
                    removed = []
                    if "due" in updates or "status" in updates:
                        removed = _remove_reminder_schedules(manager.scheduler, reminder_id)
                    result = update_reminder(REMINDERS_PATH, reminder_id, updates)
                    if result.get("error"):
                        return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                    reminder = result.get("reminder")
                    schedule_payload = None
                    if manager.scheduler and reminder and reminder.get("status") not in {"done", "cancelled"}:
                        if "due" in updates or updates.get("reschedule"):
                            due_time = _parse_due_time(reminder.get("due"))
                            if due_time:
                                schedule_payload = manager.scheduler.add_schedule(
                                    prompt=f"Reminder: {reminder.get('title')}",
                                    run_at=due_time,
                                    session_id=payload.get("session_id"),
                                    metadata={"job": "reminder", "reminder_id": reminder.get("id")},
                                ).to_dict()
                    if removed:
                        result["removed_schedules"] = removed
                    if schedule_payload:
                        result["schedule"] = schedule_payload
                    return self._send_json(result)
                if action == "remove":
                    reminder_id = str(payload.get("id") or payload.get("reminder_id") or "").strip()
                    if not reminder_id:
                        return self._send_json({"error": "reminder_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    removed = _remove_reminder_schedules(manager.scheduler, reminder_id)
                    result = remove_reminder(REMINDERS_PATH, reminder_id)
                    if result.get("error"):
                        return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                    if removed:
                        result["removed_schedules"] = removed
                    return self._send_json(result)
                return self._send_json({"error": "invalid_action"}, status=HTTPStatus.BAD_REQUEST)

            if path == "/api/workflow/templates":
                action = str(payload.get("action") or "add").lower()
                if action == "add":
                    result = add_template(WORKFLOW_TEMPLATE_STORE, payload)
                    if result.get("error"):
                        return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                    if payload.get("save_file"):
                        template = result.get("template") or {}
                        result["path"] = save_template_spec(WORKFLOW_TEMPLATE_DIR, template)
                    return self._send_json(result)
                if action == "update":
                    template_id = str(payload.get("id") or payload.get("template_id") or "").strip()
                    if not template_id:
                        return self._send_json({"error": "template_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    updates = payload.get("updates") if isinstance(payload.get("updates"), dict) else payload
                    result = update_template(WORKFLOW_TEMPLATE_STORE, template_id, updates)
                    if result.get("error"):
                        return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                    if payload.get("save_file"):
                        template = result.get("template") or {}
                        result["path"] = save_template_spec(WORKFLOW_TEMPLATE_DIR, template)
                    return self._send_json(result)
                if action == "remove":
                    template_id = str(payload.get("id") or payload.get("template_id") or "").strip()
                    if not template_id:
                        return self._send_json({"error": "template_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    result = remove_template(WORKFLOW_TEMPLATE_STORE, template_id)
                    if result.get("error"):
                        return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                    return self._send_json(result)
                if action in {"export", "run"}:
                    template_id = str(payload.get("id") or payload.get("template_id") or "").strip()
                    if not template_id:
                        return self._send_json({"error": "template_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    data = list_templates(WORKFLOW_TEMPLATE_STORE)
                    template = next((item for item in data.get("items", []) if item.get("id") == template_id), None)
                    if not template:
                        return self._send_json({"error": "template_not_found"}, status=HTTPStatus.NOT_FOUND)
                    path_value = save_template_spec(WORKFLOW_TEMPLATE_DIR, template)
                    if not path_value:
                        return self._send_json({"error": "spec_invalid"}, status=HTTPStatus.BAD_REQUEST)
                    if action == "export":
                        return self._send_json({"path": path_value})
                    session_id = payload.get("session_id")
                    output_dir = getattr(manager.config.workflow, "output_dir", "outputs/workflows")
                    if session_id and manager.get_status(session_id):
                        _, session = manager.get_session(session_id)
                        runner = TaskRunner(session.agent, logger=logger, output_dir=output_dir)
                    else:
                        memory = ConversationMemory()
                        memory.apply_config(manager.config.memory)
                        agent = BaseAgent(config=manager.config, profile=manager.profile, memory=memory)
                        runner = TaskRunner(agent, logger=logger, output_dir=output_dir)
                    result = run_workflow(path_value, runner, output_dir=output_dir)
                    summary = [
                        {
                            "node_id": node.node_id,
                            "status": node.status,
                            "output_dir": node.output_dir,
                        }
                        for node in result.nodes
                    ]
                    return self._send_json({"workflow_id": result.workflow_id, "nodes": summary, "path": path_value})
                return self._send_json({"error": "invalid_action"}, status=HTTPStatus.BAD_REQUEST)

            if path == "/api/artifacts/tags":
                action = str(payload.get("action") or "update").lower()
                if action == "update":
                    task_id = str(payload.get("task_id") or payload.get("id") or "").strip()
                    if not task_id:
                        return self._send_json({"error": "task_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    result = update_artifact_tags(ARTIFACT_TAGS_PATH, task_id, payload)
                elif action == "remove":
                    task_id = str(payload.get("task_id") or payload.get("id") or "").strip()
                    if not task_id:
                        return self._send_json({"error": "task_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    result = remove_artifact_tags(ARTIFACT_TAGS_PATH, task_id)
                else:
                    return self._send_json({"error": "invalid_action"}, status=HTTPStatus.BAD_REQUEST)
                if result.get("error"):
                    return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(result)

            if path == "/api/focus/sessions":
                result = add_session(FOCUS_SESSIONS_PATH, payload)
                if result.get("error"):
                    return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(result)

            if path == "/api/code/review":
                paths = payload.get("paths")
                text = payload.get("text")
                analysis_enabled = payload.get("analysis", True)
                if isinstance(paths, list) and paths:
                    clean_paths = [str(p) for p in paths if str(p).strip()]
                    static_result = review_paths(clean_paths)
                    analysis = None
                    if analysis_enabled:
                        entries = _collect_review_entries(clean_paths, None, None)
                        analysis = _run_code_review_agent(manager, entries)
                    static_result["analysis"] = analysis
                    return self._send_json(static_result)
                if isinstance(text, str) and text.strip():
                    static_result = review_text(text, payload.get("name"))
                    analysis = _run_code_review_agent(
                        manager,
                        _collect_review_entries([], text, payload.get("name"))
                    ) if analysis_enabled else None
                    static_result["analysis"] = analysis
                    return self._send_json(static_result)
                return self._send_json({"error": "paths_or_text_required"}, status=HTTPStatus.BAD_REQUEST)

            if path == "/api/data/preview":
                content = str(payload.get("content") or "")
                path_value = str(payload.get("path") or "").strip()
                limit = payload.get("limit", 20)
                try:
                    limit = int(limit)
                except (TypeError, ValueError):
                    limit = 20
                if not content and path_value:
                    try:
                        content = Path(path_value).read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        return self._send_json({"error": "file_read_failed"}, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(preview_csv(content, limit=limit))

            if path == "/api/data/transform":
                content = str(payload.get("content") or "")
                path_value = str(payload.get("path") or "").strip()
                operations = payload.get("operations") if isinstance(payload.get("operations"), list) else []
                limit = payload.get("limit", 50)
                try:
                    limit = int(limit)
                except (TypeError, ValueError):
                    limit = 50
                if not content and path_value:
                    try:
                        content = Path(path_value).read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        return self._send_json({"error": "file_read_failed"}, status=HTTPStatus.BAD_REQUEST)
                result = transform_csv(content, operations, limit=limit)
                if result.get("error"):
                    return self._send_json(result, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(result)

            if path == "/api/profile":
                session_id = payload.get("session_id")
                profile_name = str(payload.get("profile") or "").strip()
                if not session_id or not profile_name:
                    return self._send_json({"error": "missing_params"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                ok = manager.apply_profile(session, profile_name)
                if not ok:
                    return self._send_json({"error": "profile_not_found"}, status=HTTPStatus.BAD_REQUEST)
                self._persist_session(session)
                return self._send_json({"profile": profile_name})

            if path == "/api/preset":
                name = str(payload.get("name") or "").strip().lower()
                if not name or name not in PRESET_OVERRIDES:
                    return self._send_json({"error": "preset_not_found"}, status=HTTPStatus.BAD_REQUEST)
                manager.update_config(PRESET_OVERRIDES[name])
                self._audit_event({
                    "type": "preset",
                    "preset": name,
                })
                return self._send_json({"preset": name})

            if path == "/api/kb/search":
                if not manager.config.knowledge_base.enabled:
                    return self._send_json({"error": "kb_disabled"}, status=HTTPStatus.BAD_REQUEST)
                query = str(payload.get("query") or "").strip()
                if not query:
                    return self._send_json({"error": "query_required"}, status=HTTPStatus.BAD_REQUEST)
                result = kb_search(query)
                return self._send_json(result)

            if path == "/api/kb/index":
                if not manager.config.knowledge_base.enabled:
                    return self._send_json({"error": "kb_disabled"}, status=HTTPStatus.BAD_REQUEST)
                raw_paths = payload.get("paths")
                full_rebuild = bool(payload.get("full_rebuild", False))
                paths = []
                if isinstance(raw_paths, list):
                    paths = [str(item) for item in raw_paths if str(item).strip()]
                elif isinstance(raw_paths, str):
                    paths = [raw_paths]
                if not paths:
                    paths = ["."]
                result = index_paths(paths, full_rebuild=full_rebuild)
                return self._send_json(result)

            if path == "/api/kb/clear":
                if not manager.config.knowledge_base.enabled:
                    return self._send_json({"error": "kb_disabled"}, status=HTTPStatus.BAD_REQUEST)
                clear_index()
                return self._send_json({"cleared": True})

            if path == "/api/command":
                command_text = str(payload.get("command") or "").strip()
                if not command_text:
                    return self._send_json({"error": "command_required"}, status=HTTPStatus.BAD_REQUEST)
                session_id = payload.get("session_id")
                client_id = payload.get("client_id")
                session_id, session = manager.get_session(session_id, client_id=client_id)
                cmd, args, parse_error = self._parse_command(command_text)
                if parse_error:
                    return self._send_json({"error": parse_error}, status=HTTPStatus.BAD_REQUEST)
                if not cmd:
                    return self._send_json({"error": "command_required"}, status=HTTPStatus.BAD_REQUEST)
                result = self._handle_command(session_id, session, cmd, args)
                self._persist_session(session)
                return self._send_json(result)

            if path == "/api/plugins/reload":
                if not manager.config.plugins.enabled:
                    return self._send_json({"error": "plugins_disabled"}, status=HTTPStatus.BAD_REQUEST)
                result = manager.reload_plugins()
                return self._send_json(result)

            if path == "/api/memory/snapshot":
                session_id = payload.get("session_id")
                label = str(payload.get("label") or "").strip()
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                snapshot = session.agent.memory.create_snapshot(label=label)
                return self._send_json({"snapshot": snapshot})

            if path == "/api/memory/rollback":
                session_id = payload.get("session_id")
                snapshot_id = str(payload.get("snapshot_id") or "").strip()
                if not session_id or not snapshot_id:
                    return self._send_json({"error": "missing_params"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                ok = session.agent.memory.restore_snapshot(snapshot_id)
                return self._send_json({"restored": ok})

            if path == "/api/memory/archive":
                session_id = payload.get("session_id")
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                archive_path = session.agent.memory.archive_memory()
                if not archive_path:
                    return self._send_json({"error": "archive_failed"}, status=HTTPStatus.BAD_REQUEST)
                return self._send_json({"archive": archive_path})

            if path == "/api/memory/archive/restore":
                session_id = payload.get("session_id")
                name = str(payload.get("name") or "").strip()
                if not session_id or not name:
                    return self._send_json({"error": "missing_params"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                archive_path = self._resolve_archive_path(name, manager.config.memory.archive_dir)
                if not archive_path:
                    return self._send_json({"error": "archive_not_found"}, status=HTTPStatus.NOT_FOUND)
                try:
                    payload_data = json.loads(archive_path.read_text(encoding="utf-8"))
                except Exception:
                    return self._send_json({"error": "invalid_archive"}, status=HTTPStatus.BAD_REQUEST)
                _, session = manager.get_session(session_id)
                ok = session.agent.memory.load_snapshot_payload(payload_data)
                self._persist_session(session)
                return self._send_json({"restored": ok, "name": name})

            if path == "/api/artifacts/search":
                query = str(payload.get("query") or "").strip()
                filters = payload.get("filters") if isinstance(payload.get("filters"), dict) else {}
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                results = self._search_artifacts(query, filters, output_dir)
                return self._send_json({"results": results})

            if path == "/api/artifacts/diff":
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                left = str(payload.get("left") or "").strip()
                right = str(payload.get("right") or "").strip()
                mode = str(payload.get("mode") or "").lower()
                if mode == "all":
                    diff = self._diff_artifacts_bundle(left, right, output_dir)
                    if diff.get("error"):
                        return self._send_json(diff, status=HTTPStatus.BAD_REQUEST)
                    return self._send_json(diff)
                diff = self._diff_artifacts(left, right, output_dir)
                if diff.get("error"):
                    return self._send_json(diff, status=HTTPStatus.BAD_REQUEST)
                return self._send_json(diff)

            if path == "/api/artifacts/archive":
                task_id = str(payload.get("task_id") or "").strip()
                if not task_id:
                    return self._send_json({"error": "task_id_required"}, status=HTTPStatus.BAD_REQUEST)
                archive_dir = getattr(manager.config.artifacts, "archive_dir", "outputs/archives")
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                archive_path = create_task_archive(task_id, output_dir=output_dir, archive_dir=archive_dir)
                if not archive_path:
                    return self._send_json({"error": "archive_failed"}, status=HTTPStatus.BAD_REQUEST)
                download_url = f"/api/archive?name={Path(archive_path).name}"
                return self._send_json({"archive": archive_path, "download_url": download_url})

            if path == "/api/artifacts/archive/batch":
                task_ids = payload.get("task_ids")
                if not isinstance(task_ids, list) or not task_ids:
                    return self._send_json({"error": "task_ids_required"}, status=HTTPStatus.BAD_REQUEST)
                archive_dir = getattr(manager.config.artifacts, "archive_dir", "outputs/archives")
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                archive_path, skipped = self._create_bundle_archive(task_ids, output_dir, archive_dir)
                if not archive_path:
                    return self._send_json({"error": "archive_failed"}, status=HTTPStatus.BAD_REQUEST)
                download_url = f"/api/archive?name={Path(archive_path).name}"
                return self._send_json({"archive": archive_path, "download_url": download_url, "skipped": skipped})

            if path == "/api/artifacts/cleanup":
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                keep_recent = payload.get("keep_recent")
                max_days = payload.get("max_days")
                keep_failed = payload.get("keep_failed")
                dry_run = bool(payload.get("dry_run", False))
                cfg = manager.config.artifacts
                keep_recent = int(keep_recent) if keep_recent is not None else getattr(cfg, "cleanup_keep_recent", 50)
                if max_days is None:
                    max_days = getattr(cfg, "cleanup_max_days", None)
                elif max_days == "":
                    max_days = None
                else:
                    max_days = int(max_days)
                if keep_failed is None:
                    keep_failed = getattr(cfg, "cleanup_keep_failed", True)
                result = cleanup_task_outputs(
                    output_dir=output_dir,
                    keep_recent=keep_recent,
                    max_age_days=max_days,
                    keep_failed=bool(keep_failed),
                    dry_run=dry_run
                )
                return self._send_json(result)

            if path == "/api/artifacts/rerun":
                task_id = str(payload.get("task_id") or "").strip()
                session_id = payload.get("session_id")
                if not task_id:
                    return self._send_json({"error": "task_id_required"}, status=HTTPStatus.BAD_REQUEST)
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                record = get_task_record(task_id, output_dir=output_dir)
                if not record:
                    return self._send_json({"error": "task_not_found"}, status=HTTPStatus.NOT_FOUND)
                prompt = record.get("prompt") or ""
                if not prompt:
                    return self._send_json({"error": "prompt_missing"}, status=HTTPStatus.BAD_REQUEST)
                if session_id and manager.get_status(session_id):
                    session_id, session = manager.get_session(session_id)
                    with session.lock:
                        runner = TaskRunner(session.agent, logger=logger, output_dir=output_dir)
                        task = TaskSpec(task_id=f"{task_id}_rerun_{int(time.time())}", prompt=prompt, metadata={
                            "source": "rerun",
                            "origin_task_id": task_id,
                        })
                        result = runner.run_task(task, preprocess=False)
                        out = runner.save_result(result, print_result=False)
                else:
                    memory = ConversationMemory()
                    memory.apply_config(manager.config.memory)
                    agent = BaseAgent(config=manager.config, profile=manager.profile, memory=memory)
                    runner = TaskRunner(agent, logger=logger, output_dir=output_dir)
                    task = TaskSpec(task_id=f"{task_id}_rerun_{int(time.time())}", prompt=prompt, metadata={
                        "source": "rerun",
                        "origin_task_id": task_id,
                    })
                    result = runner.run_task(task, preprocess=False)
                    out = runner.save_result(result, print_result=False)
                return self._send_json({
                    "task_id": task.task_id,
                    "success": getattr(result.response, "success", False),
                    "output_dir": out,
                })

            if path == "/api/chat/stream":
                return self._handle_chat_stream(payload)

            if path == "/api/chat/cancel":
                session_id = payload.get("session_id")
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                session.cancel_event.set()
                return self._send_json({"cancelled": True, "session_id": session_id})

            if path == "/api/pin":
                session_id = payload.get("session_id")
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                memory = session.agent.memory
                message_id = str(payload.get("message_id") or "").strip()
                index = payload.get("index")
                ok = False
                if index is not None:
                    try:
                        ok = memory.pin_message_by_index(int(index))
                    except (TypeError, ValueError):
                        ok = False
                elif message_id:
                    ok = memory.pin_message(message_id)
                else:
                    last = self._find_last_message(memory, role="assistant")
                    if last:
                        ok = memory.pin_message(last.message_id)
                return self._send_json({"pinned": ok})

            if path == "/api/unpin":
                session_id = payload.get("session_id")
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                memory = session.agent.memory
                message_id = str(payload.get("message_id") or "").strip()
                if message_id == "all":
                    memory.pinned_ids = []
                    return self._send_json({"unpinned": True})
                if not message_id:
                    return self._send_json({"error": "message_id_required"}, status=HTTPStatus.BAD_REQUEST)
                ok = memory.unpin_message(message_id)
                return self._send_json({"unpinned": ok})

            if path == "/api/notes":
                session_id = payload.get("session_id")
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                note_type = str(payload.get("type") or "project").lower()
                title = str(payload.get("title") or "").strip()
                content = str(payload.get("content") or "").strip()
                if not content:
                    return self._send_json({"error": "content_required"}, status=HTTPStatus.BAD_REQUEST)
                if not manager.get_status(session_id):
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                _, session = manager.get_session(session_id)
                memory = session.agent.memory
                if note_type in {"long", "long_term", "longterm"}:
                    note = memory.add_long_term_note(title, content, tags=payload.get("tags"))
                else:
                    note = memory.add_project_note(title, content, tags=payload.get("tags"))
                return self._send_json({"note": note.to_dict() if note else None})

            if path == "/api/schedules":
                if not manager.scheduler:
                    return self._send_json({"error": "scheduler_disabled"}, status=HTTPStatus.BAD_REQUEST)
                action = str(payload.get("action") or "add").lower()
                if action == "add":
                    try:
                        item = manager.scheduler.add_schedule(
                            prompt=str(payload.get("prompt") or "").strip(),
                            run_at=payload.get("run_at"),
                            interval_seconds=payload.get("interval_seconds"),
                            session_id=payload.get("session_id"),
                            metadata=payload.get("metadata"),
                        )
                    except ValueError as exc:
                        return self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    self._audit_event({
                        "type": "schedule_add",
                        "schedule_id": item.schedule_id,
                        "session_id": item.session_id,
                    })
                    return self._send_json({"schedule": item.to_dict()})
                if action == "remove":
                    schedule_id = str(payload.get("schedule_id") or "").strip()
                    ok = manager.scheduler.remove_schedule(schedule_id)
                    self._audit_event({
                        "type": "schedule_remove",
                        "schedule_id": schedule_id,
                        "success": ok,
                    })
                    return self._send_json({"removed": ok})
                return self._send_json({"error": "invalid_action"}, status=HTTPStatus.BAD_REQUEST)

            if path == "/api/workflow":
                wf_path = str(payload.get("path") or "").strip()
                if not wf_path:
                    return self._send_json({"error": "path_required"}, status=HTTPStatus.BAD_REQUEST)
                session_id = payload.get("session_id")
                output_dir = getattr(manager.config.workflow, "output_dir", "outputs/workflows")
                if session_id:
                    _, session = manager.get_session(session_id)
                    runner = TaskRunner(session.agent, logger=logger, output_dir=output_dir)
                else:
                    memory = ConversationMemory()
                    memory.apply_config(manager.config.memory)
                    agent = BaseAgent(config=manager.config, profile=manager.profile, memory=memory)
                    runner = TaskRunner(agent, logger=logger, output_dir=output_dir)
                result = run_workflow(wf_path, runner, output_dir=output_dir)
                summary = [
                    {
                        "node_id": node.node_id,
                        "status": node.status,
                        "output_dir": node.output_dir,
                    }
                    for node in result.nodes
                ]
                return self._send_json({"workflow_id": result.workflow_id, "nodes": summary})

            if path == "/api/reset":
                session_id = str(payload.get("session_id") or "").strip()
                if not session_id:
                    return self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                ok = manager.reset_session(session_id)
                if not ok:
                    return self._send_json({"error": "session_not_found"}, status=HTTPStatus.NOT_FOUND)
                return self._send_json({"session_id": session_id, "reset": True})

            if path == "/api/chat":
                session_id = payload.get("session_id")
                client_id = payload.get("client_id")
                session_id, session = manager.get_session(session_id, client_id=client_id)
                continue_mode = bool(payload.get("continue"))
                if continue_mode:
                    resume_message_id = payload.get("resume_message_id")
                    resume_text = payload.get("resume_text")
                    message = self._build_continue_prompt(
                        session,
                        resume_message_id=resume_message_id,
                        resume_text=resume_text
                    )
                    if not message:
                        return self._send_json({"error": "continue_unavailable"}, status=HTTPStatus.BAD_REQUEST)
                else:
                    message = str(payload.get("message") or "").strip()
                    if not message:
                        return self._send_json({"error": "message_required"}, status=HTTPStatus.BAD_REQUEST)
                cmd, args, parse_error = (None, [], None) if continue_mode else self._parse_command(message)
                if cmd:
                    if parse_error:
                        return self._send_json({"error": parse_error}, status=HTTPStatus.BAD_REQUEST)
                    result = self._handle_command(session_id, session, cmd, args)
                    self._audit_event({
                        "type": "command",
                        "session_id": session_id,
                        "command": cmd,
                        "args": args,
                    })
                    self._persist_session(session)
                    return self._send_json(result)
                session.cancel_event.clear()
                session.last_partial_reply = ""
                if not continue_mode:
                    session.last_user_message = message
                with session.lock:
                    response = session.agent.run(message, stream=False, cancel_event=session.cancel_event)
                last_assistant = self._find_last_message(session.agent.memory, role="assistant")
                result = {
                    "session_id": session_id,
                    "success": getattr(response, "success", False),
                    "reply": getattr(response, "final_answer", ""),
                    "execution_time": getattr(response, "execution_time", 0),
                    "total_iterations": getattr(response, "total_iterations", 0),
                    "total_tokens_used": getattr(response, "total_tokens_used", 0),
                    "error_message": getattr(response, "error_message", None),
                    "assistant_message_id": getattr(last_assistant, "message_id", None),
                    "cancelled": getattr(response, "error_message", None) == "cancelled",
                }
                if result["cancelled"]:
                    session.last_partial_reply = result["reply"]
                else:
                    session.last_partial_reply = ""
                    session.last_reply = result["reply"]
                self._persist_session(session)
                self._audit_event({
                    "type": "chat",
                    "session_id": session_id,
                    "message": message,
                    "success": result["success"],
                    "cancelled": result["cancelled"],
                    "error": result["error_message"],
                })
                return self._send_json(result)

            return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)

        def _parse_command(self, raw: str) -> Tuple[Optional[str], List[str], Optional[str]]:
            text = (raw or "").strip()
            if not text.startswith("/"):
                return None, [], None
            try:
                parts = shlex.split(text[1:])
            except ValueError:
                return "__invalid__", [], "command_parse_error"
            if not parts:
                return None, [], None
            return parts[0].lower(), parts[1:], None

        def _handle_command(
            self,
            session_id: str,
            session: ChatSession,
            cmd: str,
            args: List[str]
        ) -> Dict[str, Any]:
            messages: List[str] = []
            payload: Dict[str, Any] = {"session_id": session_id, "command": cmd, "messages": messages}

            def emit(text: str) -> None:
                messages.append(text)

            memory = session.agent.memory

            if cmd in {"help", "?"}:
                emit("Commands: /help /reset /new /pin /unpin /pins /search /note /notes /docx /pdf /kb /workflow /schedule /mode /config /snapshot /rollback /plugins /reload /dashboard")
                return payload

            if cmd == "reset":
                manager.reset_session(session_id)
                emit("Session memory reset.")
                return payload

            if cmd in {"new", "session"}:
                new_session = manager.create_session()
                payload["session_id"] = new_session.session_id
                emit(f"New session created: {new_session.session_id}")
                return payload

            if cmd == "pin":
                target = args[0] if args else ""
                ok = False
                if target.isdigit():
                    ok = memory.pin_message_by_index(int(target))
                elif target:
                    ok = memory.pin_message(target)
                else:
                    last = self._find_last_message(memory, role="assistant")
                    if last:
                        ok = memory.pin_message(last.message_id)
                emit("Pinned." if ok else "Pin failed.")
                return payload

            if cmd == "unpin":
                target = args[0] if args else ""
                if target == "all":
                    memory.pinned_ids = []
                    emit("All pins cleared.")
                    return payload
                ok = memory.unpin_message(target)
                emit("Unpinned." if ok else "Unpin failed.")
                return payload

            if cmd == "pins":
                pins = memory.get_pinned_messages()
                if not pins:
                    emit("No pinned messages.")
                    return payload
                emit("Pinned messages:")
                for msg in pins:
                    emit(f"- [{msg.role}] {msg.message_id}: {truncate_text(msg.content, 120)}")
                return payload

            if cmd == "search":
                role = None
                if args and args[0] in {"user", "assistant", "system", "tool"}:
                    role = args[0]
                    args = args[1:]
                query = " ".join(args).strip()
                if not query:
                    emit("Search requires a query.")
                    return payload
                results = memory.search_messages(query, roles=[role] if role else None)
                if not results:
                    emit("No matches.")
                    return payload
                emit(f"Matches: {len(results)}")
                for item in results:
                    emit(f"- [{item['role']}] {item['message_id']}: {item['content']}")
                payload["data"] = {"results": results}
                return payload

            if cmd == "note":
                note_type = "project"
                if args and args[0] in {"project", "long", "long_term", "longterm"}:
                    note_type = args[0]
                    args = args[1:]
                raw = " ".join(args)
                if "::" in raw:
                    title, content = [part.strip() for part in raw.split("::", 1)]
                else:
                    title = args[0] if args else ""
                    content = " ".join(args[1:]) if len(args) > 1 else ""
                if not content:
                    emit("Note requires content.")
                    return payload
                if note_type in {"long", "long_term", "longterm"}:
                    note = memory.add_long_term_note(title, content)
                else:
                    note = memory.add_project_note(title, content)
                emit(f"Note saved: {note.note_id if note else 'failed'}")
                return payload

            if cmd == "notes":
                project = memory.list_project_notes()
                long_term = memory.list_long_term_notes()
                emit(f"Project notes: {len(project)} | Long-term notes: {len(long_term)}")
                for note in project[-3:]:
                    emit(f"- [Project] {note.title}: {truncate_text(note.content, 120)}")
                for note in long_term[-3:]:
                    emit(f"- [Long] {note.title}: {truncate_text(note.content, 120)}")
                return payload

            if cmd in {"docx", "pdf"}:
                doc_type = "docx" if cmd == "docx" else "pdf"
                raw = " ".join(args).strip()
                title = ""
                content = ""
                if "::" in raw:
                    title, content = [part.strip() for part in raw.split("::", 1)]
                else:
                    title = raw
                    content = session.last_reply or session.last_user_message or ""
                if not content:
                    emit("No content to export.")
                    return payload
                output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
                try:
                    document = generate_document(
                        content=content,
                        doc_type=doc_type,
                        output_dir=output_dir,
                        title=title or None,
                    )
                except (ValueError, ImportError) as exc:
                    emit(str(exc))
                    return payload
                summary = truncate_text(content, 1600)
                response = SimpleNamespace(
                    success=True,
                    final_answer=summary,
                    total_iterations=0,
                    execution_time=0,
                    error_message=None,
                )
                metadata = {
                    "source": "document",
                    "format": document.get("format"),
                    "title": document.get("title"),
                    "file": document.get("file_name"),
                    "tags": [document.get("format")],
                }
                save_task_result(
                    task_id=document["task_id"],
                    prompt=f"Document export ({document.get('format')})",
                    response=response,
                    output_dir=output_dir,
                    print_result=False,
                    record_history=True,
                    record_index=True,
                    metadata=metadata,
                )
                document_url = f"/api/artifact?task_id={document['task_id']}&name={document['file_name']}"
                payload["data"] = {
                    "document": {
                        "task_id": document.get("task_id"),
                        "name": document.get("file_name"),
                        "format": document.get("format"),
                        "title": document.get("title"),
                        "url": document_url,
                    }
                }
                emit(f"Document ready: {document.get('file_name')}")
                return payload

            if cmd == "kb":
                sub = args[0] if args else "search"
                rest = args[1:] if len(args) > 1 else []
                if sub == "search":
                    query = " ".join(rest).strip()
                    if not query:
                        emit("KB search requires a query.")
                        return payload
                    result = kb_search(query)
                    emit(f"KB results: {len(result.get('results', []))}")
                    for item in result.get("results", []):
                        emit(f"- {item.get('path')}: {item.get('snippet')}")
                    payload["data"] = result
                    return payload
                if sub == "index":
                    paths = rest or ["."]
                    result = index_paths(paths)
                    emit(f"KB indexed: +{result.get('updated', 0)}, skipped {result.get('skipped', 0)}")
                    payload["data"] = result
                    return payload
                if sub == "clear":
                    clear_index()
                    emit("KB index cleared.")
                    return payload
                emit("Unknown KB command.")
                return payload

            if cmd == "workflow":
                wf_path = " ".join(args).strip()
                if not wf_path:
                    emit("Workflow path required.")
                    return payload
                output_dir = getattr(manager.config.workflow, "output_dir", "outputs/workflows")
                runner = TaskRunner(session.agent, logger=logger, output_dir=output_dir)
                result = run_workflow(wf_path, runner, output_dir=output_dir)
                emit(f"Workflow finished: {result.workflow_id}")
                for node in result.nodes:
                    emit(f"- {node.node_id}: {node.status}")
                payload["data"] = {"workflow_id": result.workflow_id}
                return payload

            if cmd == "schedule":
                if not manager.scheduler:
                    emit("Scheduler disabled.")
                    return payload
                if not args or args[0] == "list":
                    schedules = [item.to_dict() for item in manager.scheduler.list_schedules()]
                    emit(f"Schedules: {len(schedules)}")
                    payload["data"] = {"schedules": schedules}
                    return payload
                if args[0] == "remove" and len(args) > 1:
                    ok = manager.scheduler.remove_schedule(args[1])
                    emit("Schedule removed." if ok else "Schedule not found.")
                    return payload
                if args[0] == "add" and len(args) > 2:
                    mode = args[1]
                    prompt = " ".join(args[3:]) if len(args) > 3 else ""
                    if not prompt:
                        emit("Schedule prompt required.")
                        return payload
                    try:
                        if mode == "in":
                            seconds = int(args[2])
                            item = manager.scheduler.add_schedule(prompt=prompt, interval_seconds=seconds, session_id=session_id)
                        elif mode == "at":
                            item = manager.scheduler.add_schedule(prompt=prompt, run_at=args[2], session_id=session_id)
                        else:
                            emit("Schedule format: /schedule add in 60 <prompt> or /schedule add at <iso_time> <prompt>")
                            return payload
                    except ValueError as exc:
                        emit(f"Schedule error: {exc}")
                        return payload
                    emit(f"Schedule added: {item.schedule_id}")
                    return payload
                emit("Schedule usage: /schedule list | /schedule remove <id> | /schedule add in/at ...")
                return payload

            if cmd == "mode":
                mode = args[0] if args else "balanced"
                overrides = {
                    "fast": {"agent": {"max_iterations": 60}, "memory": {"max_entries": 50}},
                    "balanced": {"agent": {"max_iterations": 120}, "memory": {"max_entries": 100}},
                    "quality": {"agent": {"max_iterations": 200}, "memory": {"max_entries": 160}},
                }
                if mode not in overrides:
                    emit("Mode options: fast | balanced | quality")
                    return payload
                manager.update_config(overrides[mode])
                emit(f"Mode switched to {mode}.")
                return payload

            if cmd == "config":
                emit("Config overrides loaded.")
                payload["data"] = {
                    "config": _safe_config_view(manager.config),
                    "overrides": manager.overrides.overrides,
                }
                return payload

            if cmd == "snapshot":
                label = " ".join(args).strip()
                snap = memory.create_snapshot(label=label)
                emit(f"Snapshot created: {snap.get('snapshot_id') if snap else 'failed'}")
                return payload

            if cmd == "rollback":
                if not args:
                    emit("Snapshot id required.")
                    return payload
                ok = memory.restore_snapshot(args[0])
                emit("Snapshot restored." if ok else "Snapshot restore failed.")
                return payload

            if cmd == "plugins":
                plugins = manager.list_plugins()
                emit(f"Plugins: {len(plugins)}")
                for item in plugins[:5]:
                    emit(f"- {item.get('name')}: {'signed' if item.get('signed') else 'unsigned'}")
                payload["data"] = {"plugins": plugins}
                return payload

            if cmd == "reload":
                if not manager.config.plugins.enabled:
                    emit("Plugins disabled.")
                    return payload
                result = manager.reload_plugins()
                emit(f"Reloaded plugins for {result.get('sessions', 0)} sessions.")
                return payload

            if cmd == "dashboard":
                url = manager.ensure_dashboard()
                if not url:
                    emit("Dashboard disabled.")
                    return payload
                emit(f"Dashboard ready: {url}")
                payload["data"] = {"url": url}
                return payload

            emit("Unknown command.")
            return payload

        def _find_last_message(self, memory: ConversationMemory, role: str) -> Optional[Any]:
            for msg in reversed(memory.messages):
                if msg.role == role:
                    return msg
            return None

        def _persist_session(self, session: ChatSession) -> None:
            if not manager.session_store_enabled:
                return
            try:
                snapshot = session.agent.memory.export_snapshot()
                save_session_snapshot(session.session_id, snapshot, manager.session_store_dir)
            except Exception as exc:
                logger.debug(f"保存会话快照失败: {exc}")

        def _audit_event(self, event: Dict[str, Any]) -> None:
            if not manager.audit_enabled:
                return
            try:
                if manager.audit_redact:
                    event = redact_sensitive_payload(event)
                append_audit_event(event, manager.audit_path)
            except Exception as exc:
                logger.debug(f"写入审计失败: {exc}")

        def _log_webhook(self, entry: Dict[str, Any]) -> None:
            try:
                append_webhook_log(WEBHOOK_LOG_PATH, entry)
            except Exception as exc:
                logger.debug(f"写入Webhook日志失败: {exc}")

        def _enqueue_webhook_prompt(self, prompt: str, session_id: Optional[str]) -> Dict[str, Any]:
            if manager.scheduler:
                try:
                    item = manager.scheduler.add_schedule(
                        prompt=prompt,
                        run_at=datetime.now().isoformat(),
                        session_id=session_id,
                        metadata={"job": "webhook"},
                    )
                    return {"queued": True, "schedule_id": item.schedule_id}
                except Exception as exc:
                    return {"queued": False, "error": str(exc)}
            thread = threading.Thread(
                target=self._run_webhook_prompt,
                args=(prompt, session_id),
                daemon=True
            )
            thread.start()
            return {"queued": False, "running": True}

        def _run_webhook_prompt(self, prompt: str, session_id: Optional[str]) -> None:
            output_dir = getattr(manager.config.artifacts, "output_dir", "outputs")
            metadata = {"source": "webhook"}
            task_id = f"webhook_{uuid.uuid4().hex}"
            if session_id and manager.get_status(session_id):
                session_id, session = manager.get_session(session_id)
                with session.lock:
                    runner = TaskRunner(session.agent, logger=logger, output_dir=output_dir)
                    task = TaskSpec(task_id=task_id, prompt=prompt, metadata=metadata)
                    result = runner.run_task(task, preprocess=False)
                    runner.save_result(result, print_result=False)
            else:
                memory = ConversationMemory()
                memory.apply_config(manager.config.memory)
                agent = BaseAgent(config=manager.config, profile=manager.profile, memory=memory)
                runner = TaskRunner(agent, logger=logger, output_dir=output_dir)
                task = TaskSpec(task_id=task_id, prompt=prompt, metadata=metadata)
                result = runner.run_task(task, preprocess=False)
                runner.save_result(result, print_result=False)
            if manager.audit_enabled:
                event = {
                    "type": "webhook_prompt",
                    "session_id": session_id,
                    "task_id": task_id,
                    "success": getattr(result.response, "success", False),
                }
                if manager.audit_redact:
                    event = redact_sensitive_payload(event)
                append_audit_event(event, manager.audit_path)

        def _search_artifacts(
            self,
            query: str,
            filters: Dict[str, Any],
            output_dir: str
        ) -> List[Dict[str, Any]]:
            query_lower = (query or "").lower()
            records = manager.get_artifact_index()
            results = []
            for entry in records:
                if not isinstance(entry, dict):
                    continue
                if not self._artifact_match(entry, query_lower, filters):
                    continue
                results.append(entry)
            results.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
            return results[:50]

        def _artifact_match(self, entry: Dict[str, Any], query_lower: str, filters: Dict[str, Any]) -> bool:
            if query_lower:
                hay = " ".join([
                    str(entry.get("prompt") or ""),
                    str(entry.get("final_answer") or ""),
                    json.dumps(entry.get("metadata", {}), ensure_ascii=False),
                ]).lower()
                if query_lower not in hay:
                    return False
            success = filters.get("success")
            if success is not None:
                if bool(entry.get("success")) != bool(success):
                    return False
            source = filters.get("source")
            if source:
                meta_source = (entry.get("metadata") or {}).get("source")
                if meta_source != source:
                    return False
            tag = filters.get("tag")
            if tag:
                tags = (entry.get("metadata") or {}).get("tags") or []
                if tag not in tags:
                    return False
            date_from = filters.get("from")
            date_to = filters.get("to")
            ts = entry.get("timestamp")
            if ts:
                if date_from and ts < date_from:
                    return False
                if date_to and ts > date_to:
                    return False
            return True

        def _diff_artifacts(self, left: str, right: str, output_dir: str) -> Dict[str, Any]:
            left_path = self._resolve_artifact_path(left, output_dir)
            right_path = self._resolve_artifact_path(right, output_dir)
            if not left_path or not right_path:
                return {"error": "invalid_path"}
            try:
                left_text = left_path.read_text(encoding="utf-8", errors="replace").splitlines()
                right_text = right_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception as exc:
                return {"error": str(exc)}
            import difflib
            diff = difflib.unified_diff(
                left_text,
                right_text,
                fromfile=str(left_path.name),
                tofile=str(right_path.name),
                lineterm="",
            )
            diff_lines = list(diff)
            return {"diff": diff_lines[:400], "left": left, "right": right}

        def _diff_artifacts_bundle(self, left: str, right: str, output_dir: str) -> Dict[str, Any]:
            if not left or not right:
                return {"error": "invalid_path"}
            left_dir = Path(output_dir) / left
            right_dir = Path(output_dir) / right
            if not left_dir.exists() or not right_dir.exists():
                return {"error": "task_not_found"}
            left_files = {str(p.relative_to(left_dir)) for p in left_dir.rglob("*") if p.is_file()}
            right_files = {str(p.relative_to(right_dir)) for p in right_dir.rglob("*") if p.is_file()}
            all_files = sorted(left_files | right_files)
            results = []
            for name in all_files:
                if name in left_files and name in right_files:
                    diff = self._diff_artifacts(f"{left}/{name}", f"{right}/{name}", output_dir)
                    results.append({
                        "name": name,
                        "status": "both",
                        "diff": diff.get("diff", []),
                    })
                elif name in left_files:
                    results.append({"name": name, "status": "left_only", "diff": []})
                else:
                    results.append({"name": name, "status": "right_only", "diff": []})
            return {"left": left, "right": right, "files": results}

        def _create_bundle_archive(
            self,
            task_ids: List[str],
            output_dir: str,
            archive_dir: str
        ) -> Tuple[Optional[str], List[str]]:
            if not task_ids:
                return None, []
            archive_path = Path(archive_dir)
            archive_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            bundle_name = archive_path / f"bundle_{timestamp}.zip"
            skipped: List[str] = []
            with zipfile.ZipFile(bundle_name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for task_id in task_ids:
                    task_dir = Path(output_dir) / task_id
                    if not task_dir.exists() or not task_dir.is_dir():
                        skipped.append(task_id)
                        continue
                    for file_path in task_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = f"{task_id}/{file_path.relative_to(task_dir)}"
                            zf.write(file_path, arcname)
            return str(bundle_name), skipped

        def _resolve_artifact_path(self, value: str, output_dir: str) -> Optional[Path]:
            if not value:
                return None
            if "/" in value:
                task_id, name = value.split("/", 1)
            else:
                task_id = value
                name = "result.json"
            if not task_id or not name:
                return None
            base = Path(output_dir) / task_id
            target = (base / name).resolve()
            if not str(target).startswith(str(base.resolve())):
                return None
            if not target.exists() or not target.is_file():
                return None
            return target

        def _list_memory_archives(self, archive_dir: str) -> List[Dict[str, Any]]:
            base = Path(archive_dir)
            if not base.exists():
                return []
            items = []
            for entry in sorted(base.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    stamp = datetime.fromtimestamp(entry.stat().st_mtime).isoformat()
                except Exception:
                    stamp = ""
                items.append({
                    "name": entry.name,
                    "timestamp": stamp,
                })
            return items

        def _resolve_archive_path(self, name: str, archive_dir: str) -> Optional[Path]:
            if not name:
                return None
            base = Path(archive_dir).resolve()
            target = (base / name).resolve()
            if not str(target).startswith(str(base)):
                return None
            if not target.exists() or not target.is_file():
                return None
            return target

        def _load_audit_events(self, limit: int, session_id: Optional[str]) -> List[Dict[str, Any]]:
            if not manager.audit_enabled:
                return []
            path = Path(manager.audit_path)
            if not path.exists():
                return []
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
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
                if session_id and data.get("session_id") != session_id:
                    continue
                entries.append(data)
            return entries

        def _load_tool_metrics(self, output_dir: str) -> Dict[str, Any]:
            metrics_path = Path(output_dir) / "tool_metrics.json"
            if not metrics_path.exists():
                return {"summary": {}, "tools": {}}
            try:
                data = json.loads(metrics_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                return {"summary": {}, "tools": {}}
            return {"summary": {}, "tools": {}}

        def _load_recent_task_times(self, output_dir: str, limit: int = 30) -> List[Dict[str, Any]]:
            history_path = Path(output_dir) / "task_history.jsonl"
            if not history_path.exists():
                return []
            try:
                lines = history_path.read_text(encoding="utf-8").splitlines()
            except Exception:
                return []
            if limit > 0:
                lines = lines[-limit:]
            items = []
            for line in lines:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                items.append({
                    "task_id": data.get("task_id"),
                    "timestamp": data.get("timestamp"),
                    "execution_time": data.get("execution_time"),
                    "success": data.get("success"),
                })
            return items

        def _send_sse_headers(self) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

        def _send_sse_event(self, payload: Dict[str, Any]) -> bool:
            try:
                data = json.dumps(payload, ensure_ascii=False)
                self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                self.wfile.flush()
                return True
            except Exception:
                return False

        def _chunk_text(self, text: str, size: int = 80) -> List[str]:
            if not text:
                return []
            if size <= 0:
                return [text]
            return [text[i:i + size] for i in range(0, len(text), size)]

        def _build_continue_prompt(
            self,
            session: ChatSession,
            resume_message_id: Optional[str] = None,
            resume_text: Optional[str] = None
        ) -> Optional[str]:
            base_reply = resume_text or session.last_partial_reply or session.last_reply
            if not base_reply and resume_message_id:
                msg = session.agent.memory.get_message_by_id(resume_message_id)
                if msg and msg.content:
                    base_reply = msg.content
            if not base_reply:
                return None
            user_message = session.last_user_message or ""
            lines = [
                "Continue the previous response from where it stopped.",
            ]
            if user_message:
                lines.extend(["", "Last user message:", user_message])
            lines.extend(["", "Partial response:", base_reply, "", "Continue:"])
            return "\n".join(lines)

        def _handle_chat_stream(self, payload: Dict[str, Any]) -> None:
            session_id = payload.get("session_id")
            client_id = payload.get("client_id")
            session_id, session = manager.get_session(session_id, client_id=client_id)
            continue_mode = bool(payload.get("continue"))
            if continue_mode:
                resume_message_id = payload.get("resume_message_id")
                resume_text = payload.get("resume_text")
                message = self._build_continue_prompt(
                    session,
                    resume_message_id=resume_message_id,
                    resume_text=resume_text
                )
                if not message:
                    return self._send_json({"error": "continue_unavailable"}, status=HTTPStatus.BAD_REQUEST)
            else:
                message = str(payload.get("message") or "").strip()
                if not message:
                    return self._send_json({"error": "message_required"}, status=HTTPStatus.BAD_REQUEST)
            cmd, args, parse_error = (None, [], None) if continue_mode else self._parse_command(message)

            self._send_sse_headers()
            meta = {
                "type": "meta",
                "payload": {
                    "session_id": session_id,
                    "max_iterations": session.agent.config.agent.max_iterations,
                    "model": session.agent.config.model.effective_model_name,
                    "streaming": True,
                },
            }
            if not self._send_sse_event(meta):
                return None

            if cmd:
                if parse_error:
                    self._send_sse_event({"type": "error", "payload": {"message": parse_error}})
                    self._send_sse_event({"type": "done", "payload": {"session_id": session_id}})
                    return None
                result = self._handle_command(session_id, session, cmd, args)
                self._audit_event({
                    "type": "command",
                    "session_id": session_id,
                    "command": cmd,
                    "args": args,
                })
                self._persist_session(session)
                self._send_sse_event({"type": "command", "payload": result})
                self._send_sse_event({"type": "done", "payload": {"session_id": session_id}})
                return None

            session.cancel_event.clear()
            session.last_partial_reply = ""
            if not continue_mode:
                session.last_user_message = message

            event_queue: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()
            partial_parts: List[str] = []

            def enqueue(event_type: str, payload_data: Optional[Dict[str, Any]] = None) -> None:
                event_queue.put({"type": event_type, "payload": payload_data or {}})

            def run_agent() -> None:
                try:
                    def on_delta(text: Optional[str] = None, **_: Any) -> None:
                        if text:
                            partial_parts.append(text)
                            session.last_partial_reply += text
                        enqueue("delta", {"text": text or ""})

                    session.agent.set_ui_hooks({
                        "llm_start": lambda iteration=None, **_: enqueue("llm_start", {"iteration": iteration}),
                        "llm_end": lambda iteration=None, **_: enqueue("llm_end", {"iteration": iteration}),
                        "thinking": lambda thinking=None, step=None, **_: enqueue("thinking", {"step": step, "thinking": thinking}),
                        "tool_start": lambda tool_name=None, arguments=None, call_id=None, **_: enqueue(
                            "tool_start",
                            {"tool": tool_name, "call_id": call_id}
                        ),
                        "tool_end": lambda tool_name=None, result=None, call_id=None, **_: enqueue(
                            "tool_end",
                            {"tool": tool_name, "call_id": call_id, "status": getattr(result, "status", None)}
                        ),
                        "delta": on_delta,
                    })
                    with session.lock:
                        response = session.agent.run(message, stream=True, cancel_event=session.cancel_event)
                    last_assistant = self._find_last_message(session.agent.memory, role="assistant")
                    partial_text = "".join(partial_parts).strip()
                    result = {
                        "session_id": session_id,
                        "success": getattr(response, "success", False),
                        "reply": getattr(response, "final_answer", "") or partial_text,
                        "execution_time": getattr(response, "execution_time", 0),
                        "total_iterations": getattr(response, "total_iterations", 0),
                        "total_tokens_used": getattr(response, "total_tokens_used", 0),
                        "error_message": getattr(response, "error_message", None),
                        "assistant_message_id": getattr(last_assistant, "message_id", None),
                    }
                    cancelled = result["error_message"] == "cancelled"
                    if cancelled:
                        session.last_partial_reply = result["reply"]
                    else:
                        session.last_partial_reply = ""
                        session.last_reply = result["reply"]
                    result["cancelled"] = cancelled
                    enqueue("done", result)
                    self._audit_event({
                        "type": "chat",
                        "session_id": session_id,
                        "success": result["success"],
                        "message": message,
                        "cancelled": cancelled,
                    })
                    self._persist_session(session)
                except AgentCancelled as exc:
                    partial_text = "".join(partial_parts).strip()
                    session.last_partial_reply = partial_text
                    enqueue("done", {
                        "session_id": session_id,
                        "success": False,
                        "reply": partial_text,
                        "execution_time": 0,
                        "total_iterations": session.agent.current_step,
                        "total_tokens_used": 0,
                        "error_message": "cancelled",
                        "assistant_message_id": None,
                        "cancelled": True,
                    })
                except Exception as exc:
                    enqueue("error", {"message": str(exc)})
                finally:
                    session.agent.set_ui_hooks({})
                    event_queue.put(None)

            thread = threading.Thread(target=run_agent, daemon=True)
            thread.start()

            keepalive_seconds = 1.2
            while True:
                try:
                    event = event_queue.get(timeout=keepalive_seconds)
                except queue.Empty:
                    if not self._send_sse_event({"type": "ping", "payload": {"ts": time.time()}}):
                        break
                    continue
                if event is None:
                    break
                if not self._send_sse_event(event):
                    break
            return None

        def log_message(self, format: str, *args) -> None:
            logger.debug(format % args)

        def _read_json(self, max_size: int) -> Tuple[Dict[str, Any], Optional[str]]:
            length = self.headers.get("Content-Length")
            if not length:
                return {}, None
            try:
                size = int(length)
            except ValueError:
                return {}, "invalid_content_length"
            if size <= 0:
                return {}, None
            if size > max_size:
                return {}, "payload_too_large"
            try:
                raw = self.rfile.read(size)
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                return {}, "invalid_json"
            if not isinstance(data, dict):
                return {}, "invalid_json"
            return data, None

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_text(self, text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_static_file(self, name: str, base: Path) -> None:
            base_root = base.resolve()
            file_path = (base / name).resolve()
            if not str(file_path).startswith(str(base_root)):
                return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)
            if file_path.is_dir():
                file_path = (file_path / "index.html").resolve()
                if not str(file_path).startswith(str(base_root)):
                    return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)
            if not file_path.exists():
                return self._send_text("Not Found", status=HTTPStatus.NOT_FOUND)

            mime, _ = mimetypes.guess_type(file_path.name)
            if not mime:
                mime = "application/octet-stream"
            if file_path.name == "index.html":
                text = file_path.read_text(encoding="utf-8")
                text = text.replace("{{CHAT_TITLE}}", title)
                data = text.encode("utf-8")
            else:
                data = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            if mime.startswith("text/"):
                self.send_header("Content-Type", f"{mime}; charset=utf-8")
            else:
                self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return ChatHandler
