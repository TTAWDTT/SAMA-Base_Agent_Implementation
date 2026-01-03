import io
import os
import sys
import subprocess
import tempfile
import contextlib
from typing import Optional

from pydantic import Field

from src.core.config import get_config
from src.tools.base import BaseTool, ToolInput
from src.utils.encoding import decode_output_bytes


class PythonInput(ToolInput):
    """Python代码输入"""
    code: str = Field(description="要执行的Python代码")
    timeout: Optional[int] = Field(default=None, description="执行超时（秒）")
    save_to: Optional[str] = Field(default=None, description="保存代码到文件路径（可选）")
    run_file: Optional[str] = Field(default=None, description="执行指定的Python文件（可选，与code互斥）")
    persistent: bool = Field(default=False, description="是否使用持久化环境（REPL模式）")


class PythonTool(BaseTool):
    """
    Python代码执行工具。

    支持执行代码片段、执行文件与REPL模式，可选超时与保存路径。
    """
    
    name: str = "python"
    subprocess_safe: bool = True
    required_permissions = ["python"]
    
    description: str = """Python代码执行工具，执行Python代码并返回结果。

## 使用说明

- **code**（与run_file二选一）：要执行的Python代码
- **run_file**（与code二选一）：要执行的Python文件路径
- **timeout**（可选）：超时秒数，默认30秒
- **save_to**（可选）：保存代码的文件路径
- **persistent**（可选）：是否使用REPL模式
"""
    
    description_zh: str = description
    
    input_schema = PythonInput
    
    def __init__(self, timeout: Optional[int] = None):
        """
        初始化

        Args:
            timeout: 默认执行超时
        """
        super().__init__()
        config = get_config()
        self.default_timeout = timeout or config.tools.code_executor.timeout
        
        # 交互式模式的持久化环境
        self._globals = {}
        self._locals = {}

    def should_run_in_subprocess(self, arguments: dict) -> bool:
        """
        持久化模式需要保留上下文，避免子进程执行
        """
        if arguments.get("persistent"):
            return False
        return self.subprocess_safe

    def can_run_in_parallel(self, arguments: dict) -> bool:
        """
        持久化模式避免并行
        """
        return not arguments.get("persistent")
    
    def _run(
        self,
        code: Optional[str] = None,
        timeout: Optional[int] = None,
        save_to: Optional[str] = None,
        run_file: Optional[str] = None,
        persistent: bool = False
    ) -> str:
        """
        执行Python代码

        Args:
            code: 要执行的代码
            timeout: 超时时间
            save_to: 保存路径
            run_file: 要执行的文件
            persistent: 是否使用持久化环境

        Returns:
            str: 执行结果
        """
        exec_timeout = timeout or self.default_timeout
        
        # 如果指定了文件路径，直接执行文件
        if run_file:
            return self._execute_file(run_file, exec_timeout)
        
        # 如果没有代码，返回错误
        if not code:
            return "错误：必须提供 code 或 run_file 参数"
        
        # 如果指定了保存路径，先保存代码
        if save_to:
            save_result = self._save_code(code, save_to)
            if "错误" in save_result or "Error" in save_result:
                return save_result
        
        # 执行代码
        if persistent:
            return self._execute_repl(code)
        else:
            return self._execute_subprocess(code, exec_timeout)
    
    def _save_code(self, code: str, file_path: str) -> str:
        """
        保存代码到文件

        Args:
            code: Python代码
            file_path: 文件路径

        Returns:
            str: 保存结果
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            return f"代码已保存到: {file_path}"
            
        except Exception as e:
            return f"保存代码错误: {str(e)}"
    
    def _execute_subprocess(self, code: str, timeout: int) -> str:
        """
        在子进程中执行代码

        Args:
            code: Python代码
            timeout: 超时时间

        Returns:
            str: 执行结果
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 执行代码
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                timeout=timeout,
                text=False
            )
            
            output_parts = []
            
            stdout_text = decode_output_bytes(result.stdout) if result.stdout else ""
            if stdout_text:
                output_parts.append(f"输出:\n{stdout_text}")
            
            stderr_text = decode_output_bytes(result.stderr) if result.stderr else ""
            if stderr_text:
                output_parts.append(f"错误:\n{stderr_text}")
            
            if result.returncode != 0:
                output_parts.append(f"返回码: {result.returncode}")
            
            if not output_parts:
                return "代码执行完成，无输出"
            
            return "\n\n".join(output_parts)
            
        except subprocess.TimeoutExpired:
            return f"代码执行超时（{timeout}秒）"
        except Exception as e:
            return f"代码执行错误: {str(e)}"
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except OSError:
                pass
    
    def _execute_file(self, file_path: str, timeout: int) -> str:
        """
        执行Python文件

        Args:
            file_path: 文件路径
            timeout: 超时时间

        Returns:
            str: 执行结果
        """
        if not os.path.exists(file_path):
            return f"文件不存在: {file_path}"
        
        try:
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                timeout=timeout,
                text=False
            )
            
            output_parts = []
            
            stdout_text = decode_output_bytes(result.stdout) if result.stdout else ""
            if stdout_text:
                output_parts.append(f"输出:\n{stdout_text}")
            
            stderr_text = decode_output_bytes(result.stderr) if result.stderr else ""
            if stderr_text:
                output_parts.append(f"错误:\n{stderr_text}")
            
            if result.returncode != 0:
                output_parts.append(f"返回码: {result.returncode}")
            
            if not output_parts:
                return f"文件执行完成，无输出: {file_path}"
            
            return "\n\n".join(output_parts)
            
        except subprocess.TimeoutExpired:
            return f"文件执行超时（{timeout}秒）"
        except Exception as e:
            return f"文件执行错误: {str(e)}"
    
    def _execute_repl(self, code: str) -> str:
        """
        在持久化REPL环境中执行代码

        注意：该方法执行任意代码

        Args:
            code: Python代码

        Returns:
            str: 执行结果
        """
        # 捕获标准输出
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                # 尝试作为表达式执行
                try:
                    # 注意：此处执行任意代码是该工具的设计用途
                    result = eval(code, self._globals, self._locals)  # nosec: intentional design
                    if result is not None:
                        print(repr(result))
                except SyntaxError:
                    # 作为语句执行
                    exec(code, self._globals, self._locals)  # nosec: intentional design

            output_parts = []

            stdout_output = stdout_capture.getvalue()
            if stdout_output:
                output_parts.append(f"输出:\n{stdout_output}")

            stderr_output = stderr_capture.getvalue()
            if stderr_output:
                output_parts.append(f"警告:\n{stderr_output}")

            if not output_parts:
                return "执行完成（REPL模式）"

            return "\n\n".join(output_parts)

        except Exception as e:
            return f"执行错误（REPL模式）: {type(e).__name__}: {str(e)}"
