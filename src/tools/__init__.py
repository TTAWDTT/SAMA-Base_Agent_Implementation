# ==============================================================================
# 工具模块 / Tools Module
# ==============================================================================
# 提供五个核心工具：shell、file、python、web_search、todo
# Provides five core tools: shell, file, python, web_search, todo
# ==============================================================================

from src.tools.base import BaseTool, ToolInput
from src.tools.shell_tool import ShellTool
from src.tools.unified_file_tool import FileTool
from src.tools.python_tool import PythonTool
from src.tools.search_tool import WebSearchTool
from src.tools.todo_tool import TodoTool

# 所有可用工具 / All available tools
ALL_TOOLS = [
    ShellTool,
    FileTool,
    PythonTool,
    WebSearchTool,
    TodoTool,
]

# 默认工具集（与ALL_TOOLS相同）/ Default tool set (same as ALL_TOOLS)
DEFAULT_TOOLS = [
    ShellTool,
    FileTool,
    PythonTool,
    WebSearchTool,
    TodoTool,
]

__all__ = [
    # Base
    "BaseTool",
    "ToolInput",
    # Core Tools
    "ShellTool",
    "FileTool",
    "PythonTool",
    "WebSearchTool",
    "TodoTool",
    # Collections
    "ALL_TOOLS",
    "DEFAULT_TOOLS",
]
