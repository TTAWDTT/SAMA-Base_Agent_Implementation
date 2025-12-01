# ==============================================================================
# 工具函数模块 / Utility Functions Module
# ==============================================================================
# 提供各种通用工具函数
# Provides various utility functions
# ==============================================================================

import json
import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")


def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,)
) -> Callable[..., T]:
    """
    带指数退避的重试装饰器 / Retry decorator with exponential backoff
    
    Args:
        func: 要重试的函数 / Function to retry
        max_retries: 最大重试次数 / Maximum retries
        base_delay: 基础延迟（秒）/ Base delay (seconds)
        max_delay: 最大延迟（秒）/ Maximum delay (seconds)
        exceptions: 要捕获的异常类型 / Exception types to catch
        
    Returns:
        Callable: 包装后的函数 / Wrapped function
    """
    def wrapper(*args, **kwargs) -> T:
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    time.sleep(delay)
        
        raise last_exception
    
    return wrapper


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    截断文本 / Truncate text
    
    Args:
        text: 原始文本 / Original text
        max_length: 最大长度 / Maximum length
        suffix: 截断后缀 / Truncation suffix
        
    Returns:
        str: 截断后的文本 / Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    从文本中提取JSON / Extract JSON from text
    
    尝试从文本中找到并解析JSON内容
    Attempts to find and parse JSON content from text
    
    Args:
        text: 包含JSON的文本 / Text containing JSON
        
    Returns:
        Optional[Dict]: 解析后的JSON，如果失败则返回None / Parsed JSON, or None if failed
    """
    # 尝试直接解析 / Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试找到JSON块 / Try to find JSON block
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",  # Markdown JSON块
        r"```\s*([\s\S]*?)\s*```",  # 通用代码块
        r"\{[\s\S]*\}",  # JSON对象
        r"\[[\s\S]*\]",  # JSON数组
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    return None


def format_tool_result(result: Any, max_length: int = 2000) -> str:
    """
    格式化工具结果 / Format tool result
    
    Args:
        result: 工具执行结果 / Tool execution result
        max_length: 最大长度 / Maximum length
        
    Returns:
        str: 格式化的结果 / Formatted result
    """
    if result is None:
        return "无结果 / No result"
    
    if isinstance(result, str):
        return truncate_text(result, max_length)
    
    if isinstance(result, (dict, list)):
        try:
            formatted = json.dumps(result, ensure_ascii=False, indent=2)
            return truncate_text(formatted, max_length)
        except (TypeError, ValueError):
            return truncate_text(str(result), max_length)
    
    return truncate_text(str(result), max_length)


def generate_request_id() -> str:
    """
    生成请求ID / Generate request ID
    
    Returns:
        str: 唯一的请求ID / Unique request ID
    """
    import uuid
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    random_part = uuid.uuid4().hex[:8]
    return f"req_{timestamp}_{random_part}"


def parse_tool_call_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    从模型响应中解析工具调用 / Parse tool call from model response
    
    支持多种格式 / Supports multiple formats
    
    Args:
        response: 模型响应 / Model response
        
    Returns:
        Optional[Dict]: 工具调用信息 / Tool call information
    """
    # 尝试解析JSON格式 / Try to parse JSON format
    json_data = extract_json_from_text(response)
    if json_data and isinstance(json_data, dict):
        if "tool_name" in json_data or "function" in json_data or "name" in json_data:
            return json_data
    
    # 尝试解析特定格式 / Try to parse specific formats
    # 格式1: Action: tool_name, Action Input: {...}
    action_pattern = r"Action:\s*(\w+)\s*\nAction Input:\s*(.*?)(?:\n|$)"
    match = re.search(action_pattern, response, re.DOTALL)
    if match:
        tool_name = match.group(1).strip()
        action_input = match.group(2).strip()
        try:
            args = json.loads(action_input)
        except json.JSONDecodeError:
            args = {"input": action_input}
        return {"tool_name": tool_name, "arguments": args}
    
    return None


def safe_dict_get(d: Dict[str, Any], *keys, default: Any = None) -> Any:
    """
    安全地获取嵌套字典的值 / Safely get value from nested dictionary
    
    Args:
        d: 字典 / Dictionary
        *keys: 键路径 / Key path
        default: 默认值 / Default value
        
    Returns:
        Any: 获取的值或默认值 / Retrieved value or default
    """
    result = d
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, default)
        else:
            return default
    return result


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归合并字典 / Recursively merge dictionaries
    
    Args:
        base: 基础字典 / Base dictionary
        override: 覆盖字典 / Override dictionary
        
    Returns:
        Dict: 合并后的字典 / Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def estimate_tokens(text: str) -> int:
    """
    估算文本的token数量 / Estimate token count of text
    
    简单估算，实际token数量可能有所不同
    Simple estimation, actual token count may vary
    
    Args:
        text: 文本 / Text
        
    Returns:
        int: 估算的token数量 / Estimated token count
    """
    # 英文约4字符一个token，中文约2字符一个token
    # English ~4 chars per token, Chinese ~2 chars per token
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    
    return (chinese_chars // 2) + (other_chars // 4)
