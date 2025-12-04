# ==============================================================================
# Python代码执行工具 / Python Code Execution Tool
# ==============================================================================
# 提供Python代码编写和执行功能
# Provides Python code writing and execution functionality
#
# 功能说明 / Features:
# - 执行Python代码片段 / Execute Python code snippets
# - 支持持久化执行环境（REPL模式）/ Support persistent execution environment (REPL mode)
# - 自动捕获输出和错误 / Automatically capture output and errors
#
# 安全说明 / Security Note:
# 此工具允许执行任意Python代码，这是其设计用途。
# 仅在受信任的环境中使用，或配合适当的沙箱机制。
# This tool allows arbitrary Python code execution by design.
# Use only in trusted environments or with proper sandboxing.
# ==============================================================================

import io
import os
import sys
import subprocess
import tempfile
import contextlib
from typing import Any, Optional

from pydantic import Field

from src.core.config import get_config
from src.tools.base import BaseTool, ToolInput


class PythonInput(ToolInput):
    """Python代码输入 / Python Code Input"""
    code: str = Field(description="要执行的Python代码 / Python code to execute")
    timeout: Optional[int] = Field(default=None, description="执行超时（秒）/ Execution timeout (seconds)")
    save_to: Optional[str] = Field(default=None, description="保存代码到文件路径（可选）/ Save code to file path (optional)")
    run_file: Optional[str] = Field(default=None, description="执行指定的Python文件（可选，与code互斥）/ Run specified Python file (optional, mutually exclusive with code)")
    persistent: bool = Field(default=False, description="是否使用持久化环境（REPL模式）/ Use persistent environment (REPL mode)")


