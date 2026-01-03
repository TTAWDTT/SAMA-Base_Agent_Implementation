# ==============================================================================
# 插件工具加载器
# ==============================================================================

from __future__ import annotations

import importlib.util
import sys
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Type

from src.core.logger import get_logger
from src.tools.base import BaseTool

logger = get_logger("tools.registry")


def load_plugin_tool_classes(paths: Iterable[str], allow_unsigned: bool = True) -> List[Type[BaseTool]]:
    """
    从插件目录加载工具类
    """
    tool_classes: List[Type[BaseTool]] = []
    seen = set()
    for file_path in discover_plugin_files(paths, allow_unsigned=allow_unsigned):
        classes = _load_tool_classes_from_file(file_path)
        for cls in classes:
            if cls in seen:
                continue
            seen.add(cls)
            tool_classes.append(cls)
    return tool_classes


def merge_tool_classes(
    base_tools: List[Type[BaseTool]],
    plugin_tools: List[Type[BaseTool]]
) -> List[Type[BaseTool]]:
    """
    合并工具列表，按工具名称去重
    """
    merged: List[Type[BaseTool]] = []
    names = set()
    for tool_cls in base_tools + plugin_tools:
        try:
            name = getattr(tool_cls, "name", "")
        except Exception:
            name = ""
        if not name or name in names:
            continue
        names.add(name)
        merged.append(tool_cls)
    return merged


def discover_plugin_files(paths: Iterable[str], allow_unsigned: bool = True) -> List[Path]:
    """
    获取插件文件列表
    """
    files: List[Path] = []
    for raw in paths:
        if not raw:
            continue
        path = Path(raw).expanduser()
        if not path.exists():
            continue
        if path.is_file() and path.suffix == ".py":
            if _is_signed(path) or allow_unsigned:
                files.append(path)
            continue
        if path.is_dir():
            for file_path in sorted(path.glob("*.py")):
                if file_path.name.startswith("_"):
                    continue
                if _is_signed(file_path) or allow_unsigned:
                    files.append(file_path)
    return files


def build_plugin_catalog(
    plugin_paths: Iterable[str],
    catalog_files: Optional[Iterable[str]] = None,
    allow_unsigned: bool = True
) -> List[Dict[str, Any]]:
    """
    构建插件索引
    """
    catalog: List[Dict[str, Any]] = []
    seen = set()
    for file_path in discover_plugin_files(plugin_paths, allow_unsigned=allow_unsigned):
        signature = _read_signature(file_path)
        entry = {
            "name": file_path.stem,
            "path": str(file_path),
            "signed": signature is not None,
            "signature": signature,
            "updated_at": file_path.stat().st_mtime,
        }
        catalog.append(entry)
        seen.add(entry["name"])

    for raw in catalog_files or []:
        path = Path(raw).expanduser()
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            data = data.get("plugins", [])
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("id") or "")
            if not name or name in seen:
                continue
            catalog.append(item)
            seen.add(name)
    return catalog


def _read_signature(path: Path) -> Optional[str]:
    sig_path = path.with_suffix(path.suffix + ".sig")
    if not sig_path.exists():
        return None
    try:
        return sig_path.read_text(encoding="utf-8").strip()
    except Exception:
        return None


def _is_signed(path: Path) -> bool:
    """
    判断插件是否具备签名
    """
    signature = _read_signature(path)
    if not signature:
        return False
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return False
    return digest == signature


def _load_tool_classes_from_file(path: Path) -> List[Type[BaseTool]]:
    """
    加载单个文件中的工具类
    """
    module = _load_module(path)
    if not module:
        return []
    classes = []
    for obj in module.__dict__.values():
        if not isinstance(obj, type):
            continue
        if obj is BaseTool:
            continue
        if not issubclass(obj, BaseTool):
            continue
        classes.append(obj)
    return classes


def _load_module(path: Path):
    """
    动态加载模块
    """
    try:
        module_name = f"sama_plugin_{path.stem}_{abs(hash(str(path)))}"
        if module_name in sys.modules:
            return sys.modules[module_name]
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if not spec or not spec.loader:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        logger.warning(f"加载插件失败: {path}: {exc}")
        return None
