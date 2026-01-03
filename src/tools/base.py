# ==============================================================================
# 工具基类模块
# ==============================================================================
# 定义所有工具的基类和通用接口
# ==============================================================================

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

from src.core.logger import get_logger
from src.core.schema import ToolResult, ToolResultStatus

logger = get_logger("tools.base")


class ToolInput(BaseModel):
    """
    工具输入基类

    所有工具输入参数应继承此类
    """
    pass


class BaseTool(ABC):
    """
    工具基类

    所有自定义工具都应继承此类并实现相关方法
    """
    
    # 工具名称
    name: str = "base_tool"
    
    # 工具描述（用于模型理解工具功能）
    description: str = "基础工具"
    
    # 工具描述（中文版）
    description_zh: str = "基础工具"
    
    # 输入参数结构
    input_schema: Optional[Type[ToolInput]] = None

    # 是否允许子进程隔离执行
    subprocess_safe: bool = False

    # 工具所需权限列表
    required_permissions: list = []
    
    def __init__(self):
        """初始化工具"""
        self.logger = get_logger(f"tools.{self.name}")
    
    @abstractmethod
    def _run(self, **kwargs) -> Any:
        """
        执行工具（同步）

        子类必须实现此方法

        Args:
            **kwargs: 工具参数

        Returns:
            Any: 工具执行结果
        """
        pass
    
    async def _arun(self, **kwargs) -> Any:
        """
        执行工具（异步）

        默认调用同步方法，子类可以覆盖此方法实现异步执行

        Args:
            **kwargs: 工具参数

        Returns:
            Any: 工具执行结果
        """
        return self._run(**kwargs)
    
    def run(self, **kwargs) -> ToolResult:
        """
        运行工具并返回标准化结果

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 标准化的工具执行结果
        """
        import time
        
        start_time = time.time()
        
        try:
            self.logger.info(f"执行工具: {self.name}")
            self.logger.debug(f"参数: {kwargs}")
            
            result = self._run(**kwargs)
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"工具执行成功: {self.name}")
            
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.SUCCESS,
                output=result,
                execution_time=execution_time
            )
            
        except TimeoutError as e:
            execution_time = time.time() - start_time
            error_msg = f"工具执行超时: {str(e)}"
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
            error_msg = f"工具执行错误: {str(e)}"
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
        异步运行工具并返回标准化结果

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 标准化的工具执行结果
        """
        import time
        
        start_time = time.time()
        
        try:
            self.logger.info(f"异步执行工具: {self.name}")
            self.logger.debug(f"参数: {kwargs}")
            
            result = await self._arun(**kwargs)
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"工具执行成功: {self.name}")
            
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.SUCCESS,
                output=result,
                execution_time=execution_time
            )
            
        except TimeoutError as e:
            execution_time = time.time() - start_time
            error_msg = f"工具执行超时: {str(e)}"
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
            error_msg = f"工具执行错误: {str(e)}"
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
        获取工具的JSON Schema定义

        用于LLM的函数调用（符合Kimi API要求）

        Returns:
            Dict: JSON Schema格式的工具定义
        """
        # 基础参数结构（符合接口要求）
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # 如果定义了输入结构，使用模型生成并校验
        if self.input_schema:
            pydantic_schema = self.input_schema.model_json_schema()
            
            # 提取字段与必填项，确保符合接口格式
            if "properties" in pydantic_schema:
                parameters["properties"] = pydantic_schema["properties"]
            
            if "required" in pydantic_schema:
                parameters["required"] = pydantic_schema["required"]
        
        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description if self.description else f"{self.name} 工具",
                "parameters": parameters
            }
        }
        
        return schema

    def should_run_in_subprocess(self, arguments: Dict[str, Any]) -> bool:
        """
        判断是否需要在子进程执行
        """
        return self.subprocess_safe

    def can_run_in_parallel(self, arguments: Dict[str, Any]) -> bool:
        """
        判断是否允许并行执行
        """
        return True
    
    def __str__(self) -> str:
        return f"工具(name={self.name})"
    
    def __repr__(self) -> str:
        return f"工具(name={self.name}, description={self.description})"
