# ==============================================================================
# 数据模式定义模块
# ==============================================================================
# 定义Agent使用的各种数据结构
# ==============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentState(Enum):
    """
    Agent状态枚举 / Agent State Enumeration
    """
    IDLE = "idle"  # 空闲
    THINKING = "thinking"  # 思考中
    EXECUTING = "executing"  # 执行工具中
    COMPLETED = "completed"  # 完成
    ERROR = "error"  # 错误
    STOPPED = "stopped"  # 已停止


class ToolResultStatus(Enum):
    """
    工具执行结果状态 / Tool Execution Result Status
    """
    SUCCESS = "success"  # 成功
    ERROR = "error"  # 错误
    TIMEOUT = "timeout"  # 超时


@dataclass
class ToolCall:
    """
    工具调用记录 / Tool Call Record
    
    记录单次工具调用的详细信息
    Records details of a single tool call
    """
    tool_name: str  # 工具名称
    arguments: Dict[str, Any]  # 调用参数
    timestamp: datetime = field(default_factory=datetime.now)
    call_id: Optional[str] = None  # 调用ID
    
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
    tool_name: str  # 工具名称
    status: ToolResultStatus  # 状态
    output: Any  # 输出结果
    error_message: Optional[str] = None  # 错误信息
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
    step_number: int  # 步骤编号
    thinking: str = ""  # 思考内容（Extended Thinking）/ Thinking content
    tool_calls: List[ToolCall] = field(default_factory=list)  # 工具调用列表
    tool_results: List[ToolResult] = field(default_factory=list)  # 工具结果列表
    response: Optional[str] = None  # 最终响应
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 / Convert to dictionary"""
        return {
            "step_number": self.step_number,
            "thinking": self.thinking,
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
    success: bool  # 是否成功
    final_answer: str  # 最终答案
    steps: List[AgentStep] = field(default_factory=list)  # 执行步骤
    total_iterations: int = 0  # 总迭代次数
    total_tokens_used: int = 0  # 使用的token总数
    execution_time: float = 0.0  # 总执行时间（秒）/ Total execution time (seconds)
    error_message: Optional[str] = None  # 错误信息
    
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
