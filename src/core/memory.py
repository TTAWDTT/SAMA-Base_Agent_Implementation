# ==============================================================================
# 对话记忆模块
# ==============================================================================
# 管理智能体的对话历史和上下文
# ==============================================================================

from dataclasses import dataclass, field
from datetime import datetime
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
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "role": self.role,
            "content": self.content,
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
        self.messages: List[Message] = []
        self.system_message: Optional[Message] = None
        self.files: Dict[str, FileContext] = {}  # 文件上下文字典，key为文件路径
        self.summary = ""
    
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
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        
        # 根据记忆类型处理长度
        if self.memory_type == "summary":
            self._summarize_if_needed()
        else:
            # 如果超过最大条数，删除最早的消息（保留系统消息）
            while len(self.messages) > self.max_entries:
                self.messages.pop(0)
    
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

        # 1. 添加系统消息
        if self.system_message:
            system_messages.append(self.system_message.to_openai_format())

        # 2. 构建摘要消息（可选）
        if self.summary:
            summary_message = {
                "role": "system",
                "content": "## 对话摘要\n" + self.summary
            }

        # 3. 构建对话历史
        history_messages = [msg.to_openai_format() for msg in self.messages]

        query_text = self._get_recent_user_text(self.file_context_query_messages)
        return self._trim_messages_to_token_limit(
            system_messages,
            summary_message,
            history_messages,
            query_text
        )

    def _trim_messages_to_token_limit(
        self,
        system_messages: List[Dict[str, Any]],
        summary_message: Optional[Dict[str, Any]],
        history_messages: List[Dict[str, Any]],
        query_text: str
    ) -> List[Dict[str, Any]]:
        """
        根据分层预算裁剪消息
        """
        def _msg_tokens(msg: Dict[str, Any]) -> int:
            return estimate_tokens(msg.get("content", "") or "")

        if not self.max_context_tokens:
            file_context_msg = self._build_file_context_message(query_text=query_text)
            messages = list(system_messages)
            if summary_message:
                messages.append(summary_message)
            if file_context_msg:
                messages.append(file_context_msg)
            messages.extend(history_messages)
            return messages

        messages = list(system_messages)

        # 控制系统摘要预算
        if summary_message:
            system_budget = int(self.max_context_tokens * max(self.system_token_ratio, 0.0))
            if system_budget < 0:
                system_budget = 0
            if sum(_msg_tokens(msg) for msg in messages + [summary_message]) <= system_budget:
                messages.append(summary_message)

        system_tokens = sum(_msg_tokens(msg) for msg in messages)
        remaining = self.max_context_tokens - system_tokens
        if remaining <= 0:
            return messages

        file_ratio, history_ratio = self._normalize_budget_ratios(
            self.file_context_token_ratio,
            self.history_token_ratio
        )
        file_budget = int(remaining * file_ratio)
        file_context_msg = self._build_file_context_message(
            query_text=query_text,
            max_tokens=file_budget if file_budget > 0 else 0
        )
        if file_context_msg:
            messages.append(file_context_msg)
            remaining -= _msg_tokens(file_context_msg)

        history_budget = max(0, remaining)
        messages.extend(self._trim_history_messages(history_messages, history_budget))
        return messages
    
    def _normalize_budget_ratios(self, file_ratio: float, history_ratio: float) -> Tuple[float, float]:
        """
        归一化文件与历史预算比例
        """
        safe_file = max(file_ratio, 0.0)
        safe_history = max(history_ratio, 0.0)
        total = safe_file + safe_history
        if total <= 0:
            return 0.35, 0.65
        return safe_file / total, safe_history / total

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
        if not self.files:
            return None

        file_contents = [
            "## 当前文件上下文\n",
            f"共有 {len(self.files)} 个文件",
            "内容按相关性分块注入",
            ""
        ]

        if max_tokens is not None and max_tokens <= 0:
            return None

        tokens_used = estimate_tokens("\n".join(file_contents))
        budget = max_tokens if max_tokens is not None else None

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

        if len(file_contents) <= 4:
            return None

        return {"role": "system", "content": "\n".join(file_contents)}
    
    def clear(self, keep_system: bool = True) -> None:
        """
        清空对话历史

        Args:
            keep_system: 是否保留系统消息
        """
        self.messages = []
        self.summary = ""
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
        
        return "\n".join(summary_lines)

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
