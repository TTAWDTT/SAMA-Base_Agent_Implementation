# ==============================================================================
# 数据模式定义模块 / Data Schema Definition Module
# ==============================================================================
# 定义Agent使用的各种数据结构
# Defines various data structures used by the Agent
# ==============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class AgentState(Enum):
    """
    Agent状态枚举 / Agent State Enumeration
    """
    IDLE = "idle"  # 空闲 / Idle
    THINKING = "thinking"  # 思考中 / Thinking
    EXECUTING = "executing"  # 执行工具中 / Executing tool
    COMPLETED = "completed"  # 完成 / Completed
    ERROR = "error"  # 错误 / Error
    STOPPED = "stopped"  # 已停止 / Stopped


class ToolResultStatus(Enum):
    """
    工具执行结果状态 / Tool Execution Result Status
    """
    SUCCESS = "success"  # 成功 / Success
    ERROR = "error"  # 错误 / Error
    TIMEOUT = "timeout"  # 超时 / Timeout


@dataclass
class ToolCall:
    """
    工具调用记录 / Tool Call Record
    
    记录单次工具调用的详细信息
    Records details of a single tool call
    """
    tool_name: str  # 工具名称 / Tool name
    arguments: Dict[str, Any]  # 调用参数 / Call arguments
    timestamp: datetime = field(default_factory=datetime.now)
    call_id: Optional[str] = None  # 调用ID / Call ID
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 / Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "timestamp": self.timestamp.isoformat(),
            "call_id": self.call_id
        }


@dataclass
class ToolResult:
    """
    工具执行结果 / Tool Execution Result
    
    记录工具执行的结果
    Records the result of tool execution
    """
    tool_name: str  # 工具名称 / Tool name
    status: ToolResultStatus  # 状态 / Status
    output: Any  # 输出结果 / Output result
    error_message: Optional[str] = None  # 错误信息 / Error message
    execution_time: float = 0.0  # 执行时间（秒）/ Execution time (seconds)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 / Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "output": str(self.output) if self.output else None,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat()
        }
    
    @property
    def is_success(self) -> bool:
        """是否成功 / Is successful"""
        return self.status == ToolResultStatus.SUCCESS


@dataclass
class AgentStep:
    """
    Agent执行步骤 / Agent Execution Step
    
    记录Agent单次迭代的完整信息
    Records complete information of a single Agent iteration
    """
    step_number: int  # 步骤编号 / Step number
    thought: str  # Agent的思考过程 / Agent's thought process
    tool_calls: List[ToolCall] = field(default_factory=list)  # 工具调用列表 / Tool calls
    tool_results: List[ToolResult] = field(default_factory=list)  # 工具结果列表 / Tool results
    response: Optional[str] = None  # 最终响应 / Final response
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 / Convert to dictionary"""
        return {
            "step_number": self.step_number,
            "thought": self.thought,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "tool_results": [tr.to_dict() for tr in self.tool_results],
            "response": self.response,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AgentResponse:
    """
    Agent最终响应 / Agent Final Response
    
    包含Agent完整执行结果
    Contains complete Agent execution result
    """
    success: bool  # 是否成功 / Is successful
    final_answer: str  # 最终答案 / Final answer
    steps: List[AgentStep] = field(default_factory=list)  # 执行步骤 / Execution steps
    total_iterations: int = 0  # 总迭代次数 / Total iterations
    total_tokens_used: int = 0  # 使用的token总数 / Total tokens used
    execution_time: float = 0.0  # 总执行时间（秒）/ Total execution time (seconds)
    error_message: Optional[str] = None  # 错误信息 / Error message
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 / Convert to dictionary"""
        return {
            "success": self.success,
            "final_answer": self.final_answer,
            "steps": [step.to_dict() for step in self.steps],
            "total_iterations": self.total_iterations,
            "total_tokens_used": self.total_tokens_used,
            "execution_time": self.execution_time,
            "error_message": self.error_message
        }


@dataclass
class UserInput:
    """
    用户输入 / User Input
    
    封装用户输入信息
    Encapsulates user input information
    """
    content: str  # 输入内容 / Input content
    context: Optional[Dict[str, Any]] = None  # 附加上下文 / Additional context
    attachments: List[str] = field(default_factory=list)  # 附件路径 / Attachment paths
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 / Convert to dictionary"""
        return {
            "content": self.content,
            "context": self.context,
            "attachments": self.attachments,
            "timestamp": self.timestamp.isoformat()
        }
