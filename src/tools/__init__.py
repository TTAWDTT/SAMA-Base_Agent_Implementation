# ==============================================================================
# 工具模块
# ==============================================================================
# 提供五个核心工具：shell、file、python、web_search、todo
# 提供五个核心工具：shell、file、python、web_search、todo
# ==============================================================================

from src.tools.base import BaseTool, ToolInput
from src.tools.shell_tool import ShellTool
from src.tools.unified_file_tool import FileTool
from src.tools.python_tool import PythonTool
from src.tools.search_tool import WebSearchTool
from src.tools.todo_tool import TodoTool

# 所有可用工具
ALL_TOOLS = [
    ShellTool,
    FileTool,
    PythonTool,
    WebSearchTool,
    TodoTool,
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
    # 集合
    "ALL_TOOLS",
    "DEFAULT_TOOLS",
]
