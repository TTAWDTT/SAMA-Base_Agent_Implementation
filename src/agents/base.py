# ==============================================================================
# 智能体基础实现
# ==============================================================================
# 实现基于大模型的智能体循环，通过工具完成任务
#
# 设计理念
# - 智能体是在循环中使用工具来实现目标的大模型
#
# 参考
# ==============================================================================

import json
import time
import re
import os
from datetime import datetime
import concurrent.futures
import importlib
import multiprocessing
import queue as queue_module
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from openai import OpenAI
from pydantic import ValidationError

from src.core.config import get_config, Config, find_project_root
from src.core.logger import get_logger, init_logging
from src.core.memory import ConversationMemory, get_memory
from src.core.prompts import get_system_prompt
from src.core.profiles import resolve_profile, apply_profile_to_agent
from src.core.schema import (
    AgentState,
    AgentStep,
    AgentResponse,
    ToolCall,
    ToolResult,
    ToolResultStatus,
)
from src.tools import DEFAULT_TOOLS, BaseTool, load_plugin_tool_classes
from src.utils.helpers import format_tool_result, format_tool_trace, generate_request_id, is_search_result, refine_search_result

logger = get_logger("agents.base")


class AgentCancelled(Exception):
    """
    运行被取消
    """

    def __init__(self, message: str = "cancelled", partial: str = "") -> None:
        super().__init__(message)
        self.partial = partial or ""


class _StreamFunction:
    def __init__(self, name: str = "", arguments: str = "") -> None:
        self.name = name
        self.arguments = arguments


class _StreamToolCall:
    def __init__(self, call_id: str = "", function: Optional[_StreamFunction] = None) -> None:
        self.id = call_id
        self.function = function or _StreamFunction()