class PythonTool(BaseTool):
    """
    Python代码执行工具 / Python Code Execution Tool
    
    执行Python代码并返回结果
    Executes Python code and returns results
    
    使用方式 / Usage:
    1. 直接执行代码：传入code参数
    2. 保存并执行：传入code和save_to参数
    3. 执行文件：传入run_file参数
    4. REPL模式：设置persistent=True保持变量状态
    
    ⚠️ 安全警告 / Security Warning:
    此工具允许执行任意Python代码。
    This tool allows arbitrary Python code execution.
    """
    
    name: str = "python"
    description: str = """Python代码执行工具。参数：
- code: 要执行的Python代码
- timeout: 执行超时秒数（默认30）
- save_to: 保存代码到文件路径（可选）
- run_file: 执行指定Python文件（可选，与code互斥）
- persistent: 是否使用REPL模式保持变量状态（默认false）

Python code execution tool. Parameters:
- code: Python code to execute
- timeout: Execution timeout in seconds (default 30)
- save_to: Save code to file path (optional)
- run_file: Run specified Python file (optional, mutually exclusive with code)
- persistent: Use REPL mode to maintain variable state (default false)"""
    
    description_zh: str = """Python代码执行工具。参数：
- code: 要执行的Python代码
- timeout: 执行超时秒数（默认30）
- save_to: 保存代码到文件路径（可选）
- run_file: 执行指定Python文件（可选，与code互斥）
- persistent: 是否使用REPL模式保持变量状态（默认false）"""
    
    description_en: str = """Python code execution tool. Parameters:
- code: Python code to execute
- timeout: Execution timeout in seconds (default 30)
- save_to: Save code to file path (optional)
- run_file: Run specified Python file (optional, mutually exclusive with code)
- persistent: Use REPL mode to maintain variable state (default false)"""
    
    input_schema = PythonInput
    
    def __init__(self, timeout: Optional[int] = None):
        """
        初始化 / Initialize
        
        Args:
            timeout: 默认执行超时 / Default execution timeout
        """
        super().__init__()
        config = get_config()
        self.default_timeout = timeout or config.tools.code_executor.timeout
        
        # REPL模式的持久化环境 / Persistent environment for REPL mode
        self._globals = {}
        self._locals = {}
    
    def _run(
        self,
        code: Optional[str] = None,
        timeout: Optional[int] = None,
        save_to: Optional[str] = None,
        run_file: Optional[str] = None,
        persistent: bool = False
    ) -> str:
        """
        执行Python代码 / Execute Python code
        
        Args:
            code: 要执行的代码 / Code to execute
            timeout: 超时时间 / Timeout
            save_to: 保存路径 / Save path
            run_file: 要执行的文件 / File to run
            persistent: 是否使用持久化环境 / Use persistent environment
            
        Returns:
            str: 执行结果 / Execution result
        """
        exec_timeout = timeout or self.default_timeout
        
        # 如果指定了run_file，执行文件 / If run_file specified, execute file
        if run_file:
            return self._execute_file(run_file, exec_timeout)
        
        # 如果没有code，返回错误 / If no code, return error
        if not code:
            return "错误：必须提供code或run_file参数 / Error: Must provide code or run_file parameter"
        
        # 如果指定了save_to，保存代码到文件 / If save_to specified, save code to file
        if save_to:
            save_result = self._save_code(code, save_to)
            if "错误" in save_result or "Error" in save_result:
                return save_result
        
        # 执行代码 / Execute code
        if persistent:
            return self._execute_repl(code)
        else:
            return self._execute_subprocess(code, exec_timeout)
    
    def _save_code(self, code: str, file_path: str) -> str:
        """
        保存代码到文件 / Save code to file
        
        Args:
            code: Python代码 / Python code
            file_path: 文件路径 / File path
            
        Returns:
            str: 保存结果 / Save result
        """
        try:
            # 确保目录存在 / Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            return f"代码已保存到 / Code saved to: {file_path}"
            
        except Exception as e:
            return f"保存代码错误 / Error saving code: {str(e)}"
    
    def _execute_subprocess(self, code: str, timeout: int) -> str:
        """
        在子进程中执行代码 / Execute code in subprocess
        
        Args:
            code: Python代码 / Python code
            timeout: 超时时间 / Timeout
            
        Returns:
            str: 执行结果 / Execution result
        """
        # 创建临时文件 / Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 执行代码 / Execute code
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            
            output_parts = []
            
            if result.stdout:
                output_parts.append(f"输出 / Output:\n{result.stdout}")
            
            if result.stderr:
                output_parts.append(f"错误 / Error:\n{result.stderr}")
            
            if result.returncode != 0:
                output_parts.append(f"返回码 / Return code: {result.returncode}")
            
            if not output_parts:
                return "代码执行完成，无输出 / Code executed, no output"
            
            return "\n\n".join(output_parts)
            
        except subprocess.TimeoutExpired:
            return f"代码执行超时（{timeout}秒）/ Code execution timeout ({timeout} seconds)"
        except Exception as e:
            return f"代码执行错误 / Code execution error: {str(e)}"
        finally:
            # 清理临时文件 / Clean up temporary file
            try:
                os.unlink(temp_file)
            except OSError:
                pass
    
    def _execute_file(self, file_path: str, timeout: int) -> str:
        """
        执行Python文件 / Execute Python file
        
        Args:
            file_path: 文件路径 / File path
            timeout: 超时时间 / Timeout
            
        Returns:
            str: 执行结果 / Execution result
        """
        if not os.path.exists(file_path):
            return f"文件不存在 / File not found: {file_path}"
        
        try:
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            
            output_parts = []
            
            if result.stdout:
                output_parts.append(f"输出 / Output:\n{result.stdout}")
            
            if result.stderr:
                output_parts.append(f"错误 / Error:\n{result.stderr}")
            
            if result.returncode != 0:
                output_parts.append(f"返回码 / Return code: {result.returncode}")
            
            if not output_parts:
                return f"文件执行完成，无输出 / File executed, no output: {file_path}"
            
            return "\n\n".join(output_parts)
            
        except subprocess.TimeoutExpired:
            return f"文件执行超时（{timeout}秒）/ File execution timeout ({timeout} seconds)"
        except Exception as e:
            return f"文件执行错误 / File execution error: {str(e)}"
    
    def _execute_repl(self, code: str) -> str:
        """
        在持久化REPL环境中执行代码 / Execute code in persistent REPL environment
        
        ⚠️ 此方法执行任意代码 / This method executes arbitrary code
        
        Args:
            code: Python代码 / Python code
            
        Returns:
            str: 执行结果 / Execution result
        """
        # 捕获标准输出 / Capture stdout
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
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
            
            output_parts = []
            
            stdout_output = stdout_capture.getvalue()
            if stdout_output:
                output_parts.append(f"输出 / Output:\n{stdout_output}")
            
            stderr_output = stderr_capture.getvalue()
            if stderr_output:
                output_parts.append(f"警告 / Warning:\n{stderr_output}")
            
            if not output_parts:
                return "执行完成（REPL模式）/ Execution completed (REPL mode)"
            
            return "\n\n".join(output_parts)
            
        except Exception as e:
            return f"执行错误（REPL模式）/ Execution error (REPL mode): {type(e).__name__}: {str(e)}"
    
    def reset_repl(self) -> str:
        """
        重置REPL环境 / Reset REPL environment
        
        Returns:
            str: 重置结果 / Reset result
        """
        self._globals = {}
        self._locals = {}
        return "REPL环境已重置 / REPL environment reset"
    
    def get_repl_variables(self) -> str:
        """
        获取REPL环境中的变量 / Get variables in REPL environment
        
        Returns:
            str: 变量列表 / Variable list
        """
        variables = []
        for name, value in self._locals.items():
            if not name.startswith("_"):
                try:
                    var_type = type(value).__name__
                    var_repr = repr(value)[:100]
                    variables.append(f"  {name} ({var_type}): {var_repr}")
                except Exception:
                    variables.append(f"  {name}: <无法显示 / cannot display>")
        
        if not variables:
            return "REPL环境为空 / REPL environment is empty"
        
        return "REPL环境变量 / REPL environment variables:\n" + "\n".join(variables)
