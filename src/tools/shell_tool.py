import os
import subprocess
import platform
from typing import List, Optional

from pydantic import Field

from src.core.config import get_config
from src.tools.base import BaseTool, ToolInput
from src.utils.encoding import decode_output_bytes


class ShellInput(ToolInput):
    """命令输入"""
    command: str = Field(description="要执行的命令")
    timeout: Optional[int] = Field(default=None, description="执行超时（秒）")
    working_directory: Optional[str] = Field(default=None, description="工作目录")


class ShellTool(BaseTool):
    """
    命令行执行工具。

    在系统命令行中执行命令并返回结果，支持超时与工作目录配置。
    """
    
    name: str = "shell"
    subprocess_safe: bool = True
    required_permissions = ["shell"]
    
    description: str = """命令行执行工具，在系统命令行中执行命令并返回结果。

## 使用说明

- **command**（必填）：要执行的命令字符串
- **timeout**（可选）：执行超时秒数，默认30秒
- **working_directory**（可选）：命令执行的工作目录
"""
    
    description_zh: str = description
    
    input_schema = ShellInput
    
    # 默认危险命令黑名单（即使在全放行模式下也禁止）
    DANGEROUS_COMMANDS = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        "dd if=",
        ":(){:|:&};:",  # 叉状炸弹
        "chmod -R 777 /",
        "chown -R",
        "> /dev/sda",
    ]

    # 禁止的命令控制符，避免链式执行或重定向绕过
    FORBIDDEN_TOKENS = [
        "&&",
        "||",
        "|",
        ";",
        ">",
        "<",
        "&",
        "\n",
        "\r",
    ]
    
    def __init__(
        self,
        policy: Optional[str] = None,
        whitelist: Optional[List[str]] = None,
        timeout: Optional[int] = None
    ):
        """
        初始化

        Args:
            policy: 安全策略（allow_all/deny_all/whitelist）
            whitelist: 白名单命令前缀列表
            timeout: 默认超时时间
        """
        super().__init__()
        config = get_config()
        
        # 从配置获取策略
        shell_config = getattr(config.tools, 'shell_tool', None)
        if shell_config:
            self.policy = policy or getattr(shell_config, 'policy', 'whitelist')
            self.whitelist = whitelist or getattr(shell_config, 'whitelist', [])
            self.default_timeout = timeout or getattr(shell_config, 'timeout', 30)
        else:
            self.policy = policy or 'whitelist'
            self.whitelist = whitelist or ['echo', 'ls', 'dir', 'cat', 'type', 'pwd', 'cd', 'head', 'tail', 'grep', 'find', 'where', 'which']
            self.default_timeout = timeout or 30
        
        # 检测系统类型
        self.is_windows = platform.system() == 'Windows'
        self.shell = True if self.is_windows else True
    
    def _is_command_allowed(self, command: str) -> tuple[bool, str]:
        """
        检查命令是否被允许

        Args:
            command: 要检查的命令

        Returns:
            tuple[bool, str]: (是否允许, 原因)
        """
        # 阻断链式执行与重定向
        for token in self.FORBIDDEN_TOKENS:
            if token in command:
                return False, f"命令包含禁止的控制符: {token}"

        # 检查危险命令
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in command:
                return False, f"命令包含危险操作: {dangerous}"
        
        # 根据策略检查
        if self.policy == 'deny_all':
            return False, "命令工具已禁用（deny_all策略）"
        
        if self.policy == 'allow_all':
            return True, ""
        
        # 白名单策略
        if self.policy == 'whitelist':
            cmd_parts = command.strip().split()
            if not cmd_parts:
                return False, "空命令"
            
            cmd_name = cmd_parts[0].lower()
            
            # 检查命令是否在白名单中
            for allowed in self.whitelist:
                if cmd_name == allowed.lower() or cmd_name.startswith(allowed.lower()):
                    return True, ""
            
            return False, f"命令不在白名单中: {cmd_name}"
        
        return False, f"未知策略: {self.policy}"
    
    def _run(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_directory: Optional[str] = None
    ) -> str:
        """
        执行Shell命令

        Args:
            command: 要执行的命令
            timeout: 超时时间
            working_directory: 工作目录

        Returns:
            str: 命令执行结果
        """
        # 检查命令是否被允许
        is_allowed, reason = self._is_command_allowed(command)
        if not is_allowed:
            return f"命令被拒绝: {reason}"
        
        exec_timeout = timeout or self.default_timeout
        cwd = working_directory or os.getcwd()
        
        # 验证工作目录存在
        if not os.path.isdir(cwd):
            return f"工作目录不存在: {cwd}"
        
        try:
            # 执行命令
            result = subprocess.run(
                command,
                shell=self.shell,
                capture_output=True,
                timeout=exec_timeout,
                cwd=cwd,
                text=False
            )
            
            output_parts = []
            
            stdout_text = decode_output_bytes(result.stdout) if result.stdout else ""
            if stdout_text:
                output_parts.append(f"标准输出:\n{stdout_text}")
            
            stderr_text = decode_output_bytes(result.stderr) if result.stderr else ""
            if stderr_text:
                output_parts.append(f"标准错误:\n{stderr_text}")
            
            if result.returncode != 0:
                output_parts.append(f"返回码: {result.returncode}")
            
            if not output_parts:
                return "命令执行成功，无输出"
            
            return "\n\n".join(output_parts)
            
        except subprocess.TimeoutExpired:
            return f"命令执行超时（{exec_timeout}秒）"
        except FileNotFoundError as e:
            return f"命令未找到: {str(e)}"
        except PermissionError as e:
            return f"权限不足: {str(e)}"
        except Exception as e:
            return f"命令执行错误: {str(e)}"
