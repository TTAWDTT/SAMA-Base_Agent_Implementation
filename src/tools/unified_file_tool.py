# ==============================================================================
# 统一文件操作工具 / Unified File Operation Tool
# ==============================================================================
# 整合read、write、list等文件操作到单一工具
# Consolidates read, write, list file operations into a single tool
#
# 操作说明 / Operation Guide:
# - read: 读取文件内容 / Read file content
# - write: 写入文件内容（支持覆盖和追加）/ Write file content (overwrite or append)
# - list: 列出目录内容 / List directory content
#
# 写入功能增强 / Write Enhancement:
# - 自动创建父目录 / Auto-create parent directories
# - 支持追加模式 / Support append mode
# - 写入前可选备份 / Optional backup before write
# ==============================================================================

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, List, Literal, Optional

from pydantic import Field

from src.core.config import get_config
from src.tools.base import BaseTool, ToolInput


class FileInput(ToolInput):
    """文件操作输入 / File Operation Input"""
    operation: Literal["read", "write", "list"] = Field(
        description="操作类型：read（读取）、write（写入）、list（列目录）/ Operation type: read, write, list"
    )
    path: str = Field(description="文件或目录路径 / File or directory path")
    content: Optional[str] = Field(default=None, description="写入内容（仅write操作需要）/ Content to write (only for write operation)")
    encoding: str = Field(default="utf-8", description="文件编码 / File encoding")
    append: bool = Field(default=False, description="是否追加模式（仅write操作）/ Append mode (only for write operation)")
    recursive: bool = Field(default=False, description="是否递归列出（仅list操作）/ Recursive listing (only for list operation)")
    backup: bool = Field(default=False, description="写入前是否备份原文件（仅write操作）/ Backup original file before write (only for write operation)")
    create_dirs: bool = Field(default=True, description="是否自动创建父目录（仅write操作）/ Auto-create parent directories (only for write operation)")


