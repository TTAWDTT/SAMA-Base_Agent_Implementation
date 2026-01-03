# ==============================================================================
# 对话记忆模块
# ==============================================================================
# 管理智能体的对话历史和上下文
# ==============================================================================

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import get_config
from src.utils.helpers import estimate_tokens, truncate_text


@dataclass
class FileContext:
    """
    文件上下文

    管理智能体工作过程中涉及的文件
    """
    path: str
    content: Optional[str] = None
    abstract: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "path": self.path,
            "content": self.content,
            "abstract": self.abstract,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def get_summary(self) -> str:
        """获取文件摘要信息"""
        size_info = f"({len(self.content)} 字符)" if self.content else "(无内容)"
        return f"{self.path} {size_info}: {self.abstract}"


@dataclass
class Message:
    """
    消息数据类

    表示对话中的单条消息
    """
    role: str  # "user", "assistant", "system", "tool"
    content: str
    message_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "role": self.role,
            "content": self.content,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def to_openai_format(self) -> Dict[str, Any]:
        """
        转换为OpenAI API格式

        Returns:
            Dict: OpenAI格式的消息
        """
        msg: Dict[str, Any] = {"role": self.role, "content": self.content}

        if self.role == "tool":
            if self.metadata.get("tool_name"):
                msg["name"] = self.metadata["tool_name"]
            if self.metadata.get("tool_call_id"):
                msg["tool_call_id"] = self.metadata["tool_call_id"]
        elif self.role == "assistant" and self.metadata.get("tool_calls"):
            msg["tool_calls"] = self.metadata["tool_calls"]

        return msg


@dataclass
class MemoryNote:
    """
    记忆片段
    """
    note_id: str
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "manual"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "note_id": self.note_id,
            "title": self.title,
            "content": self.content,
            "tags": list(self.tags),
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