class _StreamMessage:
    def __init__(self, content: str = "", tool_calls: Optional[List[_StreamToolCall]] = None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []
        self.text = content


def _run_tool_in_subprocess(module_name: str, class_name: str, arguments: Dict[str, Any], result_queue) -> None:
    """
    在子进程中执行工具，返回原始输出与错误信息
    """
    try:
        module = importlib.import_module(module_name)
        tool_cls = getattr(module, class_name)
        tool = tool_cls()
        output = tool._run(**arguments)
        result_queue.put({"status": "success", "output": output})
    except Exception as e:
        result_queue.put({"status": "error", "error": str(e)})


class BaseAgent:
    """
    基础智能体类

    实现核心的工具循环逻辑：
    1. 接收用户输入
    2. 调用LLM生成决策
    3. 根据决策执行工具
    4. 将工具结果反馈给LLM
    5. 重复直到任务完成或达到最大迭代次数
    """
    
    def __init__(
        self,
        tools: Optional[List[Union[BaseTool, Type[BaseTool]]]] = None,
        config: Optional[Config] = None,
        memory: Optional[ConversationMemory] = None,
        system_prompt: Optional[str] = None,
        profile: Optional[str] = None,
    ):
        """
        初始化智能体
        
        Args:
            tools: 可用工具列表（实例或类）
            config: 配置对象
            memory: 对话记忆
            system_prompt: 自定义系统提示词
            profile: 模板名称
        """
        # 初始化日志
        init_logging()
        
        # 加载配置
        self.config = config or get_config()
        self.profile_name: Optional[str] = None
        profile_name = profile or self.config.active_profile
        profile_config = resolve_profile(self.config, profile_name) if profile_name else None
        if profile_config and profile_config.config_overrides:
            self.config = Config(**self._merge_dict(self._config_to_dict(self.config), profile_config.config_overrides))
        
        # 初始化工作区
        self._init_workspace()
        
        # 初始化工具
        self._init_tools(tools)
        
        # 初始化记忆
        self.memory = memory or get_memory()
        
        # 设置系统提示词
        prompt_override = system_prompt or self._load_prompt_override()
        if prompt_override:
            self.base_system_prompt = prompt_override
        else:
            self.base_system_prompt = get_system_prompt(
                tools=list(self.tools.values())
            )
        
        self._refresh_system_message()
        if profile_config:
            apply_profile_to_agent(self, profile_config)
        
        # 初始化模型客户端
        self._init_client()
        
        # 智能体状态
        self.state = AgentState.IDLE
        self.current_step = 0
        self.steps: List[AgentStep] = []
        self._max_tokens_warned = False
        self._ui_hooks: Dict[str, Any] = {}
        
        # 显式上下文模式
        self.verbose_context = False  # 是否显示详细上下文
        
        logger.info(f"智能体初始化完成，工具数量: {len(self.tools)}")
        logger.info(f"工作区: {self.workspace}")
    
    def _init_workspace(self) -> None:
        """
        初始化工作区目录

        创建工作区目录（如果不存在），并设置工作区路径
        """
        workspace_path = Path(self.config.agent.workspace)
        workspace_path.mkdir(parents=True, exist_ok=True)
        self.workspace = str(workspace_path.resolve())
        logger.info(f"工作区已初始化: {self.workspace}")

    def set_ui_hooks(self, hooks: Optional[Dict[str, Any]]) -> None:
        """
        设置UI回调

        Args:
            hooks: 回调字典
        """
        self._ui_hooks = hooks or {}

    def _emit_ui_event(self, event: str, **payload: Any) -> None:
        """
        触发UI事件
        """
        handler = self._ui_hooks.get(event)
        if not callable(handler):
            return
        try:
            handler(**payload)
        except Exception as exc:
            logger.debug(f"UI回调失败: {event}: {exc}")
    
    def _build_workspace_section(self) -> str:
        """
        构建工作区提示信息
        """
        workspace_section = f"""

## 工作区与文件管理

**工作区路径**: `{self.workspace}`

你可以在工作区中创建、修改和管理文件。对于重要的中间文件（如生成的脚本、数据文件、搜索结果等），请遵循：

1. **将文件保存到工作区**
2. **使用文件工具记录文件上下文**
3. **在对话中引用这些文件**
4. **及时清理不再需要的旧文件**

当前文件上下文：
{self.memory.get_files_summary()}

**上下文策略**：
- 文件内容按相关性分块注入，预算不足时优先压缩文件上下文
- 需要完整文件时，请明确要求读取或更新文件上下文

## 工作记忆

{self.memory.get_context_summary()}

**重要提示**：
- 避免重复执行相同操作
- 如果某个工具已经成功调用过，优先分析结果而不是重复调用
- 每次操作前先检查工作记忆中是否已有相关结果
"""
        return workspace_section

    def _compose_system_prompt(self) -> str:
        """
        组合完整系统提示词
        """
        return self.base_system_prompt + self._build_time_section() + self._build_workspace_section()

    def _build_time_section(self) -> str:
        """
        构建当前时间提示信息
        """
        now = datetime.now().astimezone()
        time_text = now.strftime("%Y-%m-%d %H:%M:%S")
        tz_name = now.tzname() or "local"
        offset = now.utcoffset()
        if offset is None:
            offset_text = ""
        else:
            total_minutes = int(offset.total_seconds() // 60)
            sign = "+" if total_minutes >= 0 else "-"
            total_minutes = abs(total_minutes)
            offset_text = f" (UTC{sign}{total_minutes // 60:02d}:{total_minutes % 60:02d})"
        return f"""

## 当前时间（极重要）
当前时间: {time_text}
时区: {tz_name}{offset_text}

**要求**: 在所有回复中必须将当前时间视为极其重要的上下文因素，尤其涉及计划、截止、时效或新闻相关问题。
"""

    def _refresh_system_message(self) -> None:
        """
        刷新系统消息内容
        """
        self.system_prompt = self._compose_system_prompt()
        self.memory.set_system_message(self.system_prompt)

    def _load_prompt_override(self) -> Optional[str]:
        """
        读取配置中的系统提示词覆盖
        """
        config_prompt = getattr(self.config.agent, "system_prompt", None)
        if config_prompt:
            return config_prompt
        prompt_path = getattr(self.config.agent, "system_prompt_path", None)
        if not prompt_path:
            return None
        base_path = Path(prompt_path)
        if not base_path.is_absolute():
            base_path = find_project_root() / base_path
        try:
            return base_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning(f"读取系统提示词失败: {exc}")
            return None

    @staticmethod
    def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并配置
        """
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = BaseAgent._merge_dict(merged[key], value)
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _config_to_dict(config: Config) -> Dict[str, Any]:
        if hasattr(config, "model_dump"):
            return config.model_dump()
        return config.dict()
    
    def _extract_thinking(self, content: str) -> Optional[str]:
        """
        从内容中提取 <thinking> 标签内的文本

        Args:
            content: 消息内容

        Returns:
            Optional[str]: 思考内容，如果没有则返回 None
        """
        pattern = r'<thinking>(.*?)</thinking>'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        return None

    def _strip_thinking_tags(self, content: str) -> str:
        """
        移除 <thinking> 标签内容
        """
        if not content:
            return ""
        cleaned = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()
    
    def _init_tools(self, tools: Optional[List[Union[BaseTool, Type[BaseTool]]]] = None) -> None:
        """
        初始化工具

        Args:
            tools: 工具列表
        """
        self.tools: Dict[str, BaseTool] = {}
        
        # 使用默认工具或自定义工具
        tool_list = list(tools or DEFAULT_TOOLS)
        plugin_config = getattr(self.config, "plugins", None)
        if plugin_config and getattr(plugin_config, "enabled", False):
            plugin_paths = getattr(plugin_config, "tool_paths", []) or []
            allow_unsigned = getattr(plugin_config, "allow_unsigned", True)
            plugin_tools = load_plugin_tool_classes(plugin_paths, allow_unsigned=allow_unsigned)
            tool_list.extend(plugin_tools)

        allowed_tools = set(getattr(self.config.tools, "allowed_tools", []) or [])
        blocked_tools = set(getattr(self.config.tools, "blocked_tools", []) or [])
        allowed_permissions = set(getattr(self.config.tools, "allowed_permissions", []) or [])
        plugin_permissions = set(getattr(plugin_config, "allowed_permissions", []) or []) if plugin_config else set()
        if plugin_permissions:
            allowed_permissions.update(plugin_permissions)
        
        for tool in tool_list:
            # 如果是类，实例化它
            if isinstance(tool, type):
                tool_instance = tool()
            else:
                tool_instance = tool

            if tool_instance.name in self.tools:
                logger.warning(f"重复工具已忽略: {tool_instance.name}")
                continue
            if allowed_tools and tool_instance.name not in allowed_tools:
                logger.warning(f"工具未在白名单内: {tool_instance.name}")
                continue
            if tool_instance.name in blocked_tools:
                logger.warning(f"工具已被禁用: {tool_instance.name}")
                continue
            required = getattr(tool_instance, "required_permissions", []) or []
            if required and allowed_permissions:
                if not set(required).issubset(allowed_permissions):
                    logger.warning(f"工具权限不满足: {tool_instance.name}")
                    continue
            self.tools[tool_instance.name] = tool_instance
            logger.debug(f"注册工具: {tool_instance.name}")
    
    def _init_client(self) -> None:
        """
        初始化OpenAI客户端

        使用OpenAI兼容接口连接模型
        """
        self.client = OpenAI(
            api_key=self.config.model.api_key,
            base_url=self.config.model.base_url,
            timeout=self.config.model.timeout
        )
        
        logger.info(f"LLM客户端初始化: {self.config.model.base_url}")
    
    def _get_tools_for_api(self) -> List[Dict[str, Any]]:
        """
        获取API格式的工具定义

        符合Kimi API要求的工具定义格式

        Returns:
            List[Dict]: OpenAI函数调用格式的工具定义
        """
        return [tool.get_schema() for tool in self.tools.values()]
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        调用LLM
        """
        max_retries = getattr(self.config.model, "max_retries", 2)
        backoff_base = getattr(self.config.model, "retry_backoff_base", 1.5)
        backoff_max = getattr(self.config.model, "retry_backoff_max", 8.0)
        last_error = None
        max_tokens = self.config.model.effective_max_tokens
        if max_tokens != self.config.model.max_tokens and not self._max_tokens_warned:
            logger.warning(
                f"max_tokens 已裁剪: {self.config.model.max_tokens} -> {max_tokens}"
            )
            self._max_tokens_warned = True

        for attempt in range(max_retries + 1):
            try:
                return self.client.chat.completions.create(
                    model=self.config.model.effective_model_name,
                    messages=messages,
                    tools=self._get_tools_for_api() if self.tools else None,
                    temperature=self.config.model.temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                last_error = e
                if attempt >= max_retries or not self._should_retry(e):
                    logger.error(f"LLM调用失败: {str(e)}")
                    raise
                delay = min(backoff_base * (2 ** attempt), backoff_max)
                logger.warning(f"LLM调用失败，准备重试: {str(e)}")
                time.sleep(delay)

        logger.error(f"LLM调用失败: {str(last_error)}")
        raise last_error

    def _chunk_text(self, text: str, size: int = 80) -> List[str]:
        if not text:
            return []
        if size <= 0:
            return [text]
        return [text[i:i + size] for i in range(0, len(text), size)]

    def _call_llm_stream(
        self,
        messages: List[Dict[str, str]],
        cancel_event: Optional[threading.Event] = None
    ) -> Tuple[Any, int]:
        """
        流式调用LLM，返回消息与token统计
        """
        content_parts: List[str] = []
        tool_calls: Dict[int, Dict[str, Any]] = {}
        usage_total = 0

        try:
            stream = self.client.chat.completions.create(
                model=self.config.model.effective_model_name,
                messages=messages,
                tools=self._get_tools_for_api() if self.tools else None,
                temperature=self.config.model.temperature,
                max_tokens=self.config.model.effective_max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                if cancel_event and cancel_event.is_set():
                    raise AgentCancelled(partial="".join(content_parts))
                if not chunk or not getattr(chunk, "choices", None):
                    continue
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None)
                if delta:
                    text = getattr(delta, "content", None)
                    if text:
                        content_parts.append(text)
                        self._emit_ui_event("delta", text=text)
                    delta_calls = getattr(delta, "tool_calls", None)
                    if delta_calls:
                        for call in delta_calls:
                            idx = getattr(call, "index", 0)
                            bucket = tool_calls.setdefault(idx, {"id": "", "function": {"name": "", "arguments": ""}})
                            call_id = getattr(call, "id", None)
                            if call_id:
                                bucket["id"] = call_id
                            func = getattr(call, "function", None)
                            if func:
                                name = getattr(func, "name", None)
                                if name:
                                    bucket["function"]["name"] += name
                                args = getattr(func, "arguments", None)
                                if args:
                                    bucket["function"]["arguments"] += args
                usage = getattr(chunk, "usage", None)
                if usage is not None:
                    total_tokens = getattr(usage, "total_tokens", None)
                    if total_tokens is None and isinstance(usage, dict):
                        total_tokens = usage.get("total_tokens")
                    if total_tokens is not None:
                        try:
                            usage_total = int(total_tokens)
                        except (TypeError, ValueError):
                            usage_total = 0
        except AgentCancelled:
            raise
        except Exception as exc:
            logger.warning(f"流式调用失败，回退非流式: {exc}")
            response = self._call_llm(messages)
            message = response.choices[0].message
            usage_total = self._extract_token_usage(response)
            content = getattr(message, "content", None) or ""
            for chunk in self._chunk_text(content, 80):
                self._emit_ui_event("delta", text=chunk)
            return message, usage_total

        content = "".join(content_parts)
        tool_list: List[_StreamToolCall] = []
        if tool_calls:
            for idx in sorted(tool_calls.keys()):
                item = tool_calls[idx]
                func_data = item.get("function") or {}
                func = _StreamFunction(
                    name=str(func_data.get("name") or ""),
                    arguments=str(func_data.get("arguments") or "")
                )
                tool_list.append(_StreamToolCall(call_id=str(item.get("id") or ""), function=func))
        return _StreamMessage(content=content, tool_calls=tool_list), usage_total

    def _should_retry(self, error: Exception) -> bool:
        """
        判断是否需要重试
        """
        status_code = getattr(error, "status_code", None)
        if status_code in {429, 500, 502, 503, 504}:
            return True
        if isinstance(error, TimeoutError):
            return True
        message = str(error).lower()
        if "timeout" in message or "rate limit" in message or "temporarily" in message:
            return True
        return False

    def _extract_token_usage(self, response: Any) -> int:
        """
        提取响应中的token使用量
        """
        usage = getattr(response, "usage", None)
        if not usage:
            return 0

        total_tokens = getattr(usage, "total_tokens", None)
        if total_tokens is None and isinstance(usage, dict):
            total_tokens = usage.get("total_tokens")

        if total_tokens is None:
            return 0

        try:
            return int(total_tokens)
        except (TypeError, ValueError):
            return 0
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        执行工具（带超时保护）
        """
        if tool_name not in self.tools:
            return ToolResult(
                tool_name=tool_name,
                status=ToolResultStatus.ERROR,
                output=None,
                error_message=f"未知工具: {tool_name}"
            )
        
        tool = self.tools[tool_name]
        logger.info(f"执行工具: {tool_name}")
        logger.debug(f"参数: {arguments}")
        
        # 使用线程池为工具执行设置超时，避免阻塞主循环
        tool_timeout = getattr(tool, "default_timeout", None)
        if tool_timeout is None:
            tool_timeout = getattr(self.config.tools.code_executor, "timeout", 30)

        if tool.should_run_in_subprocess(arguments):
            return self._execute_tool_in_subprocess(tool, arguments, tool_timeout)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(tool.run, **arguments)
            try:
                result = future.result(timeout=tool_timeout)
            except concurrent.futures.TimeoutError:
                logger.error(f"工具执行超时: {tool_name} 超过 {tool_timeout}s")
                future.cancel()
                return ToolResult(
                    tool_name=tool_name,
                    status=ToolResultStatus.TIMEOUT,
                    output=None,
                    error_message=f"工具执行超时，超过 {tool_timeout}s",
                    execution_time=tool_timeout
                )
            except Exception as e:
                logger.error(f"工具执行失败: {str(e)}")
                return ToolResult(
                    tool_name=tool_name,
                    status=ToolResultStatus.ERROR,
                    output=None,
                    error_message=str(e),
                    execution_time=0.0
                )
        
        logger.info(f"工具执行完成: {tool_name}, 状态: {getattr(result, 'status', 'unknown')}")
        
        return result

    def _execute_tool_in_subprocess(
        self,
        tool: BaseTool,
        arguments: Dict[str, Any],
        timeout: int
    ) -> ToolResult:
        """
        使用子进程执行工具，超时可强制终止
        """
        start_time = time.time()
        module_name = tool.__class__.__module__
        class_name = tool.__class__.__name__
        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()
        process = ctx.Process(
            target=_run_tool_in_subprocess,
            args=(module_name, class_name, arguments, result_queue)
        )
        process.start()
        process.join(timeout)

        if process.is_alive():
            process.terminate()
            process.join(1)
            logger.error(f"工具执行超时: {tool.name} 超过 {timeout}s")
            return ToolResult(
                tool_name=tool.name,
                status=ToolResultStatus.TIMEOUT,
                output=None,
                error_message=f"工具执行超时，超过 {timeout}s",
                execution_time=timeout
            )

        try:
            payload = result_queue.get_nowait()
        except queue_module.Empty:
            logger.error(f"工具子进程未返回结果: {tool.name}")
            return ToolResult(
                tool_name=tool.name,
                status=ToolResultStatus.ERROR,
                output=None,
                error_message="工具子进程未返回结果",
                execution_time=time.time() - start_time
            )

        if payload.get("status") == "success":
            return ToolResult(
                tool_name=tool.name,
                status=ToolResultStatus.SUCCESS,
                output=payload.get("output"),
                execution_time=time.time() - start_time
            )

        error_message = payload.get("error") or "未知错误"
        logger.error(f"工具执行失败: {error_message}")
        return ToolResult(
            tool_name=tool.name,
            status=ToolResultStatus.ERROR,
            output=None,
            error_message=error_message,
            execution_time=time.time() - start_time
        )

    def _validate_tool_arguments(
        self,
        tool: BaseTool,
        arguments: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        校验工具参数
        """
        if not tool.input_schema:
            return arguments, None
        if not isinstance(arguments, dict):
            return {}, "工具参数必须为对象"
        try:
            model = tool.input_schema(**arguments)
        except ValidationError as exc:
            return arguments, f"工具参数校验失败: {exc}"
        if hasattr(model, "model_dump"):
            return model.model_dump(), None
        return model.dict(), None
    
    def _process_tool_calls(
        self,
        tool_calls: List[Any],
        cancel_event: Optional[threading.Event] = None
    ) -> List[ToolResult]:
        """
        处理工具调用

        Args:
            tool_calls: 工具调用列表

        Returns:
            List[ToolResult]: 工具执行结果列表
        """
        if cancel_event and cancel_event.is_set():
            raise AgentCancelled()

        results: List[Optional[ToolResult]] = [None] * len(tool_calls)
        self._tool_call_ids = {}
        self._tool_call_args = {}
        parallel_entries = []
        serial_entries = []

        def _record_result(
            index: int,
            call_record: ToolCall,
            result: ToolResult,
            arguments: Dict[str, Any],
            call_id: str
        ) -> None:
            results[index] = result
            if self.steps:
                self.steps[-1].tool_calls.append(call_record)
                self.steps[-1].tool_results.append(result)
            self._emit_ui_event(
                "tool_end",
                tool_name=call_record.tool_name,
                arguments=arguments,
                result=result,
                call_id=call_id
            )

        for i, tool_call in enumerate(tool_calls):
            if cancel_event and cancel_event.is_set():
                raise AgentCancelled()
            tool_name = tool_call.function.name
            parse_error = None

            # 解析参数
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError as exc:
                arguments = {}
                parse_error = f"JSON 解析失败: {exc}"

            if not isinstance(arguments, dict):
                arguments = {}
                parse_error = parse_error or "工具参数必须为对象"

            # 获取工具调用标识（使用模型返回的）
            call_id = getattr(tool_call, "id", None) or f"call_{tool_name}_{i}"
            self._tool_call_ids[i] = call_id
            self._tool_call_args[i] = arguments

            call_record = ToolCall(
                tool_name=tool_name,
                arguments=arguments,
                call_id=call_id
            )

            tool = self.tools.get(tool_name)
            if tool is None:
                self._emit_ui_event("tool_start", tool_name=tool_name, arguments=arguments, call_id=call_id)
                result = ToolResult(
                    tool_name=tool_name,
                    status=ToolResultStatus.ERROR,
                    output=None,
                    error_message=f"未知工具: {tool_name}"
                )
                _record_result(i, call_record, result, arguments, call_id)
                continue

            if parse_error:
                self._emit_ui_event("tool_start", tool_name=tool_name, arguments=arguments, call_id=call_id)
                result = ToolResult(
                    tool_name=tool_name,
                    status=ToolResultStatus.ERROR,
                    output=None,
                    error_message=f"工具参数解析失败: {parse_error}"
                )
                _record_result(i, call_record, result, arguments, call_id)
                continue

            arguments, validation_error = self._validate_tool_arguments(tool, arguments)
            if validation_error:
                self._emit_ui_event("tool_start", tool_name=tool_name, arguments=arguments, call_id=call_id)
                result = ToolResult(
                    tool_name=tool_name,
                    status=ToolResultStatus.ERROR,
                    output=None,
                    error_message=validation_error
                )
                _record_result(i, call_record, result, arguments, call_id)
                continue

            call_record.arguments = arguments
            self._tool_call_args[i] = arguments

            # 如果是文件相关工具，进行额外检查：读取时确保目标文件已记录或路径存在
            if tool_name in ("file", "read_file", "write_file"):
                operation = str(arguments.get("operation", "")).lower()
                if tool_name == "read_file":
                    operation = "read"
                elif tool_name == "write_file":
                    operation = "write"

                if operation == "read":
                    file_path = arguments.get("file_path") or arguments.get("path") or arguments.get("file")
                    if file_path:
                        known_paths = [f.path for f in self.memory.list_files()]
                        if file_path not in known_paths and not os.path.exists(file_path):
                            logger.warning(f"文件工具调用使用了未知路径或不存在的文件，跳过: {file_path}")
                            self._emit_ui_event("tool_start", tool_name=tool_name, arguments=arguments, call_id=call_id)
                            result = ToolResult(
                                tool_name=tool_name,
                                status=ToolResultStatus.ERROR,
                                output=None,
                                error_message=f"未知或缺失的文件: {file_path}"
                            )
                            _record_result(i, call_record, result, arguments, call_id)
                            continue

            entry = {
                "index": i,
                "tool_name": tool_name,
                "arguments": arguments,
                "call_id": call_id,
                "call_record": call_record,
                "tool": tool,
            }

            if tool.can_run_in_parallel(arguments):
                parallel_entries.append(entry)
            else:
                serial_entries.append(entry)

        for entry in serial_entries:
            if cancel_event and cancel_event.is_set():
                raise AgentCancelled()
            self._emit_ui_event(
                "tool_start",
                tool_name=entry["tool_name"],
                arguments=entry["arguments"],
                call_id=entry["call_id"]
            )
            result = self._execute_tool(entry["tool_name"], entry["arguments"])
            _record_result(
                entry["index"],
                entry["call_record"],
                result,
                entry["arguments"],
                entry["call_id"]
            )

        if parallel_entries:
            max_workers = max(1, getattr(self.config.agent, "max_parallel_tools", 4))
            if len(parallel_entries) == 1 or max_workers == 1:
                for entry in parallel_entries:
                    if cancel_event and cancel_event.is_set():
                        raise AgentCancelled()
                    self._emit_ui_event(
                        "tool_start",
                        tool_name=entry["tool_name"],
                        arguments=entry["arguments"],
                        call_id=entry["call_id"]
                    )
                    result = self._execute_tool(entry["tool_name"], entry["arguments"])
                    _record_result(
                        entry["index"],
                        entry["call_record"],
                        result,
                        entry["arguments"],
                        entry["call_id"]
                    )
            else:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(len(parallel_entries), max_workers)
                ) as executor:
                    future_map = {}
                    for entry in parallel_entries:
                        if cancel_event and cancel_event.is_set():
                            raise AgentCancelled()
                        self._emit_ui_event(
                            "tool_start",
                            tool_name=entry["tool_name"],
                            arguments=entry["arguments"],
                            call_id=entry["call_id"]
                        )
                        future = executor.submit(
                            self._execute_tool,
                            entry["tool_name"],
                            entry["arguments"]
                        )
                        future_map[future] = entry
                    for future in concurrent.futures.as_completed(future_map):
                        entry = future_map[future]
                        try:
                            result = future.result()
                        except Exception as exc:
                            result = ToolResult(
                                tool_name=entry["tool_name"],
                                status=ToolResultStatus.ERROR,
                                output=None,
                                error_message=f"工具执行异常: {exc}"
                            )
                        _record_result(
                            entry["index"],
                            entry["call_record"],
                            result,
                            entry["arguments"],
                            entry["call_id"]
                        )

        final_results = []
        for idx, result in enumerate(results):
            if result is None:
                result = ToolResult(
                    tool_name=tool_calls[idx].function.name,
                    status=ToolResultStatus.ERROR,
                    output=None,
                    error_message="工具结果缺失"
                )
            final_results.append(result)

        return final_results
    
    def run(
        self,
        user_input: str,
        stream: bool = False,
        cancel_event: Optional[threading.Event] = None
    ) -> AgentResponse:
        """
        运行智能体处理用户请求

        这是智能体的主循环，实现“工具循环”模式

        Args:
            user_input: 用户输入
            stream: 是否启用流式输出
            cancel_event: 取消事件

        Returns:
            AgentResponse: 智能体响应
        """
        start_time = time.time()
        request_id = generate_request_id()
        total_tokens_used = 0
        
        logger.info(f"开始处理请求: {request_id}")
        logger.debug(f"用户输入: {user_input}")
        
        # 重置状态
        self.state = AgentState.THINKING
        self.current_step = 0
        self.steps = []
        
        # 添加用户消息到记忆
        self.memory.add_user_message(user_input)
        
        try:
            # 智能体循环
            while self.current_step < self.config.agent.max_iterations:
                if cancel_event and cancel_event.is_set():
                    raise AgentCancelled()
                self.current_step += 1
                
                logger.info(f"迭代 {self.current_step}/{self.config.agent.max_iterations}")
                
                # 刷新系统消息与上下文
                self._refresh_system_message()
                # 获取对话历史
                messages = self.memory.get_openai_messages()
                
                # 如果开启显式上下文模式，打印当前上下文
                if self.verbose_context:
                    self._print_current_context(messages)
                
                # 调用模型
                self.state = AgentState.THINKING
                self._emit_ui_event("llm_start", iteration=self.current_step)
                try:
                    if stream:
                        message, usage_total = self._call_llm_stream(messages, cancel_event=cancel_event)
                        total_tokens_used += usage_total
                        response = None
                    else:
                        response = self._call_llm(messages)
                        message = response.choices[0].message
                        total_tokens_used += self._extract_token_usage(response)
                except TimeoutError as te:
                    logger.error(f"LLM 超时：{str(te)}")
                    # 将错误信息反馈给用户并终止
                    self.memory.add_assistant_message("[系统] LLM 调用超时，请稍后重试。")
                    return AgentResponse(success=False, final_answer="LLM 调用超时，请稍后重试。", steps=self.steps, total_iterations=self.current_step, total_tokens_used=total_tokens_used, execution_time=time.time()-start_time, error_message=str(te))
                except AgentCancelled as exc:
                    raise exc
                except Exception as e:
                    logger.error(f"LLM 调用失败：{str(e)}")
                    self.memory.add_assistant_message(f"[系统] LLM 调用失败：{str(e)}")
                    return AgentResponse(success=False, final_answer=f"LLM 调用失败：{str(e)}", steps=self.steps, total_iterations=self.current_step, total_tokens_used=total_tokens_used, execution_time=time.time()-start_time, error_message=str(e))
                finally:
                    self._emit_ui_event("llm_end", iteration=self.current_step)
                
                # 解析响应
                # 保护性检查响应是否为空或格式异常
                if stream:
                    if not message:
                        logger.error("LLM 流式响应为空")
                        self.memory.add_assistant_message("[系统] LLM 流式响应为空。")
                        return AgentResponse(
                            success=False,
                            final_answer="LLM 流式响应为空。",
                            steps=self.steps,
                            total_iterations=self.current_step,
                            total_tokens_used=total_tokens_used,
                            execution_time=time.time() - start_time,
                            error_message="LLM 流式响应为空"
                        )
                else:
                    if not response or not hasattr(response, 'choices') or not response.choices:
                        logger.error("LLM 响应无效或为空")
                        self.memory.add_assistant_message("[系统] LLM 响应无效或为空。")
                        return AgentResponse(
                            success=False,
                            final_answer="LLM 响应无效或为空。",
                            steps=self.steps,
                            total_iterations=self.current_step,
                            total_tokens_used=0,
                            execution_time=time.time() - start_time,
                            error_message="LLM 响应无效或为空"
                        )
                    choice = response.choices[0]
                    message = choice.message

                # 提取思考内容
                content = getattr(message, 'content', None) or getattr(message, 'text', '') or ""
                thinking_text = self._extract_thinking(content)
                
                # 创建步骤记录
                step = AgentStep(
                    step_number=self.current_step,
                    thinking=thinking_text
                )
                self.steps.append(step)
                
                # 如果有思考内容，记录到日志
                if thinking_text:
                    logger.info(f"思考: {thinking_text[:200]}..." if len(thinking_text) > 200 else f"思考: {thinking_text}")
                    self._emit_ui_event(
                        "thinking",
                        thinking=thinking_text,
                        step=self.current_step
                    )
                
                if cancel_event and cancel_event.is_set():
                    raise AgentCancelled(partial=getattr(message, "content", "") or "")

                # 检查是否有工具调用
                if message.tool_calls:
                    self.state = AgentState.EXECUTING
                    
                    # 处理工具调用
                    tool_results = self._process_tool_calls(message.tool_calls, cancel_event=cancel_event)
                    
                    # 将助手消息添加到记忆（包含工具调用）
                    # 需要将工具调用也添加到消息中，便于接口识别
                    tool_calls_data = []
                    for tool_call in message.tool_calls:
                        tool_calls_data.append({
                            "id": str(tool_call.id) if hasattr(tool_call, "id") else "",
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        })
                    
                    self.memory.add_assistant_message(
                        self._strip_thinking_tags(message.content or ""),
                        metadata={"tool_calls": tool_calls_data} if tool_calls_data else None
                    )
                    
                    # 将工具结果添加到记忆
                    for i, tool_call in enumerate(message.tool_calls):
                        result = tool_results[i]
                        arguments = {}
                        if hasattr(self, "_tool_call_args") and i in self._tool_call_args:
                            arguments = self._tool_call_args[i]

                        result_text = format_tool_result(result.output)

                        # 对搜索结果进行精炼后再存入上下文
                        # 原始结果字段：标题、链接、正文、按钮
                        # 精炼后字段：标题、链接、摘要、关键内容
                        if tool_call.function.name == "web_search" and is_search_result(result_text):
                            result_text = refine_search_result(result_text)
                            logger.debug("搜索结果已精炼")

                        # 添加工具响应消息，必须包含工具调用标识（接口要求）
                        metadata = {"tool_name": tool_call.function.name}
                        
                        # 确保总是有工具调用标识（接口强制要求）
                        call_id = None
                        
                        # 首先尝试使用我们维护的工具调用标识映射
                        if hasattr(self, "_tool_call_ids") and i in self._tool_call_ids:
                            call_id = self._tool_call_ids[i]
                        # 其次尝试使用原始工具调用标识
                        elif hasattr(tool_call, "id") and tool_call.id:
                            call_id = str(tool_call.id).strip()
                        # 最后生成一个备选标识（以防万一）
                        else:
                            call_id = f"call_{tool_call.function.name}_{i}"
                        
                        # 添加到元数据（确保不为空）
                        if call_id:
                            metadata["tool_call_id"] = call_id

                        trace_text = format_tool_trace(
                            tool_call.function.name,
                            arguments,
                            result,
                            call_id=call_id,
                            output_override=result_text
                        )

                        self.memory.add_tool_message(
                            content=trace_text,
                            tool_name=tool_call.function.name,
                            metadata=metadata
                        )
                else:
                    # 没有工具调用，任务完成
                    self.state = AgentState.COMPLETED
                    
                    # 添加最终响应到记忆
                    final_answer = self._strip_thinking_tags(message.content or "")
                    self.memory.add_assistant_message(final_answer)
                    step.response = final_answer
                    
                    execution_time = time.time() - start_time
                    
                    logger.info(f"任务完成，耗时 {execution_time:.2f}s，迭代 {self.current_step} 次")
                    
                    return AgentResponse(
                        success=True,
                        final_answer=final_answer,
                        steps=self.steps,
                        total_iterations=self.current_step,
                        total_tokens_used=total_tokens_used,
                        execution_time=execution_time
                    )
            
            # 达到最大迭代次数
            self.state = AgentState.STOPPED
            execution_time = time.time() - start_time
            
            logger.warning(f"达到最大迭代次数: {self.config.agent.max_iterations}")
            
            return AgentResponse(
                success=False,
                final_answer="达到最大迭代次数，任务未完成。",
                steps=self.steps,
                total_iterations=self.current_step,
                total_tokens_used=total_tokens_used,
                execution_time=execution_time,
                error_message="达到最大迭代次数"
            )
            
        except AgentCancelled as exc:
            self.state = AgentState.STOPPED
            execution_time = time.time() - start_time
            logger.warning("智能体运行已取消")
            return AgentResponse(
                success=False,
                final_answer=exc.partial or "",
                steps=self.steps,
                total_iterations=self.current_step,
                total_tokens_used=total_tokens_used,
                execution_time=execution_time,
                error_message="cancelled"
            )
        except Exception as e:
            self.state = AgentState.ERROR
            execution_time = time.time() - start_time
            
            logger.error(f"智能体执行出错: {str(e)}")
            
            return AgentResponse(
                success=False,
                final_answer=f"执行过程中发生错误: {str(e)}",
                steps=self.steps,
                total_iterations=self.current_step,
                total_tokens_used=total_tokens_used,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def arun(
        self,
        user_input: str,
        stream: bool = False,
        cancel_event: Optional[threading.Event] = None
    ) -> AgentResponse:
        """
        异步运行智能体

        Args:
            user_input: 用户输入
            stream: 是否启用流式输出
            cancel_event: 取消事件

        Returns:
            AgentResponse: 智能体响应
        """
        # 目前简单地调用同步方法，未来可以实现真正的异步
        return self.run(user_input, stream=stream, cancel_event=cancel_event)
    
    def add_tool(self, tool: Union[BaseTool, Type[BaseTool]]) -> None:
        """
        添加工具

        Args:
            tool: 工具实例或类
        """
        if isinstance(tool, type):
            tool_instance = tool()
        else:
            tool_instance = tool
        
        self.tools[tool_instance.name] = tool_instance
        logger.info(f"添加工具: {tool_instance.name}")

        # 更新系统提示词
        self.base_system_prompt = get_system_prompt(
            tools=list(self.tools.values())
        )
        self._refresh_system_message()
    
    def remove_tool(self, tool_name: str) -> bool:
        """
        移除工具

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否成功移除
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"移除工具: {tool_name}")

            # 更新系统提示词
            self.base_system_prompt = get_system_prompt(
                tools=list(self.tools.values())
            )
            self._refresh_system_message()
            return True
        
        return False

    def reload_tools(self) -> None:
        """
        重新加载工具
        """
        self._init_tools()
        self.base_system_prompt = get_system_prompt(
            tools=list(self.tools.values())
        )
        self._refresh_system_message()
    
    def reset(self) -> None:
        """重置Agent状态"""
        self.state = AgentState.IDLE
        self.current_step = 0
        self.steps = []
        self.memory.clear(keep_system=True)
        
        logger.info("智能体状态已重置")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Agent状态

        Returns:
            Dict: 状态信息
        """
        return {
            "state": self.state.value,
            "current_step": self.current_step,
            "total_steps": len(self.steps),
            "tools_count": len(self.tools),
            "memory_entries": len(self.memory.messages),
            "context_length": self.memory.get_context_length(),
            "workspace": self.workspace,
            "files_count": len(self.memory.files),
        }
    
    # ==============================================================================
    # 文件上下文管理方法
    # ==============================================================================
    
    def add_file_to_context(
        self,
        path: str,
        content: Optional[str] = None,
        abstract: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        将文件添加到对话上下文

        Args:
            path: 文件路径（相对或绝对）
            content: 文件内容
            abstract: 文件摘要
            metadata: 额外元数据
        """
        self.memory.add_file(path, content, abstract, metadata)
        logger.info(f"文件已添加到上下文: {path}")
    
    def update_file_in_context(
        self,
        path: str,
        content: Optional[str] = None,
        abstract: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新上下文中的文件

        Args:
            path: 文件路径
            content: 新内容
            abstract: 新摘要
            metadata: 新元数据

        Returns:
            bool: 是否成功更新
        """
        result = self.memory.update_file(path, content, abstract, metadata)
        if result:
            logger.info(f"文件已更新: {path}")
            return True
        else:
            logger.warning(f"文件不存在，无法更新: {path}")
            return False
    
    def remove_file_from_context(self, path: str) -> bool:
        """
        从上下文中移除文件

        Args:
            path: 文件路径

        Returns:
            bool: 是否成功移除
        """
        result = self.memory.remove_file(path)
        if result:
            logger.info(f"文件已从上下文移除: {path}")
            return True
        else:
            logger.warning(f"文件不存在，无法移除: {path}")
            return False
    
    def list_context_files(self) -> List[str]:
        """
        列出上下文中的所有文件路径

        Returns:
            List[str]: 文件路径列表
        """
        return [f.path for f in self.memory.list_files()]
    
    def get_files_summary(self) -> str:
        """
        获取文件上下文摘要

        Returns:
            str: 文件摘要
        """
        return self.memory.get_files_summary()
    
    # ==============================================================================
    # 显式上下文模式方法
    # ==============================================================================
    
    def toggle_verbose_context(self) -> bool:
        """
        切换显式上下文模式

        Returns:
            bool: 当前状态
        """
        self.verbose_context = not self.verbose_context
        logger.info(f"显式上下文模式: {'开启' if self.verbose_context else '关闭'}")
        return self.verbose_context
    
    def _print_current_context(self, messages: List[Dict]) -> None:
        """
        打印当前传入LLM的上下文

        Args:
            messages: 消息列表
        """
        print("\n" + "=" * 80)
        print("当前上下文")
        print("=" * 80)

        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            role_display = {
                "system": "系统",
                "user": "用户",
                "assistant": "助手",
                "tool": "工具"
            }.get(role, f"未知角色: {role}")

            print(f"\n[{i}] {role_display}")
            print("-" * 80)

            if role == "system" and "## 当前文件上下文" in content:
                print(f"文件上下文消息（{content.count('###')} 个文件）")
            elif len(content) > 500:
                print(f"内容长度: {len(content)} 字符")
                print(f"预览: {content[:200]}...")
            else:
                print(content)

            if "tool_calls" in msg:
                for tc in msg["tool_calls"]:
                    print(f"   工具调用: {tc.get('function', {}).get('name', '未知')}")

            if role == "tool" and "name" in msg:
                print(f"工具: {msg['name']}")

        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        print(f"\n消息: {len(messages)} | 字符: {total_chars:,} | Token估计: ~{total_chars // 4:,}")
        print("=" * 80 + "\n")
