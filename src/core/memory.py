# ==============================================================================
# 对话记忆模块 / Conversation Memory Module
# ==============================================================================
# 管理Agent的对话历史和上下文
# Manages Agent's conversation history and context
# ==============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.config import get_config
from src.utils.helpers import estimate_tokens


@dataclass
class FileContext:
    """
    文件上下文 / File Context
    
    管理Agent工作过程中涉及的文件
    Manages files involved in Agent's work process
    """
    path: str
    content: Optional[str] = None
    abstract: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式 / Convert to dictionary format"""
        return {
            "path": self.path,
            "content": self.content,
            "abstract": self.abstract,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def get_summary(self) -> str:
        """获取文件摘要信息 / Get file summary"""
        size_info = f"({len(self.content)} chars)" if self.content else "(no content)"
        return f"{self.path} {size_info}: {self.abstract}"


@dataclass
class Message:
    """
    消息数据类 / Message Data Class
    
    表示对话中的单条消息
    Represents a single message in the conversation
    """
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式 / Convert to dictionary format"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def to_openai_format(self) -> Dict[str, Any]:
        """
        转换为OpenAI API格式 / Convert to OpenAI API format
        
        Returns:
            Dict: OpenAI格式的消息 / Message in OpenAI format
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
    对话记忆类 / Conversation Memory Class
    
    管理对话历史，支持添加、检索和清理消息
    Manages conversation history, supports adding, retrieving and clearing messages
    """
    
    def __init__(self, max_entries: Optional[int] = None):
        """
        初始化对话记忆 / Initialize conversation memory
        
        Args:
            max_entries: 最大记忆条数 / Maximum memory entries
        """
        config = get_config()
        self.max_entries = max_entries or config.memory.max_entries
        self.max_context_tokens = config.memory.max_context_tokens
        self.messages: List[Message] = []
        self.system_message: Optional[Message] = None
        self.files: Dict[str, FileContext] = {}  # 文件上下文字典，key为文件路径 / File context dict, key is file path
    
    def set_system_message(self, content: str) -> None:
        """
        设置系统消息 / Set system message
        
        系统消息始终位于对话开头
        System message is always at the beginning of the conversation
        
        Args:
            content: 系统消息内容 / System message content
        """
        self.system_message = Message(role="system", content=content)
    
    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        添加用户消息 / Add user message
        
        Args:
            content: 消息内容 / Message content
            metadata: 元数据 / Metadata
        """
        self._add_message("user", content, metadata)
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        添加助手消息 / Add assistant message
        
        Args:
            content: 消息内容 / Message content
            metadata: 元数据 / Metadata
        """
        self._add_message("assistant", content, metadata)
    
    def add_tool_message(self, content: str, tool_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        添加工具消息 / Add tool message
        
        Args:
            content: 消息内容 / Message content
            tool_name: 工具名称 / Tool name
            metadata: 元数据 / Metadata
        """
        meta = metadata or {}
        meta["tool_name"] = tool_name
        self._add_message("tool", content, meta)
    
    def _add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        内部方法：添加消息 / Internal method: add message
        
        Args:
            role: 角色 / Role
            content: 内容 / Content
            metadata: 元数据 / Metadata
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        
        # 如果超过最大条数，删除最早的消息（保留系统消息）
        # If exceeds max entries, remove oldest messages (keep system message)
        while len(self.messages) > self.max_entries:
            self.messages.pop(0)
    
    def get_messages(self) -> List[Message]:
        """
        获取所有消息（包括系统消息）/ Get all messages (including system message)
        
        Returns:
            List[Message]: 消息列表 / List of messages
        """
        if self.system_message:
            return [self.system_message] + self.messages
        return self.messages
    
    def get_openai_messages(self) -> List[Dict[str, str]]:
        """
        获取OpenAI格式的消息列表（包含文件上下文）/ Get messages in OpenAI format (including file context)
        
        消息顺序 / Message order:
        1. 系统消息（包含文件摘要）/ System message (with file summary)
        2. 文件内容消息（如果有）/ File content messages (if any)
        3. 对话历史 / Conversation history
        
        Returns:
            List[Dict]: OpenAI格式的消息列表 / List of messages in OpenAI format
        """
        messages = []
        
        # 1. 添加系统消息 / Add system message
        if self.system_message:
            messages.append(self.system_message.to_openai_format())
        
        # 2. 添加文件内容作为独立消息 / Add file contents as separate messages
        if self.files:
            file_context_msg = self._build_file_context_message()
            if file_context_msg:
                messages.append(file_context_msg)
        
        # 3. 添加对话历史 / Add conversation history
        for msg in self.messages:
            messages.append(msg.to_openai_format())
        
        return self._trim_messages_to_token_limit(messages)

    def _trim_messages_to_token_limit(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据token预算裁剪消息 / Trim messages to token budget
        """
        if not self.max_context_tokens:
            return messages

        if not messages:
            return messages

        pinned = []
        idx = 0

        # 保留系统消息 / Always keep system message
        if messages[0].get("role") == "system":
            pinned.append(messages[0])
            idx = 1

        # 保留文件上下文消息（如果存在）/ Keep file context message if present
        if idx < len(messages) and messages[idx].get("role") == "system":
            pinned.append(messages[idx])
            idx += 1

        def _msg_tokens(msg: Dict[str, Any]) -> int:
            return estimate_tokens(msg.get("content", "") or "")

        total_tokens = sum(_msg_tokens(msg) for msg in pinned)
        remaining = messages[idx:]
        kept = []

        for msg in reversed(remaining):
            msg_tokens = _msg_tokens(msg)
            if total_tokens + msg_tokens > self.max_context_tokens:
                break
            kept.append(msg)
            total_tokens += msg_tokens

        kept.reverse()
        return pinned + kept
    
    def _build_file_context_message(self) -> Optional[Dict[str, str]]:
        """
        构建包含文件内容的上下文消息 / Build message containing file contents
        
        Returns:
            Optional[Dict]: 文件上下文消息 / File context message, or None if no files
        """
        if not self.files:
            return None
        
        file_contents = [
            "## 📁 当前文件上下文 / Current File Context\n",
            f"共有 {len(self.files)} 个文件 / {len(self.files)} files in context\n"
        ]
        
        for path, file_ctx in self.files.items():
            file_contents.append(f"\n### `{path}`")
            file_contents.append(f"**摘要**: {file_ctx.abstract}")
            
            if file_ctx.content:
                content = file_ctx.content
                if len(content) > 2000:
                    content = content[:1000] + f"\n[... 省略 {len(content) - 2000} 字符 ...]\n" + content[-1000:]
                file_contents.append(f"```\n{content}\n```")
            
            file_contents.append("-" * 40)
        
        return {"role": "system", "content": "\n".join(file_contents)}
    
    def get_recent_messages(self, n: int) -> List[Message]:
        """
        获取最近n条消息 / Get recent n messages
        
        Args:
            n: 消息数量 / Number of messages
            
        Returns:
            List[Message]: 消息列表 / List of messages
        """
        messages = self.get_messages()
        return messages[-n:] if len(messages) > n else messages
    
    def clear(self, keep_system: bool = True) -> None:
        """
        清空对话历史 / Clear conversation history
        
        Args:
            keep_system: 是否保留系统消息 / Whether to keep system message
        """
        self.messages = []
        if not keep_system:
            self.system_message = None
    
    def get_context_length(self) -> int:
        """
        获取当前上下文长度（字符数）/ Get current context length (character count)
        
        Returns:
            int: 字符数 / Character count
        """
        total = 0
        for msg in self.get_messages():
            total += len(msg.content)
        return total
    
    def summarize(self) -> str:
        """
        生成对话摘要 / Generate conversation summary
        
        Returns:
            str: 对话摘要 / Conversation summary
        """
        if not self.messages:
            return "无对话历史 / No conversation history"
        
        summary_parts = []
        for msg in self.messages[-5:]:  # 最近5条消息 / Last 5 messages
            role_name = {
                "user": "用户/User",
                "assistant": "助手/Assistant",
                "tool": "工具/Tool"
            }.get(msg.role, msg.role)
            summary_parts.append(f"[{role_name}]: {msg.content[:100]}...")
        
        return "\n".join(summary_parts)
    
    # ==============================================================================
    # 文件上下文管理方法 / File Context Management Methods
    # ==============================================================================
    
    def add_file(
        self,
        path: str,
        content: Optional[str] = None,
        abstract: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> FileContext:
        """
        添加文件到上下文 / Add file to context
        
        Args:
            path: 文件路径 / File path
            content: 文件内容（可选）/ File content (optional)
            abstract: 文件摘要 / File abstract
            metadata: 额外元数据 / Extra metadata
            
        Returns:
            FileContext: 添加的文件上下文 / Added file context
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
        更新文件上下文 / Update file context
        
        Args:
            path: 文件路径 / File path
            content: 新的文件内容 / New file content
            abstract: 新的文件摘要 / New file abstract
            metadata: 新的元数据 / New metadata
            
        Returns:
            FileContext: 更新后的文件上下文，如果文件不存在则返回None / Updated file context, None if not exists
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
        移除文件上下文 / Remove file context
        
        Args:
            path: 文件路径 / File path
            
        Returns:
            bool: 是否成功移除 / Whether removal was successful
        """
        if path in self.files:
            del self.files[path]
            return True
        return False
    
    def get_file(self, path: str) -> Optional[FileContext]:
        """
        获取文件上下文 / Get file context
        
        Args:
            path: 文件路径 / File path
            
        Returns:
            FileContext: 文件上下文，如果不存在则返回None / File context, None if not exists
        """
        return self.files.get(path)
    
    def list_files(self) -> List[FileContext]:
        """
        列出所有文件上下文 / List all file contexts
        
        Returns:
            List[FileContext]: 文件上下文列表 / List of file contexts
        """
        return list(self.files.values())
    
    def get_files_summary(self) -> str:
        """
        获取文件上下文摘要 / Get files summary
        
        Returns:
            str: 文件摘要字符串 / Files summary string
        """
        if not self.files:
            return "当前无文件 / No files currently"
        
        summary_lines = [f"当前文件数量 / Current files: {len(self.files)}"]
        for file_ctx in self.files.values():
            summary_lines.append(f"  - {file_ctx.get_summary()}")
        
        return "\n".join(summary_lines)
    
    def clear_files(self) -> None:
        """清空所有文件上下文 / Clear all file contexts"""
        self.files.clear()
    
    # ==============================================================================
    # 工作记忆摘要方法 / Working Memory Summary Methods
    # ==============================================================================
    
    def get_context_summary(self, last_n: int = 10) -> str:
        """
        生成最近操作的摘要 / Generate summary of recent operations
        
        Args:
            last_n: 分析最近N条消息 / Analyze last N messages
            
        Returns:
            str: 上下文摘要 / Context summary
        """
        if not self.messages:
            return "暂无操作历史 / No operation history"
        
        summary_lines = []
        
        # 1. 工具使用统计 / Tool usage statistics
        tool_counts = {}
        for msg in self.messages[-last_n:]:
            if msg.role == "tool":
                tool_name = msg.metadata.get("tool_name", "unknown")
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
        
        if tool_counts:
            summary_lines.append("📊 已使用工具统计 / Tools used:")
            for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
                summary_lines.append(f"   • {tool}: {count}次")
        
        # 2. 最新工具结果 / Latest tool results
        latest_tool_msg = None
        for msg in reversed(self.messages):
            if msg.role == "tool":
                latest_tool_msg = msg
                break
        
        if latest_tool_msg:
            tool_name = latest_tool_msg.metadata.get("tool_name", "unknown")
            preview = latest_tool_msg.content[:150]
            if len(latest_tool_msg.content) > 150:
                preview += "..."
            summary_lines.append(f"\n🔍 最新工具结果 / Latest tool result ({tool_name}):")
            summary_lines.append(f"   {preview}")
        
        # 3. 当前文件上下文 / Current file context
        if self.files:
            summary_lines.append(f"\n📁 当前文件数 / Files in context: {len(self.files)}")
        
        return "\n".join(summary_lines)


# 全局记忆实例 / Global memory instance
_memory: Optional[ConversationMemory] = None


def get_memory() -> ConversationMemory:
    """
    获取全局记忆实例 / Get global memory instance
    
    Returns:
        ConversationMemory: 记忆实例 / Memory instance
    """
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
    return _memory


def reset_memory() -> ConversationMemory:
    """
    重置全局记忆 / Reset global memory
    
    Returns:
        ConversationMemory: 新的记忆实例 / New memory instance
    """
    global _memory
    _memory = ConversationMemory()
    return _memory
