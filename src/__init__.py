# ==============================================================================
# SAMA 智能体主包
# ==============================================================================

from src.agents import BaseAgent
from src.core import (
    Config,
    get_config,
    load_config,
    get_logger,
    init_logging,
    FileContext,
    ConversationMemory,
    get_memory,
    reset_memory,
    AgentState,
    ToolResultStatus,
    ToolCall,
    ToolResult,
    AgentStep,
    AgentResponse,
)
from src.core.config import (
    ArtifactsConfig,
    ObservabilityConfig,
    ProfileConfig,
    QueueConfig,
    DashboardConfig,
    ChatUIConfig,
    NotificationEventConfig,
    NotificationsConfig,
    KnowledgeBaseConfig,
)
from src.core.profiles import (
    list_profiles,
    resolve_profile,
    apply_profile_to_agent,
)
from src.tools import (
    BaseTool,
    ToolInput,
    ShellTool,
    FileTool,
    PythonTool,
    WebSearchTool,
    ALL_TOOLS,
    DEFAULT_TOOLS,
)
from src.utils import (
    DocumentConverter,
    preprocess_files,
    get_supported_extensions,
    is_file_supported,
)
from src.runtime import (
    save_task_result,
    snapshot_top_level_files,
    move_top_level_files_to_output,
    append_task_history,
    append_task_index,
    update_task_artifact_index,
    create_task_archive,
    cleanup_task_outputs,
    TaskSpec,
    TaskResult,
    TaskRunner,
    TaskQueue,
    QueueItem,
    build_tool_metrics,
    update_tool_metrics_store,
)
from src.dashboard import run_dashboard
from src.webui import run_chat_ui

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # 智能体
    "BaseAgent",
    # 配置
    "Config",
    "ArtifactsConfig",
    "ObservabilityConfig",
    "ProfileConfig",
    "QueueConfig",
    "DashboardConfig",
    "ChatUIConfig",
    "NotificationEventConfig",
    "NotificationsConfig",
    "KnowledgeBaseConfig",
    "get_config",
    "load_config",
    # 日志
    "get_logger",
    "init_logging",
    # 记忆
    "FileContext",
    "ConversationMemory",
    "get_memory",
    "reset_memory",
    # 数据结构
    "AgentState",
    "ToolResultStatus",
    "ToolCall",
    "ToolResult",
    "AgentStep",
    "AgentResponse",
    # 模板
    "list_profiles",
    "resolve_profile",
    "apply_profile_to_agent",
    # 工具
    "BaseTool",
    "ToolInput",
    "ShellTool",
    "FileTool",
    "PythonTool",
    "WebSearchTool",
    "ALL_TOOLS",
    "DEFAULT_TOOLS",
    # 文档处理
    "DocumentConverter",
    "preprocess_files",
    "get_supported_extensions",
    "is_file_supported",
    # 运行时
    "save_task_result",
    "snapshot_top_level_files",
    "move_top_level_files_to_output",
    "append_task_history",
    "append_task_index",
    "update_task_artifact_index",
    "create_task_archive",
    "cleanup_task_outputs",
    "TaskSpec",
    "TaskResult",
    "TaskRunner",
    "TaskQueue",
    "QueueItem",
    "build_tool_metrics",
    "update_tool_metrics_store",
    # 仪表盘
    "run_dashboard",
    # 聊天前端
    "run_chat_ui",
]
