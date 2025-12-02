# ==============================================================================
# 工具函数模块 / Utility Functions Module
# ==============================================================================
# 提供各种通用工具函数
# Provides various utility functions
# ==============================================================================

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional


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


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    从文本中提取JSON / Extract JSON from text
    
    Args:
        text: 包含JSON的文本 / Text containing JSON
        
    Returns:
        Optional[Dict]: 解析后的JSON / Parsed JSON, or None if failed
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```",
        r"\{[\s\S]*\}",
        r"\[[\s\S]*\]",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    return None


def estimate_tokens(text: str) -> int:
    """
    估算文本的token数量 / Estimate token count of text
    
    Args:
        text: 文本 / Text
        
    Returns:
        int: 估算的token数量 / Estimated token count
    """
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    return (chinese_chars // 2) + (other_chars // 4)