class FileTool(BaseTool):
    """
    统一文件操作工具 / Unified File Operation Tool
    
    ## 基本描述
    
    提供文件读取、写入、目录列表功能的统一工具。
    支持自动创建目录、文件备份、追加写入等高级功能。
    
    Provides unified file read, write, and directory listing functionality.
    Supports auto-creating directories, file backup, append writing and other advanced features.
    
    ## 使用步骤
    
    ### 读取文件 (read)
    1. 设置 operation 为 "read"
    2. 提供文件路径 path
    3. 可选指定编码 encoding
    
    ### 写入文件 (write)
    1. 设置 operation 为 "write"
    2. 提供文件路径 path 和内容 content
    3. 可选设置追加模式 append、备份 backup、自动创建目录 create_dirs
    
    ### 列出目录 (list)
    1. 设置 operation 为 "list"
    2. 提供目录路径 path
    3. 可选设置递归列出 recursive
    
    ## 使用说明
    
    - **operation** (必填): 操作类型，可选值 read/write/list
    - **path** (必填): 文件或目录的路径
    - **content** (write操作必填): 要写入的文件内容
    - **encoding** (可选): 文件编码，默认 utf-8
    - **append** (可选): 是否追加模式，默认 false
    - **recursive** (可选): 是否递归列出目录，默认 false
    - **backup** (可选): 写入前是否备份原文件，默认 false
    - **create_dirs** (可选): 是否自动创建父目录，默认 true
    
    ### 安全说明
    
    - 仅允许访问配置中指定的目录
    - 路径会自动规范化处理
    
    ## 示例
    
    ### 示例1：读取文件
    ```json
    {
        "operation": "read",
        "path": "C:\\\\project\\\\readme.md",
        "encoding": "utf-8"
    }
    ```
    
    ### 示例2：写入文件（自动创建目录）
    ```json
    {
        "operation": "write",
        "path": "C:\\\\project\\\\docs\\\\guide.md",
        "content": "# 使用指南\\n\\n这是内容...",
        "create_dirs": true
    }
    ```
    
    ### 示例3：追加内容到文件
    ```json
    {
        "operation": "write",
        "path": "C:\\\\project\\\\log.txt",
        "content": "新的日志条目\\n",
        "append": true
    }
    ```
    
    ### 示例4：备份后写入
    ```json
    {
        "operation": "write",
        "path": "C:\\\\project\\\\config.yaml",
        "content": "new: config",
        "backup": true
    }
    ```
    
    ### 示例5：列出目录
    ```json
    {
        "operation": "list",
        "path": "C:\\\\project",
        "recursive": false
    }
    ```
    
    ### 示例6：递归列出目录
    ```json
    {
        "operation": "list",
        "path": "C:\\\\project\\\\src",
        "recursive": true
    }
    ```
    """
    
    name: str = "file"
    
    description: str = """文件操作工具，支持读取、写入、列目录。

## 基本描述

提供文件读取、写入、目录列表功能的统一工具。支持自动创建目录、文件备份、追加写入等。

## 使用步骤

### 读取文件 (read)
1. 设置 operation 为 "read"
2. 提供文件路径 path
3. 可选指定编码 encoding

### 写入文件 (write)
1. 设置 operation 为 "write"
2. 提供文件路径 path 和内容 content
3. 可选设置追加模式 append、备份 backup、自动创建目录 create_dirs

### 列出目录 (list)
1. 设置 operation 为 "list"
2. 提供目录路径 path
3. 可选设置递归列出 recursive

## 使用说明

- **operation** (必填): 操作类型（read/write/list）
- **path** (必填): 文件或目录路径
- **content** (write操作必填): 写入内容
- **encoding** (可选): 文件编码，默认utf-8
- **append** (可选): 是否追加模式，默认false
- **recursive** (可选): 是否递归列出，默认false
- **backup** (可选): 写入前是否备份，默认false
- **create_dirs** (可选): 是否自动创建目录，默认true

## 示例

读取文件：{"operation": "read", "path": "readme.md"}
写入文件：{"operation": "write", "path": "output.txt", "content": "内容"}
追加写入：{"operation": "write", "path": "log.txt", "content": "日志", "append": true}
列出目录：{"operation": "list", "path": "./src", "recursive": true}
"""
    
    description_zh: str = """文件操作工具，支持读取、写入、列目录。

## 基本描述

提供文件读取、写入、目录列表功能的统一工具。

## 使用步骤

1. 选择操作类型：read（读取）、write（写入）、list（列目录）
2. 提供必要参数：path（路径），write操作需要content（内容）
3. 设置可选参数：encoding、append、backup、create_dirs、recursive

## 使用说明

- **operation** (必填): 操作类型（read/write/list）
- **path** (必填): 文件或目录路径
- **content** (write操作必填): 写入内容
- **encoding** (可选): 文件编码，默认utf-8
- **append** (可选): 追加模式，默认false
- **recursive** (可选): 递归列出，默认false
- **backup** (可选): 写入前备份，默认false
- **create_dirs** (可选): 自动创建目录，默认true

## 示例

{"operation": "read", "path": "readme.md"}
{"operation": "write", "path": "out.txt", "content": "内容", "append": true}
{"operation": "list", "path": "./src", "recursive": true}
"""
    
    description_en: str = """File operation tool supporting read, write, and list operations.

## Basic Description

Unified tool for file read, write, and directory listing. Supports auto-creating directories, backup, append mode.

## Usage Steps

1. Choose operation type: read, write, or list
2. Provide required parameters: path, content (for write)
3. Set optional parameters: encoding, append, backup, create_dirs, recursive

## Usage Instructions

- **operation** (required): Operation type (read/write/list)
- **path** (required): File or directory path
- **content** (required for write): Content to write
- **encoding** (optional): File encoding, default utf-8
- **append** (optional): Append mode, default false
- **recursive** (optional): Recursive listing, default false
- **backup** (optional): Backup before write, default false
- **create_dirs** (optional): Auto-create directories, default true

## Examples

{"operation": "read", "path": "readme.md"}
{"operation": "write", "path": "out.txt", "content": "content", "append": true}
{"operation": "list", "path": "./src", "recursive": true}
"""
    
    input_schema = FileInput
    
    def __init__(self, allowed_directories: Optional[List[str]] = None):
        """
        初始化 / Initialize
        
        Args:
            allowed_directories: 允许访问的目录列表 / List of allowed directories
        """
        super().__init__()
        config = get_config()
        self.allowed_directories = allowed_directories or config.tools.file_tool.allowed_directories
    
    def _is_path_allowed(self, file_path: str) -> bool:
        """
        检查路径是否在允许范围内 / Check if path is within allowed range
        
        Args:
            file_path: 文件路径 / File path
            
        Returns:
            bool: 是否允许访问 / Whether access is allowed
        """
        abs_path = os.path.normpath(os.path.abspath(file_path))
        for allowed_dir in self.allowed_directories:
            allowed_abs = os.path.normpath(os.path.abspath(allowed_dir))
            # 使用normpath确保路径分隔符一致，支持Windows和Unix
            # Use normpath to ensure consistent path separators for Windows and Unix
            if abs_path.startswith(allowed_abs):
                # 确保匹配的是完整的目录，不是前缀重叠
                # Ensure the match is for complete directory, not prefix overlap
                if len(abs_path) == len(allowed_abs) or abs_path[len(allowed_abs)] in (os.sep, os.altsep or ''):
                    return True
        return False
    
    def _run(
        self,
        operation: str,
        path: str,
        content: Optional[str] = None,
        encoding: str = "utf-8",
        append: bool = False,
        recursive: bool = False,
        backup: bool = False,
        create_dirs: bool = True
    ) -> str:
        """
        执行文件操作 / Execute file operation
        
        Args:
            operation: 操作类型 / Operation type
            path: 文件或目录路径 / File or directory path
            content: 写入内容 / Content to write
            encoding: 文件编码 / File encoding
            append: 是否追加模式 / Append mode
            recursive: 是否递归列出 / Recursive listing
            backup: 是否备份 / Backup before write
            create_dirs: 是否创建父目录 / Create parent directories
            
        Returns:
            str: 操作结果 / Operation result
        """
        operation = operation.lower().strip()
        
        if operation == "read":
            return self._read_file(path, encoding)
        elif operation == "write":
            return self._write_file(path, content, encoding, append, backup, create_dirs)
        elif operation == "list":
            return self._list_directory(path, recursive)
        else:
            return f"未知操作类型 / Unknown operation type: {operation}. 支持的操作 / Supported operations: read, write, list"
    
    def _read_file(self, file_path: str, encoding: str = "utf-8") -> str:
        """
        读取文件 / Read file
        
        Args:
            file_path: 文件路径 / File path
            encoding: 文件编码 / File encoding
            
        Returns:
            str: 文件内容 / File content
        """
        # 检查路径安全性 / Check path security
        if not self._is_path_allowed(file_path):
            return f"不允许访问该路径 / Access to this path is not allowed: {file_path}"
        
        if not os.path.exists(file_path):
            return f"文件不存在 / File not found: {file_path}"
        
        if os.path.isdir(file_path):
            return f"路径是目录，请使用list操作 / Path is a directory, use list operation: {file_path}"
        
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            
            file_size = os.path.getsize(file_path)
            return f"文件内容 / File content ({file_size} bytes):\n\n{content}"
        except UnicodeDecodeError as e:
            return f"文件编码错误 / File encoding error: {str(e)}. 尝试使用其他编码 / Try another encoding"
        except Exception as e:
            return f"读取文件错误 / Error reading file: {str(e)}"
    
    def _write_file(
        self,
        file_path: str,
        content: Optional[str],
        encoding: str = "utf-8",
        append: bool = False,
        backup: bool = False,
        create_dirs: bool = True
    ) -> str:
        """
        写入文件 / Write file
        
        Args:
            file_path: 文件路径 / File path
            content: 文件内容 / File content
            encoding: 文件编码 / File encoding
            append: 是否追加模式 / Append mode
            backup: 是否备份 / Backup before write
            create_dirs: 是否创建父目录 / Create parent directories
            
        Returns:
            str: 操作结果 / Operation result
        """
        # 检查路径安全性 / Check path security
        if not self._is_path_allowed(file_path):
            return f"不允许访问该路径 / Access to this path is not allowed: {file_path}"
        
        if content is None:
            return "写入内容不能为空 / Content cannot be empty for write operation"
        
        try:
            abs_path = os.path.abspath(file_path)
            parent_dir = os.path.dirname(abs_path)
            
            # 创建父目录 / Create parent directories
            if create_dirs and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                self.logger.info(f"创建目录 / Created directory: {parent_dir}")
            
            # 备份原文件 / Backup original file
            if backup and os.path.exists(abs_path):
                backup_path = f"{abs_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(abs_path, backup_path)
                self.logger.info(f"已备份到 / Backed up to: {backup_path}")
            
            # 写入文件 / Write file
            mode = "a" if append else "w"
            with open(abs_path, mode, encoding=encoding) as f:
                f.write(content)
            
            # 获取文件信息 / Get file info
            file_size = os.path.getsize(abs_path)
            mode_text = "追加 / appended" if append else "写入 / written"
            
            result = f"文件{mode_text}成功 / File {mode_text} successfully: {file_path}\n"
            result += f"文件大小 / File size: {file_size} bytes\n"
            result += f"内容长度 / Content length: {len(content)} characters"
            
            if backup and os.path.exists(f"{abs_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"):
                result += f"\n备份文件 / Backup file: {backup_path}"
            
            return result
            
        except PermissionError as e:
            return f"权限不足 / Permission denied: {str(e)}"
        except Exception as e:
            return f"写入文件错误 / Error writing file: {str(e)}"
    
    def _list_directory(self, directory_path: str, recursive: bool = False) -> str:
        """
        列出目录 / List directory
        
        Args:
            directory_path: 目录路径 / Directory path
            recursive: 是否递归列出 / Recursive listing
            
        Returns:
            str: 目录内容 / Directory content
        """
        # 检查路径安全性 / Check path security
        if not self._is_path_allowed(directory_path):
            return f"不允许访问该路径 / Access to this path is not allowed: {directory_path}"
        
        if not os.path.exists(directory_path):
            return f"目录不存在 / Directory not found: {directory_path}"
        
        if not os.path.isdir(directory_path):
            return f"路径不是目录 / Path is not a directory: {directory_path}"
        
        try:
            items = []
            
            if recursive:
                for root, dirs, files in os.walk(directory_path):
                    rel_root = os.path.relpath(root, directory_path)
                    if rel_root == ".":
                        rel_root = ""
                    
                    for d in sorted(dirs):
                        path = os.path.join(rel_root, d) if rel_root else d
                        items.append(f"[DIR]  {path}/")
                    
                    for f in sorted(files):
                        path = os.path.join(rel_root, f) if rel_root else f
                        file_path = os.path.join(root, f)
                        try:
                            size = os.path.getsize(file_path)
                            items.append(f"[FILE] {path} ({size} bytes)")
                        except OSError:
                            items.append(f"[FILE] {path}")
            else:
                for item in sorted(os.listdir(directory_path)):
                    item_path = os.path.join(directory_path, item)
                    if os.path.isdir(item_path):
                        items.append(f"[DIR]  {item}/")
                    else:
                        try:
                            size = os.path.getsize(item_path)
                            items.append(f"[FILE] {item} ({size} bytes)")
                        except OSError:
                            items.append(f"[FILE] {item}")
            
            if not items:
                return f"目录为空 / Directory is empty: {directory_path}"
            
            header = f"目录内容 / Directory content: {directory_path}\n"
            header += f"共 {len(items)} 项 / Total {len(items)} items\n"
            header += "-" * 50 + "\n"
            
            return header + "\n".join(items)
            
        except PermissionError as e:
            return f"权限不足 / Permission denied: {str(e)}"
        except Exception as e:
            return f"列出目录错误 / Error listing directory: {str(e)}"
