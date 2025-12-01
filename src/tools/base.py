# ==============================================================================
# 工具基类模块 / Tool Base Module
# ==============================================================================
# 定义所有工具的基类和通用接口
# Defines base class and common interface for all tools
# ==============================================================================

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

from src.core.logger import get_logger
from src.core.schema import ToolResult, ToolResultStatus

logger = get_logger("tools.base")


class ToolInput(BaseModel):
    """
    工具输入基类 / Tool Input Base Class
    
    所有工具输入参数应继承此类
    All tool input parameters should inherit from this class
    """
    pass


class BaseTool(ABC):
    """
    工具基类 / Tool Base Class
    
    所有自定义工具都应继承此类并实现相关方法
    All custom tools should inherit from this class and implement related methods
    """
    
    # 工具名称 / Tool name
    name: str = "base_tool"
    
    # 工具描述（用于LLM理解工具功能）/ Tool description (for LLM to understand tool functionality)
    description: str = "基础工具 / Base tool"
    
    # 工具描述（中文版）/ Tool description (Chinese version)
    description_zh: str = "基础工具"
    
    # 工具描述（英文版）/ Tool description (English version)
    description_en: str = "Base tool"
    
    # 输入参数Schema / Input parameter schema
    input_schema: Optional[Type[ToolInput]] = None
    
    def __init__(self):
        """初始化工具 / Initialize tool"""
        self.logger = get_logger(f"tools.{self.name}")
    
    @abstractmethod
    def _run(self, **kwargs) -> Any:
        """
        执行工具（同步）/ Execute tool (synchronous)
        
        子类必须实现此方法
        Subclasses must implement this method
        
        Args:
            **kwargs: 工具参数 / Tool parameters
            
        Returns:
            Any: 工具执行结果 / Tool execution result
        """
        pass
    
    async def _arun(self, **kwargs) -> Any:
        """
        执行工具（异步）/ Execute tool (asynchronous)
        
        默认调用同步方法，子类可以覆盖此方法实现异步执行
        Defaults to calling sync method, subclasses can override for async execution
        
        Args:
            **kwargs: 工具参数 / Tool parameters
            
        Returns:
            Any: 工具执行结果 / Tool execution result
        """
        return self._run(**kwargs)
    
    def run(self, **kwargs) -> ToolResult:
        """
        运行工具并返回标准化结果 / Run tool and return standardized result
        
        Args:
            **kwargs: 工具参数 / Tool parameters
            
        Returns:
            ToolResult: 标准化的工具执行结果 / Standardized tool execution result
        """
        import time
        
        start_time = time.time()
        
        try:
            self.logger.info(f"执行工具 / Executing tool: {self.name}")
            self.logger.debug(f"参数 / Parameters: {kwargs}")
            
            result = self._run(**kwargs)
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"工具执行成功 / Tool executed successfully: {self.name}")
            
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.SUCCESS,
                output=result,
                execution_time=execution_time
            )
            
        except TimeoutError as e:
            execution_time = time.time() - start_time
            error_msg = f"工具执行超时 / Tool execution timeout: {str(e)}"
            self.logger.error(error_msg)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.TIMEOUT,
                output=None,
                error_message=error_msg,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"工具执行错误 / Tool execution error: {str(e)}"
            self.logger.error(error_msg)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.ERROR,
                output=None,
                error_message=error_msg,
                execution_time=execution_time
            )
    
    async def arun(self, **kwargs) -> ToolResult:
        """
        异步运行工具并返回标准化结果 / Run tool asynchronously and return standardized result
        
        Args:
            **kwargs: 工具参数 / Tool parameters
            
        Returns:
            ToolResult: 标准化的工具执行结果 / Standardized tool execution result
        """
        import time
        
        start_time = time.time()
        
        try:
            self.logger.info(f"异步执行工具 / Executing tool asynchronously: {self.name}")
            self.logger.debug(f"参数 / Parameters: {kwargs}")
            
            result = await self._arun(**kwargs)
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"工具执行成功 / Tool executed successfully: {self.name}")
            
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.SUCCESS,
                output=result,
                execution_time=execution_time
            )
            
        except TimeoutError as e:
            execution_time = time.time() - start_time
            error_msg = f"工具执行超时 / Tool execution timeout: {str(e)}"
            self.logger.error(error_msg)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.TIMEOUT,
                output=None,
                error_message=error_msg,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"工具执行错误 / Tool execution error: {str(e)}"
            self.logger.error(error_msg)
            
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.ERROR,
                output=None,
                error_message=error_msg,
                execution_time=execution_time
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """
        获取工具的JSON Schema定义 / Get tool's JSON Schema definition
        
        用于LLM的函数调用
        Used for LLM function calling
        
        Returns:
            Dict: JSON Schema格式的工具定义 / Tool definition in JSON Schema format
        """
        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        # 如果定义了输入Schema，使用Pydantic生成
        # If input schema is defined, use Pydantic to generate
        if self.input_schema:
            schema["function"]["parameters"] = self.input_schema.model_json_schema()
        
        return schema
    
    def __str__(self) -> str:
        return f"Tool(name={self.name})"
    
    def __repr__(self) -> str:
        return f"Tool(name={self.name}, description={self.description})"
