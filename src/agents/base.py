# ==============================================================================
# AI Agent 基础实现 / AI Agent Base Implementation
# ==============================================================================
# 实现基于LLM的Agent循环，通过工具完成任务
# Implements LLM-based Agent loop, completing tasks through tools
#
# 设计理念 / Design Philosophy:
# - Agent是一个在循环中使用工具来实现目标的LLM
# - Agent can handle complex tasks, but the implementation is usually simple
# - It's typically just an LLM using tools in a loop based on environment feedback
#
# 参考 / Reference:
# - https://www.anthropic.com/engineering/building-effective-agents
# ==============================================================================

import json
import time
import re
import os
import concurrent.futures
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from openai import OpenAI

from src.core.config import get_config, Config
from src.core.logger import get_logger, init_logging
from src.core.memory import ConversationMemory, get_memory
from src.core.prompts import get_system_prompt
from src.core.schema import (
    AgentState,
    AgentStep,
    AgentResponse,
    ToolCall,
    ToolResult,
    ToolResultStatus,
)
from src.tools import DEFAULT_TOOLS, BaseTool
from src.utils.helpers import format_tool_result, generate_request_id, is_search_result, refine_search_result

logger = get_logger("agents.base")


class BaseAgent:
    """
    基础Agent类 / Base Agent Class
    
    实现核心的Agent循环逻辑：
    1. 接收用户输入
    2. 调用LLM进行思考
    3. 根据LLM的决策执行工具
    4. 将工具结果反馈给LLM
    5. 重复直到任务完成或达到最大迭代次数
    
    Implements core Agent loop logic:
    1. Receive user input
    2. Call LLM for thinking
    3. Execute tools based on LLM's decision
    4. Feed tool results back to LLM
    5. Repeat until task completed or max iterations reached
    """
    
    def __init__(
        self,
        tools: Optional[List[Union[BaseTool, Type[BaseTool]]]] = None,
        config: Optional[Config] = None,
        memory: Optional[ConversationMemory] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        初始化Agent / Initialize Agent
        
        Args:
            tools: 可用工具列表（实例或类）/ List of available tools (instances or classes)
            config: 配置对象 / Configuration object
            memory: 对话记忆 / Conversation memory
            system_prompt: 自定义系统提示词 / Custom system prompt
        """
        # 初始化日志 / Initialize logging
        init_logging()
        
        # 加载配置 / Load configuration
        self.config = config or get_config()
        
        # 初始化工作区 / Initialize workspace
        self._init_workspace()
        
        # 初始化工具 / Initialize tools
        self._init_tools(tools)
        
        # 初始化记忆 / Initialize memory
        self.memory = memory or get_memory()
        
        # 设置系统提示词 / Set system prompt
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = get_system_prompt(
                tools=list(self.tools.values()),
                language=self.config.agent.prompt_language
            )
        
        # 注入工作区信息到系统提示词 / Inject workspace info into system prompt
        self._inject_workspace_to_prompt()
        
        self.memory.set_system_message(self.system_prompt)
        
        # 初始化OpenAI客户端 / Initialize OpenAI client
        self._init_client()
        
        # Agent状态 / Agent state
        self.state = AgentState.IDLE
        self.current_step = 0
        self.steps: List[AgentStep] = []
        
        # 显式上下文模式 / Explicit context mode
        self.verbose_context = False  # 是否显示详细上下文 / Whether to show detailed context
        
        logger.info(f"Agent初始化完成 / Agent initialized with {len(self.tools)} tools")
        logger.info(f"工作区 / Workspace: {self.workspace}")
    
    def _init_workspace(self) -> None:
        """
        初始化工作区目录 / Initialize workspace directory
        
        创建工作区目录（如果不存在），并设置工作区路径
        Creates workspace directory if not exists, and sets workspace path
        """
        workspace_path = Path(self.config.agent.workspace)
        workspace_path.mkdir(parents=True, exist_ok=True)
        self.workspace = str(workspace_path.resolve())
        logger.info(f"工作区已初始化 / Workspace initialized: {self.workspace}")
    
    def _inject_workspace_to_prompt(self) -> None:
        """
        将工作区信息注入到系统提示词 / Inject workspace info into system prompt
        
        告知Agent可以使用的工作区路径和文件上下文管理能力
        Inform Agent about available workspace path and file context management capabilities
        """
        workspace_section = f"""

## 工作区与文件管理 / Workspace and File Management

**工作区路径 / Workspace Path**: `{self.workspace}`

你可以在工作区中创建、修改和管理文件。对于重要的中间文件（如生成的脚本、数据文件、搜索结果等），你应该：
You can create, modify and manage files in the workspace. For important intermediate files (e.g., generated scripts, data files), you should:

1. **将文件保存到工作区** / Save files to workspace
2. **使用文件工具记录文件上下文** / Record file context using file tools
3. **在对话中引用这些文件** / Reference these files in conversation
4. **及时清理不再需要的旧文件** / Clean up old files that are no longer needed

当前文件上下文 / Current file context:
{self.memory.get_files_summary()}

## 工作记忆 / Working Memory

{self.memory.get_context_summary()}

⚠️ **重要提示 / Important Notes**:
- 避免重复执行相同操作 / Avoid repeating the same operations
- 如果某个工具已经成功调用过，分析结果而不是重复调用 / If a tool has been called successfully, analyze the result instead of calling again
- 每次操作前，先检查工作记忆中是否已有相关结果 / Before each operation, check if results already exist in working memory
"""
        self.system_prompt += workspace_section
    
    def _extract_thinking(self, content: str) -> Optional[str]:
        """
        从内容中提取 <thinking> 标签内的文本 / Extract text within <thinking> tags
        
        Args:
            content: 消息内容 / Message content
            
        Returns:
            Optional[str]: 思考内容，如果没有则返回 None / Thinking content, None if not found
        """
        pattern = r'<thinking>(.*?)</thinking>'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        return None
    
    def _init_tools(self, tools: Optional[List[Union[BaseTool, Type[BaseTool]]]] = None) -> None:
        """
        初始化工具 / Initialize tools
        
        Args:
            tools: 工具列表 / List of tools
        """
        self.tools: Dict[str, BaseTool] = {}
        
        # 使用默认工具或自定义工具 / Use default or custom tools
        tool_list = tools or DEFAULT_TOOLS
        
        for tool in tool_list:
            # 如果是类，实例化它 / If it's a class, instantiate it
            if isinstance(tool, type):
                tool_instance = tool()
            else:
                tool_instance = tool
            
            self.tools[tool_instance.name] = tool_instance
            logger.debug(f"注册工具 / Registered tool: {tool_instance.name}")
    
    def _init_client(self) -> None:
        """
        初始化OpenAI客户端 / Initialize OpenAI client
        
        使用OpenAI兼容接口连接模型
        Uses OpenAI compatible interface to connect to model
        """
        self.client = OpenAI(
            api_key=self.config.model.api_key,
            base_url=self.config.model.base_url,
            timeout=self.config.model.timeout
        )
        
        logger.info(f"LLM客户端初始化 / LLM client initialized: {self.config.model.base_url}")
    
    def _get_tools_for_api(self) -> List[Dict[str, Any]]:
        """
        获取API格式的工具定义 / Get tool definitions in API format
        
        符合Kimi API要求的工具定义格式
        Tool definition format compliant with Kimi API requirements
        
        Returns:
            List[Dict]: OpenAI函数调用格式的工具定义 / Tool definitions in OpenAI function calling format
        """
        return [tool.get_schema() for tool in self.tools.values()]
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        调用LLM / Call LLM
        """
        try:
            return self.client.chat.completions.create(
                model=self.config.model.effective_model_name,
                messages=messages,
                tools=self._get_tools_for_api() if self.tools else None,
                temperature=self.config.model.temperature,
                max_tokens=self.config.model.max_tokens,
            )
        except Exception as e:
            logger.error(f"LLM调用失败 / LLM call failed: {str(e)}")
            raise
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        执行工具 / Execute tool with timeout protection
        """
        if tool_name not in self.tools:
            return ToolResult(
                tool_name=tool_name,
                status=ToolResultStatus.ERROR,
                output=None,
                error_message=f"未知工具 / Unknown tool: {tool_name}"
            )
        
        tool = self.tools[tool_name]
        logger.info(f"执行工具 / Executing tool: {tool_name}")
        logger.debug(f"参数 / Arguments: {arguments}")
        
        # 使用线程池为工具执行设置超时，避免阻塞主循环
        tool_timeout = getattr(tool, "default_timeout", None)
        if tool_timeout is None:
            tool_timeout = getattr(self.config.tools.code_executor, "timeout", 30)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(tool.run, **arguments)
            try:
                result = future.result(timeout=tool_timeout)
            except concurrent.futures.TimeoutError:
                logger.error(f"工具执行超时 / Tool execution timeout: {tool_name} after {tool_timeout}s")
                future.cancel()
                return ToolResult(
                    tool_name=tool_name,
                    status=ToolResultStatus.TIMEOUT,
                    output=None,
                    error_message=f"Tool execution timeout after {tool_timeout}s",
                    execution_time=tool_timeout
                )
            except Exception as e:
                logger.error(f"工具执行失败 / Tool execution failed: {str(e)}")
                return ToolResult(
                    tool_name=tool_name,
                    status=ToolResultStatus.ERROR,
                    output=None,
                    error_message=str(e),
                    execution_time=0.0
                )
        
        logger.info(f"工具执行完成 / Tool execution completed: {tool_name}, 状态/status: {getattr(result, 'status', 'unknown')}")
        
        return result
    
    def _process_tool_calls(self, tool_calls: List[Any]) -> List[ToolResult]:
        """
        处理工具调用 / Process tool calls
        
        Args:
            tool_calls: 工具调用列表 / List of tool calls
            
        Returns:
            List[ToolResult]: 工具执行结果列表 / List of tool execution results
        """
        results = []
        # 维护tool_call_id的映射
        # Maintain mapping of tool_call_ids
        self._tool_call_ids = {}
        
        recent_tool_calls = []
        for i, tool_call in enumerate(tool_calls):
            tool_name = tool_call.function.name
            
            # 解析参数 / Parse arguments
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}
            
            # 获取tool_call_id（使用LLM返回的）
            # Get tool_call_id from LLM response
            call_id = getattr(tool_call, "id", None) or f"call_{tool_name}_{i}"
            self._tool_call_ids[i] = call_id
            
            # 记录工具调用 / Record tool call
            call_record = ToolCall(
                tool_name=tool_name,
                arguments=arguments,
                call_id=call_id
            )
            
            # 如果是文件相关工具，进行额外检查：仅在读取时确保目标文件在memory.files或路径存在
            if tool_name in ("file", "read_file", "write_file"):
                operation = str(arguments.get("operation", "")).lower()
                if tool_name == "read_file":
                    operation = "read"
                elif tool_name == "write_file":
                    operation = "write"

                if operation == "read":
                    file_path = arguments.get("file_path") or arguments.get("path") or arguments.get("file")
                    if file_path:
                        # 优先检查内存上下文中的文件
                        known_paths = [f.path for f in self.memory.list_files()]
                        if file_path not in known_paths and not os.path.exists(file_path):
                            logger.warning(f"文件工具调用使用了未知路径或不存在的文件，跳过: {file_path}")
                            results.append(ToolResult(tool_name=tool_name, status=ToolResultStatus.ERROR, output=None, error_message=f"Unknown or missing file: {file_path}"))
                            # 更新当前步骤
                            if self.steps:
                                self.steps[-1].tool_calls.append(call_record)
                                self.steps[-1].tool_results.append(results[-1])
                            continue

            # 执行工具 / Execute tool
            result = self._execute_tool(tool_name, arguments)
            results.append(result)
            
            # 更新当前步骤 / Update current step
            if self.steps:
                self.steps[-1].tool_calls.append(call_record)
                self.steps[-1].tool_results.append(result)
        
        return results
    
    def run(self, user_input: str) -> AgentResponse:
        """
        运行Agent处理用户请求 / Run Agent to process user request
        
        这是Agent的主循环，实现"工具循环"模式
        This is the Agent's main loop, implementing the "tool loop" pattern
        
        Args:
            user_input: 用户输入 / User input
            
        Returns:
            AgentResponse: Agent响应 / Agent response
        """
        start_time = time.time()
        request_id = generate_request_id()
        
        logger.info(f"开始处理请求 / Starting request: {request_id}")
        logger.debug(f"用户输入 / User input: {user_input}")
        
        # 重置状态 / Reset state
        self.state = AgentState.THINKING
        self.current_step = 0
        self.steps = []
        
        # 添加用户消息到记忆 / Add user message to memory
        self.memory.add_user_message(user_input)
        
        try:
            # Agent循环 / Agent loop
            while self.current_step < self.config.agent.max_iterations:
                self.current_step += 1
                
                logger.info(f"迭代 / Iteration {self.current_step}/{self.config.agent.max_iterations}")
                
                # 获取对话历史 / Get conversation history
                messages = self.memory.get_openai_messages()
                
                # 如果开启显式上下文模式，打印当前上下文 / Print context if verbose mode enabled
                if self.verbose_context:
                    self._print_current_context(messages)
                
                # 调用LLM / Call LLM
                self.state = AgentState.THINKING
                try:
                    response = self._call_llm(messages)
                except TimeoutError as te:
                    logger.error(f"LLM 超时：{str(te)}")
                    # 将错误信息反馈给用户并终止
                    self.memory.add_assistant_message("[系统] LLM 调用超时，请稍后重试。")
                    return AgentResponse(success=False, final_answer="LLM 调用超时，请稍后重试。", steps=self.steps, total_iterations=self.current_step, total_tokens_used=0, execution_time=time.time()-start_time, error_message=str(te))
                except Exception as e:
                    logger.error(f"LLM 调用失败：{str(e)}")
                    self.memory.add_assistant_message(f"[系统] LLM 调用失败：{str(e)}")
                    return AgentResponse(success=False, final_answer=f"LLM 调用失败：{str(e)}", steps=self.steps, total_iterations=self.current_step, total_tokens_used=0, execution_time=time.time()-start_time, error_message=str(e))
                
                # 解析响应 / Parse response
                # 保护性检查响应是否为空或格式异常
                if not response or not hasattr(response, 'choices') or not response.choices:
                    logger.error("LLM 响应无效或为空 / Invalid or empty LLM response")
                    self.memory.add_assistant_message("[系统] LLM 响应无效或为空。")
                    return AgentResponse(success=False, final_answer="LLM 响应无效或为空。", steps=self.steps, total_iterations=self.current_step, total_tokens_used=0, execution_time=time.time()-start_time, error_message="Invalid LLM response")
                
                choice = response.choices[0]
                message = choice.message
                
                # 提取 thinking（Extended Thinking）/ Extract thinking
                content = getattr(message, 'content', None) or getattr(message, 'text', '') or ""
                thinking_text = self._extract_thinking(content)
                
                # 创建步骤记录 / Create step record
                step = AgentStep(
                    step_number=self.current_step,
                    thinking=thinking_text
                )
                self.steps.append(step)
                
                # 如果有 thinking，记录到日志 / Log thinking if present
                if thinking_text:
                    logger.info(f"💭 Thinking: {thinking_text[:200]}..." if len(thinking_text) > 200 else f"💭 Thinking: {thinking_text}")
                
                # 检查是否有工具调用 / Check for tool calls
                if message.tool_calls:
                    self.state = AgentState.EXECUTING
                    
                    # 处理工具调用 / Process tool calls
                    tool_results = self._process_tool_calls(message.tool_calls)
                    
                    # 将助手消息添加到记忆（包含工具调用）
                    # Add assistant message to memory (including tool calls)
                    # 需要将tool_calls也添加到消息中，以便Kimi API能识别
                    # Must include tool_calls so Kimi API can recognize them
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
                        message.content or "",
                        metadata={"tool_calls": tool_calls_data} if tool_calls_data else None
                    )
                    
                    # 将工具结果添加到记忆 / Add tool results to memory
                    for i, tool_call in enumerate(message.tool_calls):
                        result = tool_results[i]
                        result_text = format_tool_result(result.output)
                        if result.error_message:
                            result_text = f"错误 / Error: {result.error_message}"
                        
                        # 对搜索结果进行精炼后再存入上下文
                        # Refine search results before storing in context
                        # 原始结果格式：title/url/body/button
                        # 精炼后格式：title/url/abstract/key_content
                        if tool_call.function.name == "web_search" and is_search_result(result_text):
                            result_text = refine_search_result(result_text)
                            logger.debug("搜索结果已精炼 / Search result refined for context")

                        # 添加工具响应消息，必须包含tool_call_id（Kimi API 要求）
                        # Add tool response message with required tool_call_id (Kimi API requirement)
                        metadata = {"tool_name": tool_call.function.name}
                        
                        # 确保总是有tool_call_id（Kimi API强制要求）
                        # Always ensure tool_call_id is present (Kimi API requirement)
                        call_id = None
                        
                        # 首先尝试使用我们维护的tool_call_id映射
                        # First try to use our maintained tool_call_id mapping
                        if hasattr(self, "_tool_call_ids") and i in self._tool_call_ids:
                            call_id = self._tool_call_ids[i]
                        # 其次尝试使用原始工具调用ID
                        # Otherwise use original tool call ID
                        elif hasattr(tool_call, "id") and tool_call.id:
                            call_id = str(tool_call.id).strip()
                        # 最后生成一个备选ID（以防万一）
                        # Last resort: generate a fallback ID
                        else:
                            call_id = f"call_{tool_call.function.name}_{i}"
                        
                        # 添加到元数据（确保不为空）
                        # Add to metadata (ensure not empty)
                        if call_id:
                            metadata["tool_call_id"] = call_id

                        self.memory.add_tool_message(
                            content=result_text,
                            tool_name=tool_call.function.name,
                            metadata=metadata
                        )
                else:
                    # 没有工具调用，任务完成 / No tool calls, task completed
                    self.state = AgentState.COMPLETED
                    
                    # 添加最终响应到记忆 / Add final response to memory
                    final_answer = message.content or ""
                    self.memory.add_assistant_message(final_answer)
                    step.response = final_answer
                    
                    execution_time = time.time() - start_time
                    
                    logger.info(f"任务完成 / Task completed in {execution_time:.2f}s, {self.current_step} iterations")
                    
                    return AgentResponse(
                        success=True,
                        final_answer=final_answer,
                        steps=self.steps,
                        total_iterations=self.current_step,
                        total_tokens_used=0,
                        execution_time=execution_time
                    )
            
            # 达到最大迭代次数 / Reached max iterations
            self.state = AgentState.STOPPED
            execution_time = time.time() - start_time
            
            logger.warning(f"达到最大迭代次数 / Reached max iterations: {self.config.agent.max_iterations}")
            
            return AgentResponse(
                success=False,
                final_answer="达到最大迭代次数，任务未完成。/ Reached max iterations, task not completed.",
                steps=self.steps,
                total_iterations=self.current_step,
                total_tokens_used=0,
                execution_time=execution_time,
                error_message="Max iterations reached"
            )
            
        except Exception as e:
            self.state = AgentState.ERROR
            execution_time = time.time() - start_time
            
            logger.error(f"Agent执行出错 / Agent execution error: {str(e)}")
            
            return AgentResponse(
                success=False,
                final_answer=f"执行过程中发生错误 / Error during execution: {str(e)}",
                steps=self.steps,
                total_iterations=self.current_step,
                total_tokens_used=0,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    async def arun(self, user_input: str) -> AgentResponse:
        """
        异步运行Agent / Run Agent asynchronously
        
        Args:
            user_input: 用户输入 / User input
            
        Returns:
            AgentResponse: Agent响应 / Agent response
        """
        # 目前简单地调用同步方法，未来可以实现真正的异步
        # Currently just calls sync method, can implement true async in the future
        return self.run(user_input)
    
    def add_tool(self, tool: Union[BaseTool, Type[BaseTool]]) -> None:
        """
        添加工具 / Add tool
        
        Args:
            tool: 工具实例或类 / Tool instance or class
        """
        if isinstance(tool, type):
            tool_instance = tool()
        else:
            tool_instance = tool
        
        self.tools[tool_instance.name] = tool_instance
        logger.info(f"添加工具 / Added tool: {tool_instance.name}")
        
        # 更新系统提示词 / Update system prompt
        self.system_prompt = get_system_prompt(
            tools=list(self.tools.values()),
            language=self.config.agent.prompt_language
        )
        self.memory.set_system_message(self.system_prompt)
    
    def remove_tool(self, tool_name: str) -> bool:
        """
        移除工具 / Remove tool
        
        Args:
            tool_name: 工具名称 / Tool name
            
        Returns:
            bool: 是否成功移除 / Whether removal was successful
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"移除工具 / Removed tool: {tool_name}")
            
            # 更新系统提示词 / Update system prompt
            self.system_prompt = get_system_prompt(
                tools=list(self.tools.values()),
                language=self.config.agent.prompt_language
            )
            self.memory.set_system_message(self.system_prompt)
            return True
        
        return False
    
    def reset(self) -> None:
        """重置Agent状态 / Reset Agent state"""
        self.state = AgentState.IDLE
        self.current_step = 0
        self.steps = []
        self.memory.clear(keep_system=True)
        
        logger.info("Agent状态已重置 / Agent state reset")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Agent状态 / Get Agent status
        
        Returns:
            Dict: 状态信息 / Status information
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
    # 文件上下文管理方法 / File Context Management Methods
    # ==============================================================================
    
    def add_file_to_context(
        self,
        path: str,
        content: Optional[str] = None,
        abstract: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        将文件添加到对话上下文 / Add file to conversation context
        
        Args:
            path: 文件路径（相对或绝对）/ File path (relative or absolute)
            content: 文件内容 / File content
            abstract: 文件摘要 / File abstract
            metadata: 额外元数据 / Extra metadata
        """
        self.memory.add_file(path, content, abstract, metadata)
        logger.info(f"文件已添加到上下文 / File added to context: {path}")
    
    def update_file_in_context(
        self,
        path: str,
        content: Optional[str] = None,
        abstract: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新上下文中的文件 / Update file in context
        
        Args:
            path: 文件路径 / File path
            content: 新内容 / New content
            abstract: 新摘要 / New abstract
            metadata: 新元数据 / New metadata
            
        Returns:
            bool: 是否成功更新 / Whether update was successful
        """
        result = self.memory.update_file(path, content, abstract, metadata)
        if result:
            logger.info(f"文件已更新 / File updated: {path}")
            return True
        else:
            logger.warning(f"文件不存在，无法更新 / File does not exist, cannot update: {path}")
            return False
    
    def remove_file_from_context(self, path: str) -> bool:
        """
        从上下文中移除文件 / Remove file from context
        
        Args:
            path: 文件路径 / File path
            
        Returns:
            bool: 是否成功移除 / Whether removal was successful
        """
        result = self.memory.remove_file(path)
        if result:
            logger.info(f"文件已从上下文移除 / File removed from context: {path}")
            return True
        else:
            logger.warning(f"文件不存在，无法移除 / File does not exist, cannot remove: {path}")
            return False
    
    def list_context_files(self) -> List[str]:
        """
        列出上下文中的所有文件路径 / List all file paths in context
        
        Returns:
            List[str]: 文件路径列表 / List of file paths
        """
        return [f.path for f in self.memory.list_files()]
    
    def get_files_summary(self) -> str:
        """
        获取文件上下文摘要 / Get files context summary
        
        Returns:
            str: 文件摘要 / Files summary
        """
        return self.memory.get_files_summary()
    
    # ==============================================================================
    # 显式上下文模式方法 / Verbose Context Mode Methods
    # ==============================================================================
    
    def toggle_verbose_context(self) -> bool:
        """
        切换显式上下文模式 / Toggle verbose context mode
        
        Returns:
            bool: 当前状态 / Current state
        """
        self.verbose_context = not self.verbose_context
        logger.info(f"显式上下文模式 / Verbose context mode: {'开启 / ON' if self.verbose_context else '关闭 / OFF'}")
        return self.verbose_context
    
    def _print_current_context(self, messages: List[Dict]) -> None:
        """
        打印当前传入LLM的上下文 / Print current context sent to LLM
        
        Args:
            messages: 消息列表 / Message list
        """
        print("\n" + "="*80)
        print("📋 当前上下文 / Current Context")
        print("="*80)
        
        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            role_display = {
                "system": "⚙️  系统 / System",
                "user": "👤 用户 / User",
                "assistant": "🤖 助手 / Assistant",
                "tool": "🔧 工具 / Tool"
            }.get(role, f"❓ {role}")
            
            print(f"\n[{i}] {role_display}")
            print("-" * 80)
            
            # 根据内容长度决定显示方式 / Display based on content length
            if role == "system" and "📁 当前文件上下文" in content:
                print(f"📁 文件上下文消息 ({content.count('###')} 个文件)")
            elif len(content) > 500:
                print(f"📊 内容长度: {len(content)} 字符")
                print(f"📝 预览: {content[:200]}...")
            else:
                print(content)
            
            # 显示工具调用信息 / Show tool call info
            if "tool_calls" in msg:
                for tc in msg['tool_calls']:
                    print(f"   🔧 {tc.get('function', {}).get('name', 'unknown')}")
            
            if role == "tool" and "name" in msg:
                print(f"🏷️  工具: {msg['name']}")
        
        # 统计信息 / Statistics
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        print(f"\n📊 消息: {len(messages)} | 字符: {total_chars:,} | Token估计: ~{total_chars // 4:,}")
        print("="*80 + "\n")
