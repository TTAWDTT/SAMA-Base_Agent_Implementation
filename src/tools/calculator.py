# ==============================================================================
# 计算工具 / Calculator Tool
# ==============================================================================
# 提供数学计算功能
# Provides mathematical calculation functionality
#
# 安全说明 / Security Note:
# 此工具使用 eval() 计算数学表达式，但通过以下措施确保安全：
# 1. 使用 AST 解析验证表达式只包含允许的节点类型
# 2. 使用受限的执行环境（只包含数学函数）
# 3. 黑名单检查危险模式
# This tool uses eval() for math expressions, but ensures safety via:
# 1. AST parsing to validate expressions contain only allowed node types
# 2. Restricted execution environment (only math functions)
# 3. Blacklist checking for dangerous patterns
# ==============================================================================

import ast
import math
import re
from typing import Any

from pydantic import Field

from src.tools.base import BaseTool, ToolInput


class CalculatorInput(ToolInput):
    """计算器输入 / Calculator Input"""
    expression: str = Field(description="数学表达式 / Mathematical expression")


class CalculatorTool(BaseTool):
    """
    计算器工具 / Calculator Tool
    
    安全地计算数学表达式
    Safely evaluates mathematical expressions
    """
    
    name: str = "calculator"
    description: str = "计算数学表达式。参数：expression（数学表达式，如 '2 + 2' 或 'sqrt(16)'）/ Calculate mathematical expression. Parameters: expression (mathematical expression, e.g., '2 + 2' or 'sqrt(16)')"
    description_zh: str = "计算数学表达式。参数：expression（数学表达式，如 '2 + 2' 或 'sqrt(16)'）"
    description_en: str = "Calculate mathematical expression. Parameters: expression (mathematical expression, e.g., '2 + 2' or 'sqrt(16)')"
    input_schema = CalculatorInput
    
    # 允许的数学函数 / Allowed math functions
    ALLOWED_FUNCTIONS = {
        # 基本运算 / Basic operations
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        
        # 三角函数 / Trigonometric functions
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "atan2": math.atan2,
        
        # 指数和对数 / Exponential and logarithmic
        "exp": math.exp,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "sqrt": math.sqrt,
        
        # 其他 / Others
        "ceil": math.ceil,
        "floor": math.floor,
        "factorial": math.factorial,
        "gcd": math.gcd,
        
        # 常量 / Constants
        "pi": math.pi,
        "e": math.e,
    }
    
    def _run(self, expression: str) -> str:
        """
        计算数学表达式 / Calculate mathematical expression
        
        Args:
            expression: 数学表达式 / Mathematical expression
            
        Returns:
            str: 计算结果 / Calculation result
        """
        # 验证表达式安全性 / Validate expression safety
        self._validate_expression(expression)
        
        try:
            # 创建安全的执行环境 / Create safe execution environment
            safe_dict = {"__builtins__": {}}
            safe_dict.update(self.ALLOWED_FUNCTIONS)
            
            # 计算表达式 / Evaluate expression
            result = eval(expression, safe_dict)
            
            # 格式化结果 / Format result
            if isinstance(result, float):
                # 避免浮点数精度问题 / Avoid floating point precision issues
                if result.is_integer():
                    return str(int(result))
                return f"{result:.10g}"
            
            return str(result)
            
        except ZeroDivisionError:
            return "错误：除以零 / Error: Division by zero"
        except ValueError as e:
            return f"错误：数值错误 / Error: Value error - {str(e)}"
        except Exception as e:
            return f"错误：计算失败 / Error: Calculation failed - {str(e)}"
    
    def _validate_expression(self, expression: str) -> None:
        """
        验证表达式安全性 / Validate expression safety
        
        使用AST解析和黑名单检查双重验证
        Uses AST parsing and blacklist checking for double validation
        
        Args:
            expression: 数学表达式 / Mathematical expression
            
        Raises:
            ValueError: 如果表达式包含不安全的内容 / If expression contains unsafe content
        """
        # 检查危险关键字 / Check for dangerous keywords
        dangerous_patterns = [
            r"__\w+__",  # 双下划线
            r"import\s*\(",  # import
            r"exec\s*\(",  # exec
            r"eval\s*\(",  # eval
            r"open\s*\(",  # open
            r"file\s*\(",  # file
            r"input\s*\(",  # input
            r"compile\s*\(",  # compile
            r"globals\s*\(",  # globals
            r"locals\s*\(",  # locals
            r"getattr\s*\(",  # getattr
            r"setattr\s*\(",  # setattr
            r"delattr\s*\(",  # delattr
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, expression, re.IGNORECASE):
                raise ValueError(f"表达式包含不安全的内容 / Expression contains unsafe content: {pattern}")
        
        # 使用AST进行安全验证 / Use AST for safety validation
        try:
            tree = ast.parse(expression, mode='eval')
            self._validate_ast_node(tree.body)
        except SyntaxError as e:
            raise ValueError(f"表达式语法错误 / Expression syntax error: {str(e)}")
    
    def _validate_ast_node(self, node: ast.AST) -> None:
        """
        递归验证AST节点 / Recursively validate AST node
        
        只允许安全的节点类型 / Only allows safe node types
        
        Args:
            node: AST节点 / AST node
            
        Raises:
            ValueError: 如果节点类型不安全 / If node type is unsafe
        """
        # 允许的节点类型 / Allowed node types
        allowed_types = (
            ast.Expression, ast.Num, ast.Constant, ast.BinOp, ast.UnaryOp,
            ast.Compare, ast.Call, ast.Name, ast.Load, ast.Add, ast.Sub,
            ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv, ast.USub,
            ast.UAdd, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
            ast.List, ast.Tuple
        )
        
        if not isinstance(node, allowed_types):
            raise ValueError(f"不允许的表达式类型 / Disallowed expression type: {type(node).__name__}")
        
        # 验证函数调用只能是允许的函数 / Validate function calls are only allowed functions
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in self.ALLOWED_FUNCTIONS:
                    raise ValueError(f"不允许的函数 / Disallowed function: {node.func.id}")
            else:
                raise ValueError("不允许的函数调用方式 / Disallowed function call method")
        
        # 递归验证子节点 / Recursively validate child nodes
        for child in ast.iter_child_nodes(node):
            self._validate_ast_node(child)
