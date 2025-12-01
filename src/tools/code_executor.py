# ==============================================================================
# 代码执行工具 / Code Execution Tool
# ==============================================================================
# 提供安全的代码执行功能
# Provides safe code execution functionality
# ==============================================================================

import subprocess
import sys
import tempfile
from typing import Any, Optional

from pydantic import Field

from src.core.config import get_config
from src.tools.base import BaseTool, ToolInput


class ExecuteCodeInput(ToolInput):
    """代码执行输入 / Code Execution Input"""
    code: str = Field(description="要执行的代码 / Code to execute")
    language: str = Field(default="python", description="编程语言 / Programming language")
    timeout: Optional[int] = Field(default=None, description="执行超时（秒）/ Execution timeout (seconds)")


class CodeExecutorTool(BaseTool):
    """
    代码执行工具 / Code Executor Tool
    
    在安全环境中执行代码并返回结果
    Executes code in a safe environment and returns results
    """
    
    name: str = "execute_code"
    description: str = "执行代码并返回结果。参数：code（代码），language（语言，默认python）/ Execute code and return result. Parameters: code (code), language (language, default python)"
    description_zh: str = "执行代码并返回结果。参数：code（代码），language（语言，默认python）"
    description_en: str = "Execute code and return result. Parameters: code (code), language (language, default python)"
    input_schema = ExecuteCodeInput
    
    def __init__(
        self,
        allowed_languages: Optional[list] = None,
        timeout: Optional[int] = None
    ):
        """
        初始化 / Initialize
        
        Args:
            allowed_languages: 允许的编程语言 / Allowed programming languages
            timeout: 默认执行超时 / Default execution timeout
        """
        super().__init__()
        config = get_config()
        self.allowed_languages = allowed_languages or config.tools.code_executor.allowed_languages
        self.default_timeout = timeout or config.tools.code_executor.timeout
    
    def _run(self, code: str, language: str = "python", timeout: Optional[int] = None) -> str:
        """
        执行代码 / Execute code
        
        Args:
            code: 要执行的代码 / Code to execute
            language: 编程语言 / Programming language
            timeout: 执行超时（秒）/ Execution timeout (seconds)
            
        Returns:
            str: 执行结果 / Execution result
        """
        language = language.lower()
        
        # 检查语言是否允许 / Check if language is allowed
        if language not in self.allowed_languages:
            raise ValueError(f"不支持的语言 / Unsupported language: {language}. 允许的语言 / Allowed languages: {self.allowed_languages}")
        
        exec_timeout = timeout or self.default_timeout
        
        if language == "python":
            return self._execute_python(code, exec_timeout)
        elif language == "javascript":
            return self._execute_javascript(code, exec_timeout)
        else:
            raise ValueError(f"未实现的语言执行器 / Unimplemented language executor: {language}")
    
    def _execute_python(self, code: str, timeout: int) -> str:
        """
        执行Python代码 / Execute Python code
        
        Args:
            code: Python代码 / Python code
            timeout: 超时时间 / Timeout
            
        Returns:
            str: 执行结果 / Execution result
        """
        # 创建临时文件 / Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 执行代码 / Execute code
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = ""
            if result.stdout:
                output += f"输出 / Output:\n{result.stdout}\n"
            if result.stderr:
                output += f"错误 / Error:\n{result.stderr}\n"
            if result.returncode != 0:
                output += f"返回码 / Return code: {result.returncode}"
            
            return output.strip() if output else "代码执行完成，无输出 / Code executed, no output"
            
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"代码执行超时（{timeout}秒）/ Code execution timeout ({timeout} seconds)")
        finally:
            # 清理临时文件 / Clean up temporary file
            import os
            try:
                os.unlink(temp_file)
            except OSError:
                pass
    
    def _execute_javascript(self, code: str, timeout: int) -> str:
        """
        执行JavaScript代码 / Execute JavaScript code
        
        Args:
            code: JavaScript代码 / JavaScript code
            timeout: 超时时间 / Timeout
            
        Returns:
            str: 执行结果 / Execution result
        """
        # 创建临时文件 / Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 执行代码（需要Node.js）/ Execute code (requires Node.js)
            result = subprocess.run(
                ["node", temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = ""
            if result.stdout:
                output += f"输出 / Output:\n{result.stdout}\n"
            if result.stderr:
                output += f"错误 / Error:\n{result.stderr}\n"
            if result.returncode != 0:
                output += f"返回码 / Return code: {result.returncode}"
            
            return output.strip() if output else "代码执行完成，无输出 / Code executed, no output"
            
        except FileNotFoundError:
            raise RuntimeError("未找到Node.js，请确保已安装 / Node.js not found, please ensure it is installed")
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"代码执行超时（{timeout}秒）/ Code execution timeout ({timeout} seconds)")
        finally:
            # 清理临时文件 / Clean up temporary file
            import os
            try:
                os.unlink(temp_file)
            except OSError:
                pass


class PythonREPLTool(BaseTool):
    """
    Python REPL工具 / Python REPL Tool
    
    提供Python交互式执行环境
    Provides Python interactive execution environment
    
    ⚠️ 安全警告 / Security Warning:
    此工具允许执行任意Python代码，这是其设计用途。
    仅在受信任的环境中使用，或配合适当的沙箱机制。
    This tool allows arbitrary Python code execution by design.
    Use only in trusted environments or with proper sandboxing.
    """
    
    name: str = "python_repl"
    description: str = "执行Python代码片段。参数：code（Python代码）/ Execute Python code snippet. Parameters: code (Python code)"
    description_zh: str = "执行Python代码片段。参数：code（Python代码）"
    description_en: str = "Execute Python code snippet. Parameters: code (Python code)"
    
    def __init__(self):
        """初始化 / Initialize"""
        super().__init__()
        self._globals = {}
        self._locals = {}
    
    def _run(self, code: str) -> str:
        """
        执行Python代码 / Execute Python code
        
        ⚠️ 此方法执行任意代码 / This method executes arbitrary code
        
        Args:
            code: Python代码 / Python code
            
        Returns:
            str: 执行结果 / Execution result
        """
        import io
        import contextlib
        
        # 捕获标准输出 / Capture stdout
        stdout_capture = io.StringIO()
        
        try:
            with contextlib.redirect_stdout(stdout_capture):
                # 尝试作为表达式执行 / Try to execute as expression
                try:
                    # 注意：eval/exec执行任意代码是此工具的设计用途
                    # Note: eval/exec for arbitrary code is the intended design
                    result = eval(code, self._globals, self._locals)  # nosec: intentional design
                    if result is not None:
                        print(repr(result))
                except SyntaxError:
                    # 作为语句执行 / Execute as statement
                    exec(code, self._globals, self._locals)  # nosec: intentional design
            
            output = stdout_capture.getvalue()
            return output.strip() if output else "执行完成 / Execution completed"
            
        except Exception as e:
            return f"错误 / Error: {type(e).__name__}: {str(e)}"
    
    def reset(self):
        """重置执行环境 / Reset execution environment"""
        self._globals = {}
        self._locals = {}
