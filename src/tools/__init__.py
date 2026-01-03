# ==============================================================================
# 工具模块
# ==============================================================================
# 提供核心工具：shell、file、python、web_search、todo、knowledge_search
# ==============================================================================

from src.tools.base import BaseTool, ToolInput
from src.tools.shell_tool import ShellTool
from src.tools.unified_file_tool import FileTool
from src.tools.python_tool import PythonTool
from src.tools.search_tool import WebSearchTool
from src.tools.todo_tool import TodoTool
from src.tools.knowledge_tool import KnowledgeSearchTool
from src.tools.registry import load_plugin_tool_classes, merge_tool_classes, build_plugin_catalog, discover_plugin_files

# 所有可用工具
ALL_TOOLS = [
    ShellTool,
    FileTool,
    PythonTool,
    WebSearchTool,
    TodoTool,
    KnowledgeSearchTool,
]

# 默认工具集（与ALL_TOOLS相同）
DEFAULT_TOOLS = ALL_TOOLS

__all__ = [
    # 基础
    "BaseTool",
    "ToolInput",
    # 核心工具
    "ShellTool",
    "FileTool",
    "PythonTool",
    "WebSearchTool",
    "TodoTool",
    "KnowledgeSearchTool",
    "load_plugin_tool_classes",
    "merge_tool_classes",
    "build_plugin_catalog",
    "discover_plugin_files",
    # 集合
    "ALL_TOOLS",
    "DEFAULT_TOOLS",
]
