# ==============================================================================
# 工具模块 / Tools Module
# ==============================================================================
# 提供四个核心工具：shell、file、python、web_search
# Provides four core tools: shell, file, python, web_search
# ==============================================================================

from src.tools.base import BaseTool, ToolInput
from src.tools.shell_tool import ShellTool
from src.tools.unified_file_tool import FileTool
from src.tools.python_tool import PythonTool
from src.tools.search_tool import WebSearchTool

# 所有可用工具 / All available tools
ALL_TOOLS = [
    ShellTool,
    FileTool,
    PythonTool,
    WebSearchTool,
]

# 默认工具集（与ALL_TOOLS相同）/ Default tool set (same as ALL_TOOLS)
DEFAULT_TOOLS = [
    ShellTool,
    FileTool,
    PythonTool,
    WebSearchTool,
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
    # Collections
    "ALL_TOOLS",
    "DEFAULT_TOOLS",
]
