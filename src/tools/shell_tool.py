# ==============================================================================
# Shell命令执行工具 / Shell Command Execution Tool
# ==============================================================================
# 提供系统Shell命令执行功能，支持策略控制
# Provides system shell command execution with policy control
#
# 安全说明 / Security Note:
# - 通过 config.yaml 中的 shell_tool 配置控制允许策略
# - 支持三种模式：allow_all（允许所有）、deny_all（拒绝所有）、whitelist（白名单）
# - Security is controlled via shell_tool config in config.yaml
# - Supports three modes: allow_all, deny_all, whitelist
# ==============================================================================

import os
import subprocess
import platform
from typing import Any, List, Optional

from pydantic import Field

from src.core.config import get_config
from src.tools.base import BaseTool, ToolInput


class ShellInput(ToolInput):
    """Shell命令输入 / Shell Command Input"""
    command: str = Field(description="要执行的Shell命令 / Shell command to execute")
    timeout: Optional[int] = Field(default=None, description="执行超时（秒）/ Execution timeout (seconds)")
    working_directory: Optional[str] = Field(default=None, description="工作目录 / Working directory")


class ShellTool(BaseTool):
    """
    Shell命令执行工具 / Shell Command Execution Tool
    
    ## 基本描述
    
    在系统Shell中执行命令并返回结果。支持Windows和Unix系统，
    自动检测操作系统并选择合适的Shell环境。
    
    Executes commands in system shell and returns results. Supports Windows and Unix systems,
    automatically detects OS and selects appropriate shell environment.
    
    ## 使用步骤
    
    1. **准备命令**：确定要执行的Shell命令
    2. **设置参数**：配置超时时间和工作目录（可选）
    3. **执行命令**：调用工具执行命令
    4. **处理结果**：解析返回的stdout/stderr输出
    
    ## 使用说明
    
    - **command** (必填): 要执行的Shell命令字符串
    - **timeout** (可选): 执行超时秒数，默认30秒
    - **working_directory** (可选): 命令执行的工作目录，默认当前目录
    
    ### 安全策略
    
    - **allow_all**: 允许执行所有命令（危险，仅限受信环境）
    - **deny_all**: 禁止执行任何命令
    - **whitelist**: 只允许白名单中的命令（推荐）
    
    ### 注意事项
    
    - 路径包含空格时需用引号括起
    - 尽量使用绝对路径，避免使用cd切换目录
    - 多个独立命令可用&&链接
    - 避免使用此工具进行文件读写操作，应使用file工具
    
    ## 示例
    
    ### 示例1：列出目录内容
    ```json
    {
        "command": "dir",
        "working_directory": "C:\\Users"
    }
    ```
    
    ### 示例2：带超时的命令
    ```json
    {
        "command": "ping localhost -n 5",
        "timeout": 60
    }
    ```
    
    ### 示例3：链式命令
    ```json
    {
        "command": "git status && git log --oneline -5"
    }
    ```
    """
    
    name: str = "shell"
    
    description: str = """Shell命令执行工具，在系统Shell中执行命令并返回结果。

## 基本描述

在系统Shell中执行命令并返回结果。支持Windows和Unix系统，自动检测操作系统。

## 使用步骤

1. **准备命令**：确定要执行的Shell命令
2. **设置参数**：配置超时时间和工作目录（可选）
3. **执行命令**：调用工具执行命令
4. **处理结果**：解析返回的stdout/stderr输出

## 使用说明

- **command** (必填): 要执行的Shell命令字符串
- **timeout** (可选): 执行超时秒数，默认30秒
- **working_directory** (可选): 命令执行的工作目录

### 安全策略

- allow_all: 允许执行所有命令（危险）
- deny_all: 禁止执行任何命令
- whitelist: 只允许白名单中的命令（推荐）

### 注意事项

- 路径包含空格时需用引号括起
- 尽量使用绝对路径，避免频繁切换目录
- 避免使用此工具进行文件读写，应使用file工具

## 示例

列出目录：{"command": "dir", "working_directory": "C:\\\\Users"}
带超时：{"command": "ping localhost -n 5", "timeout": 60}
链式命令：{"command": "git status && git log --oneline -5"}
"""
    
    description_zh: str = """Shell命令执行工具，在系统Shell中执行命令并返回结果。

## 基本描述

在系统Shell中执行命令并返回结果。支持Windows和Unix系统。

## 使用步骤

1. 准备命令：确定要执行的Shell命令
2. 设置参数：配置超时时间和工作目录（可选）
3. 执行命令：调用工具执行命令
4. 处理结果：解析返回的stdout/stderr输出

## 使用说明

- **command** (必填): 要执行的Shell命令
- **timeout** (可选): 超时秒数，默认30秒
- **working_directory** (可选): 工作目录

## 示例

{"command": "dir", "timeout": 30, "working_directory": "C:\\\\Users"}
"""
    
    description_en: str = """Shell command execution tool that executes commands in system shell.

## Basic Description

Executes commands in system shell and returns results. Supports Windows and Unix.

## Usage Steps

1. Prepare command: Determine the shell command to execute
2. Set parameters: Configure timeout and working directory (optional)
3. Execute: Call the tool to run the command
4. Handle results: Parse stdout/stderr output

## Usage Instructions

- **command** (required): Shell command string to execute
- **timeout** (optional): Timeout in seconds, default 30
- **working_directory** (optional): Working directory for command

## Examples

{"command": "ls -la", "timeout": 30, "working_directory": "/home/user"}
"""
    
    input_schema = ShellInput
    
    # 默认危险命令黑名单（即使在allow_all模式下也禁止）
    # Default dangerous command blacklist (forbidden even in allow_all mode)
    DANGEROUS_COMMANDS = [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        "dd if=",
        ":(){:|:&};:",  # Fork bomb
        "chmod -R 777 /",
        "chown -R",
        "> /dev/sda",
    ]
    
    def __init__(
        self,
        policy: Optional[str] = None,
        whitelist: Optional[List[str]] = None,
        timeout: Optional[int] = None
    ):
        """
        初始化 / Initialize
        
        Args:
            policy: 安全策略（allow_all/deny_all/whitelist）/ Security policy
            whitelist: 白名单命令前缀列表 / Whitelist command prefix list
            timeout: 默认超时时间 / Default timeout
        """
        super().__init__()
        config = get_config()
        
        # 从配置获取策略 / Get policy from config
        shell_config = getattr(config.tools, 'shell_tool', None)
        if shell_config:
            self.policy = policy or getattr(shell_config, 'policy', 'whitelist')
            self.whitelist = whitelist or getattr(shell_config, 'whitelist', [])
            self.default_timeout = timeout or getattr(shell_config, 'timeout', 30)
        else:
            self.policy = policy or 'whitelist'
            self.whitelist = whitelist or ['echo', 'ls', 'dir', 'cat', 'type', 'pwd', 'cd', 'head', 'tail', 'grep', 'find', 'where', 'which']
            self.default_timeout = timeout or 30
        
        # 检测系统类型 / Detect system type
        self.is_windows = platform.system() == 'Windows'
        self.shell = True if self.is_windows else True
    
    def _is_command_allowed(self, command: str) -> tuple[bool, str]:
        """
        检查命令是否被允许 / Check if command is allowed
        
        Args:
            command: 要检查的命令 / Command to check
            
        Returns:
            tuple[bool, str]: (是否允许, 原因) / (is allowed, reason)
        """
        # 检查危险命令 / Check dangerous commands
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in command:
                return False, f"命令包含危险操作 / Command contains dangerous operation: {dangerous}"
        
        # 根据策略检查 / Check based on policy
        if self.policy == 'deny_all':
            return False, "Shell工具已禁用（deny_all策略）/ Shell tool disabled (deny_all policy)"
        
        if self.policy == 'allow_all':
            return True, ""
        
        # whitelist策略 / Whitelist policy
        if self.policy == 'whitelist':
            cmd_parts = command.strip().split()
            if not cmd_parts:
                return False, "空命令 / Empty command"
            
            cmd_name = cmd_parts[0].lower()
            
            # 检查命令是否在白名单中 / Check if command is in whitelist
            for allowed in self.whitelist:
                if cmd_name == allowed.lower() or cmd_name.startswith(allowed.lower()):
                    return True, ""
            
            return False, f"命令不在白名单中 / Command not in whitelist: {cmd_name}"
        
        return False, f"未知策略 / Unknown policy: {self.policy}"
    
    def _run(
        self,
        command: str,
        timeout: Optional[int] = None,
        working_directory: Optional[str] = None
    ) -> str:
        """
        执行Shell命令 / Execute shell command
        
        Args:
            command: 要执行的命令 / Command to execute
            timeout: 超时时间 / Timeout
            working_directory: 工作目录 / Working directory
            
        Returns:
            str: 命令执行结果 / Command execution result
        """
        # 检查命令是否被允许 / Check if command is allowed
        is_allowed, reason = self._is_command_allowed(command)
        if not is_allowed:
            return f"命令被拒绝 / Command denied: {reason}"
        
        exec_timeout = timeout or self.default_timeout
        cwd = working_directory or os.getcwd()
        
        # 验证工作目录存在 / Verify working directory exists
        if not os.path.isdir(cwd):
            return f"工作目录不存在 / Working directory does not exist: {cwd}"
        
        try:
            # 执行命令 / Execute command
            result = subprocess.run(
                command,
                shell=self.shell,
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                cwd=cwd,
                encoding='utf-8',
                errors='replace'
            )
            
            output_parts = []
            
            if result.stdout:
                output_parts.append(f"标准输出 / Stdout:\n{result.stdout}")
            
            if result.stderr:
                output_parts.append(f"标准错误 / Stderr:\n{result.stderr}")
            
            if result.returncode != 0:
                output_parts.append(f"返回码 / Return code: {result.returncode}")
            
            if not output_parts:
                return "命令执行成功，无输出 / Command executed successfully, no output"
            
            return "\n\n".join(output_parts)
            
        except subprocess.TimeoutExpired:
            return f"命令执行超时（{exec_timeout}秒）/ Command execution timeout ({exec_timeout} seconds)"
        except FileNotFoundError as e:
            return f"命令未找到 / Command not found: {str(e)}"
        except PermissionError as e:
            return f"权限不足 / Permission denied: {str(e)}"
        except Exception as e:
            return f"命令执行错误 / Command execution error: {str(e)}"
