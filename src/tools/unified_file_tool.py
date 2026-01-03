import os
import shutil
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field

from src.core.config import get_config
from src.tools.base import BaseTool, ToolInput


class FileInput(ToolInput):
    """文件操作输入"""
    operation: Literal["read", "write", "list"] = Field(
        description="操作类型：read（读取）、write（写入）、list（列目录）"
    )
    path: str = Field(description="文件或目录路径")
    content: Optional[str] = Field(default=None, description="写入内容（仅write操作需要）")
    encoding: str = Field(default="utf-8", description="文件编码")
    append: bool = Field(default=False, description="是否追加模式（仅write操作）")
    recursive: bool = Field(default=False, description="是否递归列出（仅list操作）")
    backup: bool = Field(default=False, description="写入前是否备份原文件（仅write操作）")
    create_dirs: bool = Field(default=True, description="是否自动创建父目录（仅write操作）")


class FileTool(BaseTool):
    """
    统一文件操作工具。

    提供文件读取、写入、目录列表功能，支持自动创建目录、备份与追加写入。
    """
    
    name: str = "file"
    subprocess_safe: bool = True
    required_permissions = ["files"]
    
    description: str = """文件操作工具，支持读取、写入、列目录。

## 使用说明

- **operation**（必填）：read/write/list
- **path**（必填）：文件或目录路径
- **content**（write操作必填）：写入内容
- **encoding**（可选）：文件编码，默认utf-8
- **append**（可选）：是否追加，默认false
- **recursive**（可选）：是否递归列出，默认false
- **backup**（可选）：写入前备份，默认false
- **create_dirs**（可选）：自动创建父目录，默认true
"""

    description_zh: str = description
    
    input_schema = FileInput
    
    def __init__(self, allowed_directories: Optional[List[str]] = None):
        """
        初始化

        Args:
            allowed_directories: 允许访问的目录列表
        """
        super().__init__()
        config = get_config()
        self.allowed_directories = allowed_directories or config.tools.file_tool.allowed_directories
    
    def _is_path_allowed(self, file_path: str) -> bool:
        """
        检查路径是否在允许范围内

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否允许访问
        """
        abs_path = os.path.normpath(os.path.abspath(file_path))
        for allowed_dir in self.allowed_directories:
            allowed_abs = os.path.normpath(os.path.abspath(allowed_dir))
            # 规范化路径以兼容不同系统
            if abs_path.startswith(allowed_abs):
                # 确保匹配的是完整的目录，不是前缀重叠
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
        执行文件操作

        Args:
            operation: 操作类型
            path: 文件或目录路径
            content: 写入内容
            encoding: 文件编码
            append: 是否追加模式
            recursive: 是否递归列出
            backup: 是否备份
            create_dirs: 是否创建父目录

        Returns:
            str: 操作结果
        """
        operation = operation.lower().strip()
        
        if operation == "read":
            return self._read_file(path, encoding)
        elif operation == "write":
            return self._write_file(path, content, encoding, append, backup, create_dirs)
        elif operation == "list":
            return self._list_directory(path, recursive)
        else:
            return f"未知操作类型: {operation}。支持的操作: read, write, list"
    
    def _read_file(self, file_path: str, encoding: str = "utf-8") -> str:
        """
        读取文件

        Args:
            file_path: 文件路径
            encoding: 文件编码

        Returns:
            str: 文件内容
        """
        # 检查路径安全性
        if not self._is_path_allowed(file_path):
            return f"不允许访问该路径: {file_path}"
        
        if not os.path.exists(file_path):
            return f"文件不存在: {file_path}"
        
        if os.path.isdir(file_path):
            return f"路径是目录，请使用 list 操作: {file_path}"
        
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            
            file_size = os.path.getsize(file_path)
            return f"文件内容（{file_size} 字节）:\n\n{content}"
        except UnicodeDecodeError as e:
            return f"文件编码错误: {str(e)}。请尝试其他编码"
        except Exception as e:
            return f"读取文件错误: {str(e)}"
    
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
        写入文件

        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 文件编码
            append: 是否追加模式
            backup: 是否备份
            create_dirs: 是否创建父目录

        Returns:
            str: 操作结果
        """
        # 检查路径安全性
        if not self._is_path_allowed(file_path):
            return f"不允许访问该路径: {file_path}"
        
        if content is None:
            return "写入内容不能为空"

        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".pdf", ".doc", ".docx"):
            return (
                "不支持直接写入 .pdf/.doc/.docx（文本写入会导致乱码或文件损坏）。"
                "请使用Python工具生成：PDF用reportlab并注册中文字体，"
                "Word用python-docx。"
            )
        
        try:
            abs_path = os.path.abspath(file_path)
            parent_dir = os.path.dirname(abs_path)
            
            # 创建父目录
            if create_dirs and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                self.logger.info(f"创建目录: {parent_dir}")
            
            # 备份原文件
            backup_path = None
            if backup and os.path.exists(abs_path):
                backup_path = f"{abs_path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(abs_path, backup_path)
                self.logger.info(f"已备份到: {backup_path}")
            
            # 写入文件
            mode = "a" if append else "w"
            with open(abs_path, mode, encoding=encoding) as f:
                f.write(content)
            
            # 获取文件信息
            file_size = os.path.getsize(abs_path)
            mode_text = "追加" if append else "写入"
            
            result = f"文件{mode_text}成功: {file_path}\n"
            result += f"文件大小: {file_size} 字节\n"
            result += f"内容长度: {len(content)} 字符"
            
            if backup_path:
                result += f"\n备份文件: {backup_path}"
            
            return result
            
        except PermissionError as e:
            return f"权限不足: {str(e)}"
        except Exception as e:
            return f"写入文件错误: {str(e)}"
    
    def _list_directory(self, directory_path: str, recursive: bool = False) -> str:
        """
        列出目录

        Args:
            directory_path: 目录路径
            recursive: 是否递归列出

        Returns:
            str: 目录内容
        """
        # 检查路径安全性
        if not self._is_path_allowed(directory_path):
            return f"不允许访问该路径: {directory_path}"
        
        if not os.path.exists(directory_path):
            return f"目录不存在: {directory_path}"
        
        if not os.path.isdir(directory_path):
            return f"路径不是目录: {directory_path}"
        
        try:
            items = []
            
            if recursive:
                for root, dirs, files in os.walk(directory_path):
                    rel_root = os.path.relpath(root, directory_path)
                    if rel_root == ".":
                        rel_root = ""
                    
                    for d in sorted(dirs):
                        path = os.path.join(rel_root, d) if rel_root else d
                        items.append(f"[目录]  {path}/")
                    
                    for f in sorted(files):
                        path = os.path.join(rel_root, f) if rel_root else f
                        file_path = os.path.join(root, f)
                        try:
                            size = os.path.getsize(file_path)
                            items.append(f"[文件] {path} ({size} 字节)")
                        except OSError:
                            items.append(f"[文件] {path}")
            else:
                for item in sorted(os.listdir(directory_path)):
                    item_path = os.path.join(directory_path, item)
                    if os.path.isdir(item_path):
                        items.append(f"[目录]  {item}/")
                    else:
                        try:
                            size = os.path.getsize(item_path)
                            items.append(f"[文件] {item} ({size} 字节)")
                        except OSError:
                            items.append(f"[文件] {item}")
            
            if not items:
                return f"目录为空: {directory_path}"
            
            header = f"目录内容: {directory_path}\n"
            header += f"共 {len(items)} 项\n"
            header += "-" * 50 + "\n"
            
            return header + "\n".join(items)
            
        except PermissionError as e:
            return f"权限不足: {str(e)}"
        except Exception as e:
            return f"列出目录错误: {str(e)}"
