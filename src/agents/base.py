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
from typing import Any, Callable, Dict, List, Optional, Type, Union

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
from src.utils.helpers import (
    format_tool_result,
    generate_request_id,
    estimate_tokens,
)

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
        self.memory.set_system_message(self.system_prompt)
        
        # 初始化OpenAI客户端 / Initialize OpenAI client
        self._init_client()
        
        # Agent状态 / Agent state
        self.state = AgentState.IDLE
        self.current_step = 0
        self.steps: List[AgentStep] = []
        
        logger.info(f"Agent初始化完成 / Agent initialized with {len(self.tools)} tools")
    
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
        tools = []
        for tool in self.tools.values():
            # 获取工具的Schema定义
            # Get tool schema definition
            tool_schema = tool.get_schema()
            
            # 确保基础结构符合Kimi要求
            # Ensure basic structure complies with Kimi requirements
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description if tool.description else f"{tool.name} tool",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            # 合并Schema中的参数定义
            # Merge parameter definitions from schema
            if "function" in tool_schema and "parameters" in tool_schema["function"]:
                params = tool_schema["function"]["parameters"]
                
                # 确保parameters是object类型
                # Ensure parameters is object type
                if isinstance(params, dict):
                    if "properties" in params:
                        tool_def["function"]["parameters"]["properties"] = params["properties"]
                    if "required" in params:
                        tool_def["function"]["parameters"]["required"] = params["required"]
            
            tools.append(tool_def)
        
        return tools
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        调用LLM / Call LLM
        
        Args:
            messages: 消息列表 / List of messages
            
        Returns:
            Dict: LLM响应 / LLM response
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config.model.model_name,
                messages=messages,
                tools=self._get_tools_for_api() if self.tools else None,
                temperature=self.config.model.temperature,
                max_tokens=self.config.model.max_tokens,
            )
            
            return response
            
        except Exception as e:
            logger.error(f"LLM调用失败 / LLM call failed: {str(e)}")
            raise
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        执行工具 / Execute tool
        
        Args:
            tool_name: 工具名称 / Tool name
            arguments: 工具参数 / Tool arguments
            
        Returns:
            ToolResult: 工具执行结果 / Tool execution result
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
        
        result = tool.run(**arguments)
        
        logger.info(f"工具执行完成 / Tool execution completed: {tool_name}, 状态/status: {result.status.value}")
        
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
                
                # 调用LLM / Call LLM
                self.state = AgentState.THINKING
                response = self._call_llm(messages)
                
                # 解析响应 / Parse response
                choice = response.choices[0]
                message = choice.message
                
                # 创建步骤记录 / Create step record
                step = AgentStep(
                    step_number=self.current_step,
                    thought=message.content or ""
                )
                self.steps.append(step)
                
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
        """
        重置Agent状态 / Reset Agent state
        """
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
            "context_length": self.memory.get_context_length()
        }
