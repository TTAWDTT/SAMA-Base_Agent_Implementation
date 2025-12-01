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
        """
        转换为字典格式 / Convert to dictionary format
        
        Returns:
            Dict: 消息字典 / Message dictionary
        """
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    def to_openai_format(self) -> Dict[str, str]:
        """
        转换为OpenAI API格式 / Convert to OpenAI API format
        
        Returns:
            Dict: OpenAI格式的消息 / Message in OpenAI format
        """
        return {
            "role": self.role,
            "content": self.content
        }


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
        self.messages: List[Message] = []
        self.system_message: Optional[Message] = None
    
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
        获取OpenAI格式的消息列表 / Get messages in OpenAI format
        
        Returns:
            List[Dict]: OpenAI格式的消息列表 / List of messages in OpenAI format
        """
        return [msg.to_openai_format() for msg in self.get_messages()]
    
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
