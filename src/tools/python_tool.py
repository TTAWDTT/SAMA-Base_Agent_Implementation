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
    
    ## 基本描述
    
    执行Python代码并返回结果。支持直接执行代码片段、保存代码到文件、
    执行现有Python文件，以及REPL模式（保持变量状态）。
    
    Executes Python code and returns results. Supports direct code execution,
    saving code to files, running existing Python files, and REPL mode (maintaining variable state).
    
    ## 使用步骤
    
    ### 直接执行代码
    1. 提供 code 参数，包含要执行的Python代码
    2. 可选设置 timeout 超时时间
    3. 代码在独立子进程中执行，输出自动捕获
    
    ### 保存并执行
    1. 提供 code 参数和 save_to 参数
    2. 代码先保存到指定文件，然后执行
    
    ### 执行现有文件
    1. 提供 run_file 参数指定Python文件路径
    2. 不需要提供 code 参数
    
    ### REPL模式
    1. 设置 persistent=true
    2. 多次调用之间变量状态会保持
    3. 适合交互式探索和调试
    
    ## 使用说明
    
    - **code** (与run_file二选一): 要执行的Python代码字符串
    - **timeout** (可选): 执行超时秒数，默认30秒
    - **save_to** (可选): 保存代码的文件路径
    - **run_file** (可选): 要执行的Python文件路径，与code互斥
    - **persistent** (可选): 是否使用REPL模式保持变量状态，默认false
    
    ### 注意事项
    
    - 代码在子进程中执行，与主程序隔离
    - REPL模式下变量会在调用之间保持
    - 执行任意代码是此工具的设计用途，请在受信环境使用
    
    ## 示例
    
    ### 示例1：执行简单代码
    ```json
    {
        "code": "print('Hello, World!')"
    }
    ```
    
    ### 示例2：执行计算代码
    ```json
    {
        "code": "import math\\nresult = math.sqrt(144)\\nprint(f'平方根: {result}')"
    }
    ```
    
    ### 示例3：带超时的长时间计算
    ```json
    {
        "code": "import time\\nfor i in range(5):\\n    print(f'Step {i}')\\n    time.sleep(1)",
        "timeout": 60
    }
    ```
    
    ### 示例4：保存并执行代码
    ```json
    {
        "code": "def greet(name):\\n    return f'Hello, {name}!'\\n\\nprint(greet('User'))",
        "save_to": "C:\\\\project\\\\scripts\\\\greet.py"
    }
    ```
    
    ### 示例5：执行现有文件
    ```json
    {
        "run_file": "C:\\\\project\\\\scripts\\\\main.py",
        "timeout": 120
    }
    ```
    
    ### 示例6：REPL模式（保持状态）
    ```json
    {
        "code": "x = 10\\ny = 20",
        "persistent": true
    }
    ```
    后续调用：
    ```json
    {
        "code": "print(x + y)",
        "persistent": true
    }
    ```
    输出：30（因为x和y在上次调用中定义）
    """
    
    name: str = "python"
    
    description: str = """Python代码执行工具，执行Python代码并返回结果。

## 基本描述

执行Python代码并返回结果。支持直接执行代码片段、保存代码到文件、执行现有Python文件，以及REPL模式。

## 使用步骤

### 直接执行代码
1. 提供 code 参数
2. 可选设置 timeout 超时时间
3. 代码在独立子进程中执行

### 保存并执行
1. 提供 code 和 save_to 参数
2. 代码先保存到文件，然后执行

### 执行现有文件
1. 提供 run_file 参数
2. 不需要 code 参数

### REPL模式
1. 设置 persistent=true
2. 变量状态会在调用之间保持

## 使用说明

- **code** (与run_file二选一): 要执行的Python代码
- **timeout** (可选): 超时秒数，默认30秒
- **save_to** (可选): 保存代码的文件路径
- **run_file** (可选): 要执行的Python文件路径
- **persistent** (可选): 是否使用REPL模式，默认false

## 示例

执行代码：{"code": "print('Hello')"}
带超时：{"code": "long_running_code()", "timeout": 120}
保存执行：{"code": "print('test')", "save_to": "test.py"}
执行文件：{"run_file": "main.py"}
REPL模式：{"code": "x = 10", "persistent": true}
"""
    
    description_zh: str = """Python代码执行工具，执行Python代码并返回结果。

## 基本描述

执行Python代码并返回结果。支持直接执行、保存执行、执行文件、REPL模式。

## 使用步骤

1. 选择执行方式：直接执行、保存执行、执行文件、REPL模式
2. 提供必要参数：code或run_file
3. 设置可选参数：timeout、save_to、persistent

## 使用说明

- **code** (与run_file二选一): 要执行的Python代码
- **timeout** (可选): 超时秒数，默认30秒
- **save_to** (可选): 保存代码的文件路径
- **run_file** (可选): 要执行的Python文件路径
- **persistent** (可选): 是否使用REPL模式，默认false

## 示例

{"code": "print('Hello')", "timeout": 30}
{"code": "x = 10", "persistent": true}
{"run_file": "main.py"}
"""
    
    description_en: str = """Python code execution tool that executes Python code and returns results.

## Basic Description

Executes Python code and returns results. Supports direct execution, save and execute, run file, and REPL mode.

## Usage Steps

1. Choose execution method: direct, save and execute, run file, or REPL
2. Provide required parameters: code or run_file
3. Set optional parameters: timeout, save_to, persistent

## Usage Instructions

- **code** (either code or run_file): Python code to execute
- **timeout** (optional): Timeout in seconds, default 30
- **save_to** (optional): Path to save code to
- **run_file** (optional): Python file to execute
- **persistent** (optional): Use REPL mode, default false

## Examples

{"code": "print('Hello')", "timeout": 30}
{"code": "x = 10", "persistent": true}
{"run_file": "main.py"}
"""
    
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
