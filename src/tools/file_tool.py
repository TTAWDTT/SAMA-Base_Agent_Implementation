# ==============================================================================
# 文件操作工具 / File Operation Tool
# ==============================================================================
# 提供文件读写、目录操作等功能
# Provides file read/write, directory operations, etc.
# ==============================================================================

import os
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from src.core.config import get_config
from src.tools.base import BaseTool, ToolInput


class ReadFileInput(ToolInput):
    """读取文件输入 / Read File Input"""
    file_path: str = Field(description="文件路径 / File path")
    encoding: str = Field(default="utf-8", description="文件编码 / File encoding")


class WriteFileInput(ToolInput):
    """写入文件输入 / Write File Input"""
    file_path: str = Field(description="文件路径 / File path")
    content: str = Field(description="文件内容 / File content")
    encoding: str = Field(default="utf-8", description="文件编码 / File encoding")
    append: bool = Field(default=False, description="是否追加模式 / Append mode")


class ListDirectoryInput(ToolInput):
    """列出目录输入 / List Directory Input"""
    directory_path: str = Field(description="目录路径 / Directory path")
    recursive: bool = Field(default=False, description="是否递归列出 / Recursive listing")


class ReadFileTool(BaseTool):
    """
    读取文件工具 / Read File Tool
    
    读取指定文件的内容
    Reads content of specified file
    """
    
    name: str = "read_file"
    description: str = "读取文件内容。参数：file_path（文件路径）/ Read file content. Parameters: file_path (file path)"
    description_zh: str = "读取文件内容。参数：file_path（文件路径）"
    description_en: str = "Read file content. Parameters: file_path (file path)"
    input_schema = ReadFileInput
    
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
    
    def _run(self, file_path: str, encoding: str = "utf-8") -> str:
        """
        执行文件读取 / Execute file read
        
        Args:
            file_path: 文件路径 / File path
            encoding: 文件编码 / File encoding
            
        Returns:
            str: 文件内容 / File content
        """
        # 检查路径安全性 / Check path security
        if not self._is_path_allowed(file_path):
            raise PermissionError(f"不允许访问该路径 / Access to this path is not allowed: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在 / File not found: {file_path}")
        
        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()
        
        return content


class WriteFileTool(BaseTool):
    """
    写入文件工具 / Write File Tool
    
    将内容写入指定文件
    Writes content to specified file
    """
    
    name: str = "write_file"
    description: str = "写入内容到文件。参数：file_path（文件路径），content（内容）/ Write content to file. Parameters: file_path (file path), content (content)"
    description_zh: str = "写入内容到文件。参数：file_path（文件路径），content（内容）"
    description_en: str = "Write content to file. Parameters: file_path (file path), content (content)"
    input_schema = WriteFileInput
    
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
        """检查路径是否在允许范围内 / Check if path is within allowed range"""
        abs_path = os.path.normpath(os.path.abspath(file_path))
        for allowed_dir in self.allowed_directories:
            allowed_abs = os.path.normpath(os.path.abspath(allowed_dir))
            if abs_path.startswith(allowed_abs):
                if len(abs_path) == len(allowed_abs) or abs_path[len(allowed_abs)] in (os.sep, os.altsep or ''):
                    return True
        return False
    
    def _run(self, file_path: str, content: str, encoding: str = "utf-8", append: bool = False) -> str:
        """
        执行文件写入 / Execute file write
        
        Args:
            file_path: 文件路径 / File path
            content: 文件内容 / File content
            encoding: 文件编码 / File encoding
            append: 是否追加模式 / Append mode
            
        Returns:
            str: 操作结果 / Operation result
        """
        # 检查路径安全性 / Check path security
        if not self._is_path_allowed(file_path):
            raise PermissionError(f"不允许访问该路径 / Access to this path is not allowed: {file_path}")
        
        # 确保目录存在 / Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        mode = "a" if append else "w"
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)
        
        return f"文件写入成功 / File written successfully: {file_path}"


class ListDirectoryTool(BaseTool):
    """
    列出目录工具 / List Directory Tool
    
    列出指定目录下的文件和子目录
    Lists files and subdirectories in specified directory
    """
    
    name: str = "list_directory"
    description: str = "列出目录内容。参数：directory_path（目录路径）/ List directory content. Parameters: directory_path (directory path)"
    description_zh: str = "列出目录内容。参数：directory_path（目录路径）"
    description_en: str = "List directory content. Parameters: directory_path (directory path)"
    input_schema = ListDirectoryInput
    
    def __init__(self, allowed_directories: Optional[List[str]] = None):
        """初始化 / Initialize"""
        super().__init__()
        config = get_config()
        self.allowed_directories = allowed_directories or config.tools.file_tool.allowed_directories
    
    def _is_path_allowed(self, dir_path: str) -> bool:
        """检查路径是否在允许范围内 / Check if path is within allowed range"""
        abs_path = os.path.normpath(os.path.abspath(dir_path))
        for allowed_dir in self.allowed_directories:
            allowed_abs = os.path.normpath(os.path.abspath(allowed_dir))
            if abs_path.startswith(allowed_abs):
                if len(abs_path) == len(allowed_abs) or abs_path[len(allowed_abs)] in (os.sep, os.altsep or ''):
                    return True
        return False
    
    def _run(self, directory_path: str, recursive: bool = False) -> str:
        """
        执行目录列表 / Execute directory listing
        
        Args:
            directory_path: 目录路径 / Directory path
            recursive: 是否递归列出 / Recursive listing
            
        Returns:
            str: 目录内容列表 / Directory content list
        """
        # 检查路径安全性 / Check path security
        if not self._is_path_allowed(directory_path):
            raise PermissionError(f"不允许访问该路径 / Access to this path is not allowed: {directory_path}")
        
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"目录不存在 / Directory not found: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"路径不是目录 / Path is not a directory: {directory_path}")
        
        items = []
        
        if recursive:
            for root, dirs, files in os.walk(directory_path):
                rel_root = os.path.relpath(root, directory_path)
                for d in dirs:
                    items.append(f"[DIR]  {os.path.join(rel_root, d)}")
                for f in files:
                    items.append(f"[FILE] {os.path.join(rel_root, f)}")
        else:
            for item in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item)
                if os.path.isdir(item_path):
                    items.append(f"[DIR]  {item}")
                else:
                    items.append(f"[FILE] {item}")
        
        return "\n".join(items) if items else "目录为空 / Directory is empty"
