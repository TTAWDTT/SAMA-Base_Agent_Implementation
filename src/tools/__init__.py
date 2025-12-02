# ==============================================================================
# 工具模块 / Tools Module
# ==============================================================================

from src.tools.base import BaseTool, ToolInput
from src.tools.file_tool import ReadFileTool, WriteFileTool, ListDirectoryTool
from src.tools.code_executor import CodeExecutorTool, PythonREPLTool
from src.tools.calculator import CalculatorTool
from src.tools.search_tool import WebSearchTool
from src.tools.datetime_tool import GetCurrentTimeTool, DateCalculatorTool, TimeDifferenceTool

# 所有可用工具 / All available tools
ALL_TOOLS = [
    ReadFileTool,
    WriteFileTool,
    ListDirectoryTool,
    CodeExecutorTool,
    PythonREPLTool,
    CalculatorTool,
    WebSearchTool,
    GetCurrentTimeTool,
    DateCalculatorTool,
    TimeDifferenceTool,
]

# 默认工具集 / Default tool set
DEFAULT_TOOLS = [
    ReadFileTool,
    WriteFileTool,
    ListDirectoryTool,
    CodeExecutorTool,
    CalculatorTool,
    GetCurrentTimeTool,
    WebSearchTool,
]

__all__ = [
    # Base
    "BaseTool",
    "ToolInput",
    # File Tools
    "ReadFileTool",
    "WriteFileTool",
    "ListDirectoryTool",
    # Code Tools
    "CodeExecutorTool",
    "PythonREPLTool",
    # Calculator
    "CalculatorTool",
    # Search Tools
    "WebSearchTool",
    # DateTime Tools
    "GetCurrentTimeTool",
    "DateCalculatorTool",
    "TimeDifferenceTool",
    # Collections
    "ALL_TOOLS",
    "DEFAULT_TOOLS",
]