class ConversationMemory:
    """
    对话记忆类

    管理对话历史，支持添加、检索和清理消息
    """
    
    def __init__(self, max_entries: Optional[int] = None):
        """
        初始化对话记忆

        Args:
            max_entries: 最大记忆条数
        """
        config = get_config()
        self.max_entries = max_entries or config.memory.max_entries
        self.max_context_tokens = config.memory.max_context_tokens
        self.memory_type = config.memory.type
        self.summary_keep_last_n = config.memory.summary_keep_last_n
        self.summary_max_chars = config.memory.summary_max_chars
        self.system_token_ratio = config.memory.system_token_ratio
        self.file_context_token_ratio = config.memory.file_context_token_ratio
        self.history_token_ratio = config.memory.history_token_ratio
        self.file_context_chunk_size = config.memory.file_context_chunk_size
        self.file_context_max_chunks_per_file = config.memory.file_context_max_chunks_per_file
        self.file_context_min_score = config.memory.file_context_min_score
        self.file_context_query_messages = config.memory.file_context_query_messages
        self.history_retrieval_enabled = config.memory.history_retrieval_enabled
        self.history_retrieval_token_ratio = config.memory.history_retrieval_token_ratio
        self.history_retrieval_max_messages = config.memory.history_retrieval_max_messages
        self.history_retrieval_min_score = config.memory.history_retrieval_min_score
        self.history_retrieval_query_messages = config.memory.history_retrieval_query_messages
        self.history_retrieval_include_roles = config.memory.history_retrieval_include_roles
        self.project_notes_enabled = config.memory.project_notes_enabled
        self.project_notes_max = config.memory.project_notes_max
        self.long_term_enabled = config.memory.long_term_enabled
        self.long_term_max = config.memory.long_term_max
        self.notes_max_tokens = config.memory.notes_max_tokens
        self.auto_note_interval = config.memory.auto_note_interval
        self.auto_note_min_messages = config.memory.auto_note_min_messages
        self.auto_note_max_messages = config.memory.auto_note_max_messages
        self.auto_note_max_chars = config.memory.auto_note_max_chars
        self.pins_enabled = config.memory.pins_enabled
        self.pins_max = config.memory.pins_max
        self.search_max_results = config.memory.search_max_results
        self.dedup_enabled = config.memory.dedup_enabled
        self.dedup_window = config.memory.dedup_window
        self.auto_tag_enabled = config.memory.auto_tag_enabled
        self.auto_tag_max = config.memory.auto_tag_max
        self.snapshot_enabled = config.memory.snapshot_enabled
        self.snapshot_max = config.memory.snapshot_max
        self.archive_on_reset = config.memory.archive_on_reset
        self.archive_dir = config.memory.archive_dir
        self.messages: List[Message] = []
        self.system_message: Optional[Message] = None
        self.files: Dict[str, FileContext] = {}  # 文件上下文字典，key为文件路径
        self.summary = ""
        self.project_notes: List[MemoryNote] = []
        self.long_term_notes: List[MemoryNote] = []
        self.pinned_ids: List[str] = []
        self.snapshots: List[Dict[str, Any]] = []
        self._message_counter = 0
        self._note_counter = 0
        self._last_auto_note_count = 0
        self._recent_hashes: List[str] = []
        self.dedup_hits = 0
        self.dedup_total = 0
        self.last_context_report: Dict[str, Any] = {}

    def apply_config(self, config) -> None:
        """
        应用新的记忆配置
        """
        if not config:
            return
        self.max_entries = getattr(config, "max_entries", self.max_entries)
        self.max_context_tokens = getattr(config, "max_context_tokens", self.max_context_tokens)
        self.memory_type = getattr(config, "type", self.memory_type)
        self.summary_keep_last_n = getattr(config, "summary_keep_last_n", self.summary_keep_last_n)
        self.summary_max_chars = getattr(config, "summary_max_chars", self.summary_max_chars)
        self.system_token_ratio = getattr(config, "system_token_ratio", self.system_token_ratio)
        self.file_context_token_ratio = getattr(config, "file_context_token_ratio", self.file_context_token_ratio)
        self.history_token_ratio = getattr(config, "history_token_ratio", self.history_token_ratio)
        self.file_context_chunk_size = getattr(config, "file_context_chunk_size", self.file_context_chunk_size)
        self.file_context_max_chunks_per_file = getattr(config, "file_context_max_chunks_per_file", self.file_context_max_chunks_per_file)
        self.file_context_min_score = getattr(config, "file_context_min_score", self.file_context_min_score)
        self.file_context_query_messages = getattr(config, "file_context_query_messages", self.file_context_query_messages)
        self.history_retrieval_enabled = getattr(config, "history_retrieval_enabled", self.history_retrieval_enabled)
        self.history_retrieval_token_ratio = getattr(config, "history_retrieval_token_ratio", self.history_retrieval_token_ratio)
        self.history_retrieval_max_messages = getattr(config, "history_retrieval_max_messages", self.history_retrieval_max_messages)
        self.history_retrieval_min_score = getattr(config, "history_retrieval_min_score", self.history_retrieval_min_score)
        self.history_retrieval_query_messages = getattr(config, "history_retrieval_query_messages", self.history_retrieval_query_messages)
        self.history_retrieval_include_roles = getattr(config, "history_retrieval_include_roles", self.history_retrieval_include_roles)
        self.project_notes_enabled = getattr(config, "project_notes_enabled", self.project_notes_enabled)
        self.project_notes_max = getattr(config, "project_notes_max", self.project_notes_max)
        self.long_term_enabled = getattr(config, "long_term_enabled", self.long_term_enabled)
        self.long_term_max = getattr(config, "long_term_max", self.long_term_max)
        self.notes_max_tokens = getattr(config, "notes_max_tokens", self.notes_max_tokens)
        self.auto_note_interval = getattr(config, "auto_note_interval", self.auto_note_interval)
        self.auto_note_min_messages = getattr(config, "auto_note_min_messages", self.auto_note_min_messages)
        self.auto_note_max_messages = getattr(config, "auto_note_max_messages", self.auto_note_max_messages)
        self.auto_note_max_chars = getattr(config, "auto_note_max_chars", self.auto_note_max_chars)
        self.pins_enabled = getattr(config, "pins_enabled", self.pins_enabled)
        self.pins_max = getattr(config, "pins_max", self.pins_max)
        self.search_max_results = getattr(config, "search_max_results", self.search_max_results)
        self.dedup_enabled = getattr(config, "dedup_enabled", self.dedup_enabled)
        self.dedup_window = getattr(config, "dedup_window", self.dedup_window)
        self.auto_tag_enabled = getattr(config, "auto_tag_enabled", self.auto_tag_enabled)
        self.auto_tag_max = getattr(config, "auto_tag_max", self.auto_tag_max)
        self.snapshot_enabled = getattr(config, "snapshot_enabled", self.snapshot_enabled)
        self.snapshot_max = getattr(config, "snapshot_max", self.snapshot_max)
        self.archive_on_reset = getattr(config, "archive_on_reset", self.archive_on_reset)
        self.archive_dir = getattr(config, "archive_dir", self.archive_dir)
    
    def set_system_message(self, content: str) -> None:
        """
        设置系统消息

        系统消息始终位于对话开头

        Args:
            content: 系统消息内容
        """
        self.system_message = Message(role="system", content=content)
    
    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        添加用户消息

        Args:
            content: 消息内容
            metadata: 元数据
        """
        self._add_message("user", content, metadata)
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        添加助手消息

        Args:
            content: 消息内容
            metadata: 元数据
        """
        self._add_message("assistant", content, metadata)
    
    def add_tool_message(self, content: str, tool_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        添加工具消息

        Args:
            content: 消息内容
            tool_name: 工具名称
            metadata: 元数据
        """
        meta = metadata or {}
        meta["tool_name"] = tool_name
        self._add_message("tool", content, meta)
    
    def _add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        内部方法：添加消息

        Args:
            role: 角色
            content: 内容
            metadata: 元数据
        """
        if self.dedup_enabled:
            self.dedup_total += 1
            if self._is_duplicate(role, content):
                self.dedup_hits += 1
                return
        message_id = self._next_message_id()
        message = Message(
            role=role,
            content=content,
            message_id=message_id,
            metadata=metadata or {}
        )
        if self.auto_tag_enabled and "tags" not in message.metadata:
            message.metadata["tags"] = self._extract_query_terms(content)[: self.auto_tag_max]
        message.metadata.setdefault("message_id", message_id)
        self.messages.append(message)
        
        # 根据记忆类型处理长度
        if self.memory_type == "summary":
            self._summarize_if_needed()
        else:
            # 如果超过最大条数，删除最早的消息（保留系统消息）
            while len(self.messages) > self.max_entries:
                self.messages.pop(0)
        self._sync_pins()
        self._maybe_add_auto_note()
    
    def get_messages(self) -> List[Message]:
        """
        获取所有消息（包括系统消息）

        Returns:
            List[Message]: 消息列表
        """
        if self.system_message:
            return [self.system_message] + self.messages
        return self.messages
    
    def get_openai_messages(self) -> List[Dict[str, str]]:
        """
        获取OpenAI格式的消息列表（包含文件上下文）

        消息顺序：
        1. 系统消息
        2. 摘要消息（可选）
        3. 文件内容消息（可选）
        4. 对话历史

        Returns:
            List[Dict]: OpenAI格式的消息列表
        """
        system_messages: List[Dict[str, Any]] = []
        summary_message: Optional[Dict[str, Any]] = None
        notes_message: Optional[Dict[str, Any]] = None

        # 1. 添加系统消息
        if self.system_message:
            system_messages.append(self.system_message.to_openai_format())

        # 2. 构建摘要消息（可选）
        if self.summary:
            summary_message = {
                "role": "system",
                "content": "## 对话摘要\n" + self.summary
            }

        # 2.5 构建记忆片段（可选）
        notes_message = self._build_notes_message()

        # 3. 构建对话历史
        history_records = list(self.messages)

        file_query_text = self._get_recent_user_text(self.file_context_query_messages)
        retrieval_query_text = self._get_recent_user_text(self.history_retrieval_query_messages)
        messages, report = self._trim_messages_to_token_limit(
            system_messages,
            summary_message,
            notes_message,
            history_records,
            file_query_text,
            retrieval_query_text
        )
        self.last_context_report = report
        return messages

    def _trim_messages_to_token_limit(
        self,
        system_messages: List[Dict[str, Any]],
        summary_message: Optional[Dict[str, Any]],
        notes_message: Optional[Dict[str, Any]],
        history_records: List[Message],
        file_query_text: str,
        retrieval_query_text: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        根据分层预算裁剪消息
        """
        def _msg_tokens(msg: Dict[str, Any]) -> int:
            return estimate_tokens(msg.get("content", "") or "")

        report: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "budgets": {},
            "tokens": {},
            "summary_included": False,
            "notes_included": False,
            "retrieval": {"count": 0, "message_ids": []},
            "file_context": {"count": 0, "paths": []},
            "history": {"count": 0, "message_ids": []},
        }

        if not self.max_context_tokens:
            retrieval_message = None
            retrieval_ids: List[str] = []
            if self.history_retrieval_enabled:
                retrieval_message, retrieval_ids = self._build_history_retrieval_message_with_report(retrieval_query_text)
            file_context_msg, file_paths = self._build_file_context_message_with_report(query_text=file_query_text)
            history_messages = [msg.to_openai_format() for msg in history_records]
            messages = list(system_messages)
            if summary_message:
                messages.append(summary_message)
                report["summary_included"] = True
            if notes_message:
                messages.append(notes_message)
                report["notes_included"] = True
            if retrieval_message:
                messages.append(retrieval_message)
            if file_context_msg:
                messages.append(file_context_msg)
            messages.extend(history_messages)
            report["retrieval"] = {"count": len(retrieval_ids), "message_ids": retrieval_ids}
            report["file_context"] = {"count": len(file_paths), "paths": file_paths}
            report["history"] = {
                "count": len(history_records),
                "message_ids": [msg.message_id for msg in history_records if msg.message_id],
            }
            report["tokens"]["total"] = sum(_msg_tokens(msg) for msg in messages)
            return messages, report

        messages = list(system_messages)
        report["budgets"]["total"] = self.max_context_tokens

        # 控制系统摘要预算
        system_budget = int(self.max_context_tokens * max(self.system_token_ratio, 0.0))
        if system_budget < 0:
            system_budget = 0
        if summary_message:
            if sum(_msg_tokens(msg) for msg in messages + [summary_message]) <= system_budget:
                messages.append(summary_message)
                report["summary_included"] = True

        remaining_system = system_budget - sum(_msg_tokens(msg) for msg in messages)
        if notes_message and remaining_system > 0:
            trimmed_notes = self._trim_message_to_tokens(notes_message, remaining_system)
            if trimmed_notes:
                messages.append(trimmed_notes)
                report["notes_included"] = True

        system_tokens = sum(_msg_tokens(msg) for msg in messages)
        report["budgets"]["system"] = system_budget
        report["tokens"]["system"] = system_tokens
        remaining = self.max_context_tokens - system_tokens
        if remaining <= 0:
            report["tokens"]["total"] = system_tokens
            return messages, report

        retrieval_ratio, file_ratio, history_ratio = self._normalize_budget_ratios(
            self.history_retrieval_token_ratio if self.history_retrieval_enabled else 0.0,
            self.file_context_token_ratio,
            self.history_token_ratio
        )
        retrieval_budget = int(remaining * retrieval_ratio)
        if self.history_retrieval_enabled and retrieval_budget > 0:
            retrieval_message, retrieval_ids = self._build_history_retrieval_message_with_report(
                retrieval_query_text,
                max_tokens=retrieval_budget
            )
            if retrieval_message:
                messages.append(retrieval_message)
                remaining -= _msg_tokens(retrieval_message)
                report["retrieval"] = {"count": len(retrieval_ids), "message_ids": retrieval_ids}
                report["tokens"]["retrieval"] = _msg_tokens(retrieval_message)
            report["budgets"]["retrieval"] = retrieval_budget

        file_budget = int(remaining * file_ratio)
        file_context_msg, file_paths = self._build_file_context_message_with_report(
            query_text=file_query_text,
            max_tokens=file_budget if file_budget > 0 else 0
        )
        if file_context_msg:
            messages.append(file_context_msg)
            remaining -= _msg_tokens(file_context_msg)
            report["file_context"] = {"count": len(file_paths), "paths": file_paths}
            report["tokens"]["file"] = _msg_tokens(file_context_msg)
        report["budgets"]["file"] = file_budget

        history_budget = max(0, remaining)
        report["budgets"]["history"] = history_budget
        history_selected = self._trim_history_records(history_records, history_budget)
        messages.extend([msg.to_openai_format() for msg in history_selected])
        report["history"] = {
            "count": len(history_selected),
            "message_ids": [msg.message_id for msg in history_selected if msg.message_id],
        }
        report["tokens"]["history"] = sum(estimate_tokens(msg.content or "") for msg in history_selected)
        report["tokens"]["total"] = sum(_msg_tokens(msg) for msg in messages)
        return messages, report
    
    def _normalize_budget_ratios(
        self,
        retrieval_ratio: float,
        file_ratio: float,
        history_ratio: float
    ) -> Tuple[float, float, float]:
        """
        归一化检索、文件与历史预算比例
        """
        safe_retrieval = max(retrieval_ratio, 0.0)
        safe_file = max(file_ratio, 0.0)
        safe_history = max(history_ratio, 0.0)
        total = safe_retrieval + safe_file + safe_history
        if total <= 0:
            return 0.15, 0.35, 0.5
        return (
            safe_retrieval / total,
            safe_file / total,
            safe_history / total,
        )

    def _trim_history_messages(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int
    ) -> List[Dict[str, Any]]:
        """
        按预算裁剪对话历史
        """
        if max_tokens <= 0:
            return []
        kept = []
        total = 0
        for msg in reversed(messages):
            msg_tokens = estimate_tokens(msg.get("content", "") or "")
            if total + msg_tokens > max_tokens:
                break
            kept.append(msg)
            total += msg_tokens
        kept.reverse()
        return kept

    def _trim_history_records(
        self,
        records: List[Message],
        max_tokens: int
    ) -> List[Message]:
        """
        按预算裁剪对话历史（基于Message对象）
        """
        if max_tokens <= 0:
            return []
        kept: List[Message] = []
        total = 0
        for msg in reversed(records):
            msg_tokens = estimate_tokens(msg.content or "")
            if total + msg_tokens > max_tokens:
                break
            kept.append(msg)
            total += msg_tokens
        kept.reverse()
        return kept

    def _trim_message_to_tokens(
        self,
        message: Dict[str, Any],
        max_tokens: int
    ) -> Optional[Dict[str, Any]]:
        """
        将单条消息裁剪到预算内
        """
        if not message or max_tokens <= 0:
            return None
        content = message.get("content", "") or ""
        if estimate_tokens(content) <= max_tokens:
            return message
        ratio = max_tokens / max(estimate_tokens(content), 1)
        target_len = max(1, int(len(content) * ratio))
        trimmed = truncate_text(content, target_len)
        return {"role": message.get("role", "system"), "content": trimmed}

    def _get_recent_user_text(self, max_messages: int = 3) -> str:
        """
        汇总最近用户消息用于检索
        """
        if max_messages <= 0:
            return ""
        texts = [msg.content for msg in self.messages if msg.role == "user"]
        if not texts:
            return ""
        return "\n".join(texts[-max_messages:]).strip()

    def _normalize_content(self, content: str) -> str:
        """
        规范化内容用于去重
        """
        if not content:
            return ""
        cleaned = re.sub(r"\s+", " ", content.strip())
        return cleaned.lower()

    def _is_duplicate(self, role: str, content: str) -> bool:
        """
        检测重复消息
        """
        if not content:
            return False
        if self.dedup_window <= 0:
            return False
        norm = self._normalize_content(content)
        key = f"{role}:{norm}"
        digest = str(hash(key))
        if digest in self._recent_hashes:
            return True
        self._recent_hashes.append(digest)
        if len(self._recent_hashes) > self.dedup_window:
            self._recent_hashes = self._recent_hashes[-self.dedup_window:]
        return False

    def _next_message_id(self) -> str:
        """
        生成消息ID
        """
        self._message_counter += 1
        return f"m{self._message_counter:04d}"

    def _next_note_id(self) -> str:
        """
        生成记忆片段ID
        """
        self._note_counter += 1
        return f"n{self._note_counter:04d}"

    def _sync_pins(self) -> None:
        """
        清理已失效的置顶消息
        """
        if not self.pinned_ids:
            return
        existing = {msg.message_id for msg in self.messages}
        self.pinned_ids = [pid for pid in self.pinned_ids if pid in existing]

    def _maybe_add_auto_note(self) -> None:
        """
        自动生成长期记忆片段
        """
        if not self.long_term_enabled:
            return
        if self.auto_note_interval <= 0:
            return
        if len(self.messages) < self.auto_note_min_messages:
            return
        if len(self.messages) - self._last_auto_note_count < self.auto_note_interval:
            return
        targets = self.messages[-self.auto_note_max_messages:]
        note = self._build_note_from_messages(targets, source="auto")
        if note:
            self._add_long_term_note(note)
            self._last_auto_note_count = len(self.messages)

    def _extract_query_terms(self, text: str) -> List[str]:
        """
        提取检索关键词
        """
        if not text:
            return []
        tokens = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+", text)
        cleaned = []
        for token in tokens:
            token = token.strip().lower()
            if not token:
                continue
            if token.isascii() and len(token) < 2:
                continue
            cleaned.append(token)
        seen = set()
        result = []
        for token in cleaned:
            if token in seen:
                continue
            seen.add(token)
            result.append(token)
        return result[:64]

    def _chunk_text(self, text: str, max_chars: int) -> List[str]:
        """
        将文本按段落分块
        """
        if not text:
            return []
        if max_chars <= 0:
            return [text]
        paragraphs = re.split(r"\n{2,}", text)
        chunks = []
        current = []
        length = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_len = len(para)
            if para_len > max_chars:
                if current:
                    chunks.append("\n\n".join(current))
                    current = []
                    length = 0
                for idx in range(0, para_len, max_chars):
                    slice_text = para[idx:idx + max_chars].strip()
                    if slice_text:
                        chunks.append(slice_text)
                continue
            if length + para_len + (2 if current else 0) > max_chars and current:
                chunks.append("\n\n".join(current))
                current = [para]
                length = para_len
            else:
                if current:
                    length += 2 + para_len
                else:
                    length = para_len
                current.append(para)
        if current:
            chunks.append("\n\n".join(current))
        return chunks

    def _score_chunk(self, chunk: str, terms: List[str]) -> int:
        """
        计算分块相关性得分
        """
        if not chunk or not terms:
            return 0
        chunk_lower = chunk.lower()
        score = 0
        for term in terms:
            if term and term in chunk_lower:
                score += 1
        return score

    def _build_note_from_messages(
        self,
        messages: List[Message],
        source: str = "manual"
    ) -> Optional[MemoryNote]:
        """
        基于消息构建记忆片段
        """
        if not messages:
            return None
        lines = []
        raw_texts = []
        for msg in messages:
            role_name = {
                "user": "用户",
                "assistant": "助手",
                "tool": "工具",
                "system": "系统",
            }.get(msg.role, msg.role)
            snippet = truncate_text(msg.content.strip(), 160)
            lines.append(f"{role_name}: {snippet}")
            raw_texts.append(msg.content)
        content = "\n".join(lines)
        content = truncate_text(content, self.auto_note_max_chars)
        tags = self._extract_query_terms(" ".join(raw_texts))[: self.auto_tag_max]
        title = f"自动摘要 {datetime.now().strftime('%m-%d %H:%M')}" if source == "auto" else "记忆片段"
        return MemoryNote(
            note_id=self._next_note_id(),
            title=title,
            content=content,
            tags=tags,
            source=source
        )

    def _add_project_note(self, note: MemoryNote) -> None:
        """
        添加项目记忆片段
        """
        if not self.project_notes_enabled:
            return
        self.project_notes.append(note)
        if len(self.project_notes) > self.project_notes_max:
            self.project_notes = self.project_notes[-self.project_notes_max:]

    def _add_long_term_note(self, note: MemoryNote) -> None:
        """
        添加长期记忆片段
        """
        if not self.long_term_enabled:
            return
        self.long_term_notes.append(note)
        if len(self.long_term_notes) > self.long_term_max:
            self.long_term_notes = self.long_term_notes[-self.long_term_max:]

    def _build_notes_message(self) -> Optional[Dict[str, str]]:
        """
        构建记忆片段系统消息
        """
        if not (self.project_notes or self.long_term_notes or self.pinned_ids):
            return None

        max_tokens = self.notes_max_tokens if self.notes_max_tokens > 0 else None
        lines = ["## 关键记忆"]
        tokens_used = estimate_tokens("\n".join(lines))

        def try_append(block_lines: List[str]) -> bool:
            nonlocal tokens_used
            if not block_lines:
                return False
            block_text = "\n".join(block_lines)
            block_tokens = estimate_tokens(block_text)
            if max_tokens is not None and tokens_used + block_tokens > max_tokens:
                return False
            lines.extend(block_lines)
            tokens_used += block_tokens
            return True

        if self.pinned_ids and self.pins_enabled:
            pinned_lines = ["### 置顶消息"]
            for msg in self.get_pinned_messages():
                role_name = {
                    "user": "用户",
                    "assistant": "助手",
                    "tool": "工具",
                    "system": "系统",
                }.get(msg.role, msg.role)
                snippet = truncate_text(msg.content.strip(), 200)
                pinned_lines.append(f"- [{role_name}] {snippet}")
            try_append(pinned_lines)

        if self.project_notes_enabled and self.project_notes:
            project_lines = ["### 项目记忆"]
            for note in self.project_notes[-self.project_notes_max:]:
                project_lines.append(f"- {note.title}: {truncate_text(note.content, 220)}")
            try_append(project_lines)

        if self.long_term_enabled and self.long_term_notes:
            long_lines = ["### 长期记忆"]
            for note in self.long_term_notes[-self.long_term_max:]:
                long_lines.append(f"- {note.title}: {truncate_text(note.content, 200)}")
            try_append(long_lines)

        if len(lines) <= 1:
            return None
        return {"role": "system", "content": "\n".join(lines)}

    def _select_relevant_chunks(self, content: str, query_text: str) -> List[str]:
        """
        基于检索关键词选择相关分块
        """
        chunks = self._chunk_text(content, self.file_context_chunk_size)
        if not chunks:
            return []
        terms = self._extract_query_terms(query_text)
        if not terms:
            return chunks[: self.file_context_max_chunks_per_file]
        scored = []
        for idx, chunk in enumerate(chunks):
            scored.append((self._score_chunk(chunk, terms), idx, chunk))
        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = [item for item in scored if item[0] >= self.file_context_min_score]
        if not selected:
            selected = scored[:1]
        selected = selected[: self.file_context_max_chunks_per_file]
        selected.sort(key=lambda item: item[1])
        return [item[2] for item in selected]

    def _build_file_block(
        self,
        file_ctx: FileContext,
        query_text: str,
        max_tokens: Optional[int]
    ) -> Optional[str]:
        """
        构建单文件上下文块
        """
        lines = [f"### `{file_ctx.path}`"]
        if file_ctx.abstract:
            lines.append(f"**摘要**: {file_ctx.abstract}")
        else:
            lines.append("**摘要**: （无摘要）")

        minimal_tokens = estimate_tokens("\n".join(lines + ["-" * 40]))
        if max_tokens is not None and minimal_tokens > max_tokens:
            return None

        if file_ctx.content:
            for chunk in self._select_relevant_chunks(file_ctx.content, query_text):
                block = f"```\n{chunk}\n```"
                if max_tokens is not None:
                    candidate_tokens = estimate_tokens("\n".join(lines + [block, "-" * 40]))
                    if candidate_tokens > max_tokens:
                        break
                lines.append(block)

        lines.append("-" * 40)
        return "\n".join(lines)

    def _build_file_context_message(
        self,
        query_text: str = "",
        max_tokens: Optional[int] = None
    ) -> Optional[Dict[str, str]]:
        """
        构建包含文件内容的上下文消息

        Returns:
            Optional[Dict]: 文件上下文消息，若无文件则返回 None
        """
        message, _ = self._build_file_context_message_with_report(query_text, max_tokens=max_tokens)
        return message

    def _build_file_context_message_with_report(
        self,
        query_text: str = "",
        max_tokens: Optional[int] = None
    ) -> Tuple[Optional[Dict[str, str]], List[str]]:
        """
        构建包含文件内容的上下文消息并返回文件路径
        """
        if not self.files:
            return None, []

        file_contents = [
            "## 当前文件上下文\n",
            f"共有 {len(self.files)} 个文件",
            "内容按相关性分块注入",
            ""
        ]

        if max_tokens is not None and max_tokens <= 0:
            return None, []

        tokens_used = estimate_tokens("\n".join(file_contents))
        budget = max_tokens if max_tokens is not None else None
        included: List[str] = []

        for file_ctx in self.files.values():
            remaining = None if budget is None else max(0, budget - tokens_used)
            block = self._build_file_block(file_ctx, query_text, remaining)
            if not block:
                continue
            block_tokens = estimate_tokens(block)
            if budget is not None and tokens_used + block_tokens > budget:
                continue
            file_contents.append(block)
            tokens_used += block_tokens
            included.append(file_ctx.path)

        if len(file_contents) <= 4:
            return None, []

        return {"role": "system", "content": "\n".join(file_contents)}, included

    def _build_history_retrieval_message(
        self,
        query_text: str,
        max_tokens: Optional[int] = None
    ) -> Optional[Dict[str, str]]:
        """
        构建历史检索上下文消息
        """
        message, _ = self._build_history_retrieval_message_with_report(query_text, max_tokens=max_tokens)
        return message

    def _build_history_retrieval_message_with_report(
        self,
        query_text: str,
        max_tokens: Optional[int] = None
    ) -> Tuple[Optional[Dict[str, str]], List[str]]:
        """
        构建历史检索上下文消息并返回命中消息ID
        """
        if not query_text:
            return None, []
        terms = self._extract_query_terms(query_text)
        if not terms:
            return None, []

        roles = set(self.history_retrieval_include_roles or [])
        candidates = []
        for idx, msg in enumerate(self.messages):
            if roles and msg.role not in roles:
                continue
            score = self._score_chunk(msg.content, terms)
            if score < self.history_retrieval_min_score:
                continue
            candidates.append((score, idx, msg))

        if not candidates:
            return None, []

        candidates.sort(key=lambda item: (-item[0], -item[1]))
        selected = candidates[: self.history_retrieval_max_messages]
        selected.sort(key=lambda item: item[1])

        lines = [
            "## 相关历史片段",
            "以下内容来自历史对话的相关片段，仅供参考：",
        ]

        tokens_used = estimate_tokens("\n".join(lines))
        included_ids: List[str] = []
        for _, _, msg in selected:
            role_name = {
                "user": "用户",
                "assistant": "助手",
                "tool": "工具",
                "system": "系统",
            }.get(msg.role, msg.role)
            snippet = truncate_text(msg.content, 240)
            line = f"- [{role_name} {msg.timestamp.isoformat()}] {snippet}"
            if max_tokens is not None:
                candidate_tokens = tokens_used + estimate_tokens(line)
                if candidate_tokens > max_tokens:
                    break
            lines.append(line)
            tokens_used += estimate_tokens(line)
            if msg.message_id:
                included_ids.append(msg.message_id)

        if len(lines) <= 2:
            return None, []

        return {"role": "system", "content": "\n".join(lines)}, included_ids
    
    def clear(self, keep_system: bool = True) -> None:
        """
        清空对话历史

        Args:
            keep_system: 是否保留系统消息
        """
        if self.archive_on_reset:
            self.archive_memory()
        self.messages = []
        self.summary = ""
        self.pinned_ids = []
        self.project_notes = []
        self.long_term_notes = []
        self._last_auto_note_count = 0
        if not keep_system:
            self.system_message = None
    
    def get_context_length(self) -> int:
        """
        获取当前上下文长度（字符数）

        Returns:
            int: 字符数
        """
        total = 0
        for msg in self.get_messages():
            total += len(msg.content)
        return total
    
    # ==============================================================================
    # 文件上下文管理方法
    # ==============================================================================
    
    def add_file(
        self,
        path: str,
        content: Optional[str] = None,
        abstract: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> FileContext:
        """
        添加文件到上下文

        Args:
            path: 文件路径
            content: 文件内容（可选）
            abstract: 文件摘要
            metadata: 额外元数据

        Returns:
            FileContext: 添加的文件上下文
        """
        file_ctx = FileContext(
            path=path,
            content=content,
            abstract=abstract,
            metadata=metadata or {}
        )
        self.files[path] = file_ctx
        return file_ctx
    
    def update_file(
        self,
        path: str,
        content: Optional[str] = None,
        abstract: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[FileContext]:
        """
        更新文件上下文

        Args:
            path: 文件路径
            content: 新的文件内容
            abstract: 新的文件摘要
            metadata: 新的元数据

        Returns:
            FileContext: 更新后的文件上下文，如果文件不存在则返回 None
        """
        if path not in self.files:
            return None
        
        file_ctx = self.files[path]
        if content is not None:
            file_ctx.content = content
        if abstract is not None:
            file_ctx.abstract = abstract
        if metadata is not None:
            file_ctx.metadata.update(metadata)
        
        file_ctx.timestamp = datetime.now()
        return file_ctx
    
    def remove_file(self, path: str) -> bool:
        """
        移除文件上下文

        Args:
            path: 文件路径

        Returns:
            bool: 是否成功移除
        """
        if path in self.files:
            del self.files[path]
            return True
        return False
    
    def get_file(self, path: str) -> Optional[FileContext]:
        """
        获取文件上下文

        Args:
            path: 文件路径

        Returns:
            FileContext: 文件上下文，如果不存在则返回 None
        """
        return self.files.get(path)
    
    def list_files(self) -> List[FileContext]:
        """
        列出所有文件上下文

        Returns:
            List[FileContext]: 文件上下文列表
        """
        return list(self.files.values())
    
    def get_files_summary(self) -> str:
        """
        获取文件上下文摘要

        Returns:
            str: 文件摘要字符串
        """
        if not self.files:
            return "当前无文件"
        
        summary_lines = [f"当前文件数量: {len(self.files)}"]
        for file_ctx in self.files.values():
            summary_lines.append(f"  - {file_ctx.get_summary()}")
        
        return "\n".join(summary_lines)
    
    # ==============================================================================
    # 工作记忆摘要方法
    # ==============================================================================
    
    def get_context_summary(self, last_n: int = 10) -> str:
        """
        生成最近操作的摘要

        Args:
            last_n: 分析最近N条消息

        Returns:
            str: 上下文摘要
        """
        if not self.messages:
            return "暂无操作历史"
        
        summary_lines = []
        
        # 1. 工具使用统计
        tool_counts = {}
        for msg in self.messages[-last_n:]:
            if msg.role == "tool":
                tool_name = msg.metadata.get("tool_name", "未知")
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
        
        if tool_counts:
            summary_lines.append("已使用工具统计：")
            for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
                summary_lines.append(f"   • {tool}: {count}次")
        
        # 2. 最新工具结果
        latest_tool_msg = None
        for msg in reversed(self.messages):
            if msg.role == "tool":
                latest_tool_msg = msg
                break
        
        if latest_tool_msg:
            tool_name = latest_tool_msg.metadata.get("tool_name", "未知")
            preview = latest_tool_msg.content[:150]
            if len(latest_tool_msg.content) > 150:
                preview += "..."
            summary_lines.append(f"\n最新工具结果（{tool_name}）：")
            summary_lines.append(f"   {preview}")
        
        # 3. 当前文件上下文
        if self.files:
            summary_lines.append(f"\n当前文件数: {len(self.files)}")

        if self.project_notes:
            summary_lines.append(f"\n项目记忆: {len(self.project_notes)}")
        if self.long_term_notes:
            summary_lines.append(f"长期记忆: {len(self.long_term_notes)}")
        
        return "\n".join(summary_lines)

    def get_dedup_stats(self) -> Dict[str, Any]:
        """
        获取去重统计
        """
        total = self.dedup_total
        hits = self.dedup_hits
        rate = 0.0
        if total:
            rate = round(hits / total, 4)
        return {"total": total, "hits": hits, "hit_rate": rate}

    def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """
        根据ID获取消息
        """
        if not message_id:
            return None
        for msg in self.messages:
            if msg.message_id == message_id:
                return msg
        return None

    def get_message_by_index(self, index: int) -> Optional[Message]:
        """
        根据序号获取消息（从1开始）
        """
        if index <= 0:
            return None
        if index > len(self.messages):
            return None
        return self.messages[index - 1]

    def pin_message(self, message_id: str) -> bool:
        """
        置顶消息
        """
        if not self.pins_enabled:
            return False
        if not message_id:
            return False
        if not self.get_message_by_id(message_id):
            return False
        if message_id in self.pinned_ids:
            return True
        self.pinned_ids.append(message_id)
        if len(self.pinned_ids) > self.pins_max:
            self.pinned_ids = self.pinned_ids[-self.pins_max:]
        return True

    def pin_message_by_index(self, index: int) -> bool:
        """
        置顶指定序号消息
        """
        msg = self.get_message_by_index(index)
        if not msg:
            return False
        return self.pin_message(msg.message_id)

    def unpin_message(self, message_id: str) -> bool:
        """
        取消置顶
        """
        if not message_id or message_id not in self.pinned_ids:
            return False
        self.pinned_ids = [pid for pid in self.pinned_ids if pid != message_id]
        return True

    def get_pinned_messages(self) -> List[Message]:
        """
        获取置顶消息列表
        """
        pinned = []
        for pid in self.pinned_ids:
            msg = self.get_message_by_id(pid)
            if msg:
                pinned.append(msg)
        return pinned

    def add_project_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> Optional[MemoryNote]:
        """
        添加项目记忆片段
        """
        if not self.project_notes_enabled:
            return None
        if not tags and self.auto_tag_enabled:
            tags = self._extract_query_terms(content)[: self.auto_tag_max]
        note = MemoryNote(
            note_id=self._next_note_id(),
            title=title.strip() or "项目记忆",
            content=content.strip(),
            tags=tags or [],
            source="manual"
        )
        self._add_project_note(note)
        return note

    def add_long_term_note(self, title: str, content: str, tags: Optional[List[str]] = None) -> Optional[MemoryNote]:
        """
        添加长期记忆片段
        """
        if not self.long_term_enabled:
            return None
        if not tags and self.auto_tag_enabled:
            tags = self._extract_query_terms(content)[: self.auto_tag_max]
        note = MemoryNote(
            note_id=self._next_note_id(),
            title=title.strip() or "长期记忆",
            content=content.strip(),
            tags=tags or [],
            source="manual"
        )
        self._add_long_term_note(note)
        return note

    def list_project_notes(self) -> List[MemoryNote]:
        """
        获取项目记忆列表
        """
        return list(self.project_notes)

    def list_long_term_notes(self) -> List[MemoryNote]:
        """
        获取长期记忆列表
        """
        return list(self.long_term_notes)

    def search_messages(
        self,
        query: str,
        roles: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        检索对话消息
        """
        terms = self._extract_query_terms(query)
        if not terms:
            return []
        role_set = set(roles or [])
        now = datetime.now()
        ranked = []
        for idx, msg in enumerate(self.messages):
            if role_set and msg.role not in role_set:
                continue
            score = self._score_chunk(msg.content, terms)
            if score <= 0:
                continue
            age_seconds = max(0.0, (now - msg.timestamp).total_seconds())
            recency = 1.0 / (1.0 + age_seconds / 3600.0)
            combined = score + recency
            ranked.append((combined, score, recency, idx, msg))
        ranked.sort(key=lambda item: (-item[0], -item[3]))
        max_items = limit or self.search_max_results
        results = []
        for combined, score, recency, _, msg in ranked[:max_items]:
            results.append({
                "message_id": msg.message_id,
                "role": msg.role,
                "content": truncate_text(msg.content, 240),
                "timestamp": msg.timestamp.isoformat(),
                "score": score,
                "recency": round(recency, 4),
                "combined_score": round(combined, 4),
            })
        return results

    def export_snapshot(
        self,
        max_messages: Optional[int] = None,
        include_messages: bool = True,
        include_files: bool = True,
        include_summary: bool = True
    ) -> Dict[str, Any]:
        """
        导出上下文快照
        """
        snapshot: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "message_count": len(self.messages),
                "file_count": len(self.files),
                "context_length": self.get_context_length(),
            },
        }

        if self.system_message:
            snapshot["system_message"] = self.system_message.to_dict()

        if include_summary and self.summary:
            snapshot["summary"] = self.summary

        if include_messages:
            messages = self.messages
            if max_messages and max_messages > 0:
                messages = messages[-max_messages:]
            snapshot["messages"] = [msg.to_dict() for msg in messages]

        if include_files:
            snapshot["files"] = [file_ctx.to_dict() for file_ctx in self.files.values()]

        snapshot["pinned_ids"] = list(self.pinned_ids)
        snapshot["project_notes"] = [note.to_dict() for note in self.project_notes]
        snapshot["long_term_notes"] = [note.to_dict() for note in self.long_term_notes]

        return snapshot

    def create_snapshot(self, label: str = "") -> Optional[Dict[str, Any]]:
        """
        创建记忆快照
        """
        if not self.snapshot_enabled:
            return None
        payload = self.export_snapshot()
        snapshot_id = f"s{datetime.now().strftime('%Y%m%d%H%M%S')}"
        payload["snapshot_id"] = snapshot_id
        payload["label"] = label
        self.snapshots.append(payload)
        if len(self.snapshots) > self.snapshot_max:
            self.snapshots = self.snapshots[-self.snapshot_max:]
        return payload

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """
        列出快照
        """
        return list(self.snapshots)

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        恢复记忆快照
        """
        if not snapshot_id:
            return False
        target = None
        for snap in self.snapshots:
            if snap.get("snapshot_id") == snapshot_id:
                target = snap
                break
        if not target:
            return False
        return self.load_snapshot_payload(target)

    def load_snapshot_payload(self, payload: Dict[str, Any]) -> bool:
        """
        从快照内容恢复记忆
        """
        if not payload:
            return False
        self.messages = []
        for item in payload.get("messages", []):
            self.messages.append(
                Message(
                    role=item.get("role", "assistant"),
                    content=item.get("content", ""),
                    message_id=item.get("message_id", ""),
                    timestamp=datetime.fromisoformat(item.get("timestamp")) if item.get("timestamp") else datetime.now(),
                    metadata=item.get("metadata", {}),
                )
            )
        self.summary = payload.get("summary", "") or ""
        self.pinned_ids = list(payload.get("pinned_ids", []))
        self.project_notes = [
            MemoryNote(
                note_id=item.get("note_id", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                tags=item.get("tags", []),
                timestamp=datetime.fromisoformat(item.get("timestamp")) if item.get("timestamp") else datetime.now(),
                source=item.get("source", "manual"),
            )
            for item in payload.get("project_notes", [])
        ]
        self.long_term_notes = [
            MemoryNote(
                note_id=item.get("note_id", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                tags=item.get("tags", []),
                timestamp=datetime.fromisoformat(item.get("timestamp")) if item.get("timestamp") else datetime.now(),
                source=item.get("source", "manual"),
            )
            for item in payload.get("long_term_notes", [])
        ]
        self._message_counter = len(self.messages)
        self._note_counter = len(self.project_notes) + len(self.long_term_notes)
        return True

    def archive_memory(self) -> Optional[str]:
        """
        归档记忆到文件
        """
        if not self.archive_dir:
            return None
        if not self.messages and not self.project_notes and not self.long_term_notes:
            return None
        archive_dir = Path(self.archive_dir)
        archive_dir.mkdir(parents=True, exist_ok=True)
        filename = archive_dir / f"memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        payload = self.export_snapshot()
        payload["archive"] = True
        filename.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(filename)

    def _summarize_if_needed(self) -> None:
        """
        在摘要模式下压缩历史消息
        """
        if len(self.messages) <= self.max_entries:
            return

        keep_n = min(self.summary_keep_last_n, len(self.messages))
        summarize_target = self.messages[:-keep_n]
        if not summarize_target:
            return

        new_summary = self._build_summary_from_messages(summarize_target)
        self.summary = self._merge_summary(self.summary, new_summary)
        self.summary = self._trim_summary(self.summary)
        self.messages = self.messages[-keep_n:]

    def _build_summary_from_messages(self, messages: List[Message]) -> str:
        """
        生成消息摘要文本
        """
        lines = []
        for msg in messages:
            role_name = {
                "user": "用户",
                "assistant": "助手",
                "tool": "工具"
            }.get(msg.role, msg.role)
            content = truncate_text(msg.content, 200)
            lines.append(f"{role_name}: {content}")
        return "\n".join(lines)

    def _merge_summary(self, current: str, new_summary: str) -> str:
        """
        合并摘要内容
        """
        if not current:
            return new_summary
        return current + "\n" + new_summary

    def _trim_summary(self, summary: str) -> str:
        """
        控制摘要长度
        """
        if len(summary) <= self.summary_max_chars:
            return summary
        return "..." + summary[-self.summary_max_chars:]


# 全局记忆实例
_memory: Optional[ConversationMemory] = None


def get_memory() -> ConversationMemory:
    """
    获取全局记忆实例

    Returns:
        ConversationMemory: 记忆实例
    """
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
    return _memory


def reset_memory() -> ConversationMemory:
    """
    重置全局记忆

    Returns:
        ConversationMemory: 新的记忆实例
    """
    global _memory
    _memory = ConversationMemory()
    return _memory
