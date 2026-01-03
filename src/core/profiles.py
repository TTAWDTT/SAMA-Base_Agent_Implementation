# ==============================================================================
# 角色模板管理
# ==============================================================================

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.core.config import Config, ProfileConfig, find_project_root
from src.core.memory import ConversationMemory
from src.core.logger import get_logger
from src.core.prompts import get_system_prompt, get_tools_description
from src.tools import ALL_TOOLS

logger = get_logger("profiles")


def list_profiles(config: Config) -> List[ProfileConfig]:
    return list(config.profiles or [])


def resolve_profile(config: Config, name: str) -> Optional[ProfileConfig]:
    if not name:
        return None
    for profile in list_profiles(config):
        if profile.name == name:
            return profile
    return None


def load_profile_prompt(profile: ProfileConfig, project_root: Optional[Path] = None) -> Optional[str]:
    if profile.system_prompt:
        return profile.system_prompt
    if not profile.system_prompt_path:
        return None
    root = project_root or find_project_root()
    prompt_path = Path(profile.system_prompt_path)
    if not prompt_path.is_absolute():
        prompt_path = root / prompt_path
    try:
        return prompt_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning(f"读取系统提示词失败: {exc}")
        return None


def apply_profile_to_agent(agent: Any, profile: ProfileConfig) -> None:
    """
    将模板应用到Agent
    """
    if profile.config_overrides:
        agent.config = Config(**_merge_dict(_config_to_dict(agent.config), profile.config_overrides))
        _apply_memory_settings(agent, agent.config)
        if hasattr(agent, "_init_workspace"):
            agent._init_workspace()
    _apply_tool_filter(agent, profile.tools_include, profile.tools_exclude)
    _apply_system_prompt(agent, profile)
    agent.profile_name = profile.name


def _apply_tool_filter(agent: Any, include: List[str], exclude: List[str]) -> None:
    pool = _build_tool_pool(agent)
    if include:
        names = [name for name in include if name in pool]
    else:
        names = list(pool.keys())
    if exclude:
        names = [name for name in names if name not in set(exclude)]

    new_tools = {}
    for name in names:
        tool_cls = pool[name]
        try:
            new_tools[name] = tool_cls()
        except Exception as exc:
            logger.warning(f"工具实例化失败: {name}: {exc}")
    agent.tools = new_tools


def _build_tool_pool(agent: Any) -> Dict[str, Any]:
    pool: Dict[str, Any] = {}
    for tool_cls in ALL_TOOLS:
        try:
            name = tool_cls().name
        except Exception:
            continue
        pool[name] = tool_cls

    for tool in getattr(agent, "tools", {}).values():
        if tool.name not in pool:
            pool[tool.name] = tool.__class__
    return pool


def _apply_memory_settings(agent: Any, config: Config) -> None:
    memory = getattr(agent, "memory", None)
    if not isinstance(memory, ConversationMemory):
        return
    memory.max_entries = config.memory.max_entries
    memory.max_context_tokens = config.memory.max_context_tokens
    memory.memory_type = config.memory.type
    memory.summary_keep_last_n = config.memory.summary_keep_last_n
    memory.summary_max_chars = config.memory.summary_max_chars
    memory.system_token_ratio = config.memory.system_token_ratio
    memory.file_context_token_ratio = config.memory.file_context_token_ratio
    memory.history_token_ratio = config.memory.history_token_ratio
    memory.file_context_chunk_size = config.memory.file_context_chunk_size
    memory.file_context_max_chunks_per_file = config.memory.file_context_max_chunks_per_file
    memory.file_context_min_score = config.memory.file_context_min_score
    memory.file_context_query_messages = config.memory.file_context_query_messages
    memory.history_retrieval_enabled = config.memory.history_retrieval_enabled
    memory.history_retrieval_token_ratio = config.memory.history_retrieval_token_ratio
    memory.history_retrieval_max_messages = config.memory.history_retrieval_max_messages
    memory.history_retrieval_min_score = config.memory.history_retrieval_min_score
    memory.history_retrieval_query_messages = config.memory.history_retrieval_query_messages
    memory.history_retrieval_include_roles = config.memory.history_retrieval_include_roles


def _apply_system_prompt(agent: Any, profile: ProfileConfig) -> None:
    tools = list(getattr(agent, "tools", {}).values())
    tools_description = get_tools_description(tools)

    prompt = load_profile_prompt(profile)
    if prompt:
        if "{tools_description}" in prompt:
            prompt = prompt.format(tools_description=tools_description)
        elif profile.append_tools_description:
            prompt = prompt + "\n\n" + tools_description
    else:
        prompt = get_system_prompt(tools)

    agent.base_system_prompt = prompt
    agent._refresh_system_message()


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _config_to_dict(config: Config) -> Dict[str, Any]:
    if hasattr(config, "model_dump"):
        return config.model_dump()
    return config.dict()


def load_profiles_from_dir(path: Path) -> List[ProfileConfig]:
    """
    从目录读取模板配置
    """
    if not path.exists() or not path.is_dir():
        return []

    profiles: List[ProfileConfig] = []
    for file_path in sorted(path.glob("*.yaml")):
        data = _read_yaml(file_path)
        if not data:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    profiles.append(_build_profile(item, file_path))
            continue
        if isinstance(data, dict):
            if "profiles" in data and isinstance(data["profiles"], list):
                for item in data["profiles"]:
                    if isinstance(item, dict):
                        profiles.append(_build_profile(item, file_path))
            else:
                profiles.append(_build_profile(data, file_path))
    return profiles


def _build_profile(raw: Dict[str, Any], file_path: Path) -> ProfileConfig:
    data = dict(raw)
    if not data.get("name"):
        data["name"] = file_path.stem
    return ProfileConfig(**data)


def _read_yaml(path: Path) -> Dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
