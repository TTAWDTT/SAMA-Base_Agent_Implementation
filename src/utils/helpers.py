# ==============================================================================
# 工具函数模块
# ==============================================================================
# 提供各种通用工具函数
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


def _sanitize_value(value: Any, max_length: int, max_items: int, depth: int, max_depth: int) -> Any:
    if depth >= max_depth:
        return truncate_text(str(value), max_length)
    if isinstance(value, str):
        return truncate_text(value, max_length)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        sanitized = {}
        for idx, (key, val) in enumerate(value.items()):
            if idx >= max_items:
                sanitized["..."] = f"({len(value) - max_items} more)"
                break
            sanitized[str(key)] = _sanitize_value(val, max_length, max_items, depth + 1, max_depth)
        return sanitized
    if isinstance(value, (list, tuple)):
        sanitized_list = []
        for idx, item in enumerate(value):
            if idx >= max_items:
                sanitized_list.append(f"... ({len(value) - max_items} more)")
                break
            sanitized_list.append(_sanitize_value(item, max_length, max_items, depth + 1, max_depth))
        return sanitized_list
    return truncate_text(str(value), max_length)


def sanitize_tool_arguments(
    arguments: Optional[Dict[str, Any]],
    max_value_length: int = 240,
    max_items: int = 16,
    max_depth: int = 3
) -> Dict[str, Any]:
    """
    清理工具参数，避免过长内容进入上下文 / Sanitize tool arguments for context
    """
    if not arguments:
        return {}
    return _sanitize_value(arguments, max_value_length, max_items, 0, max_depth)


def format_tool_trace(
    tool_name: str,
    arguments: Optional[Dict[str, Any]],
    result: Any,
    call_id: Optional[str] = None,
    output_override: Optional[Any] = None,
    max_output_length: int = 2000
) -> str:
    """
    生成结构化工具轨迹 / Build structured tool trace payload
    """
    status = getattr(result, "status", None)
    status_value = getattr(status, "value", None) or (str(status) if status else "unknown")
    error_message = getattr(result, "error_message", None)
    execution_time = getattr(result, "execution_time", None)
    output_value = None if error_message else (output_override if output_override is not None else getattr(result, "output", None))

    payload = {
        "tool": tool_name,
        "status": status_value,
        "call_id": call_id,
        "arguments": sanitize_tool_arguments(arguments),
        "output": None if output_value is None else format_tool_result(output_value, max_output_length),
        "error": error_message,
        "execution_time": execution_time,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def refine_search_result(raw_result: str) -> str:
    """
    精炼搜索结果，将原始结果转换为上下文友好的格式 / Refine search result to context-friendly format
    
    输入格式（工具返回）/ Input format (from tool):
    - title: 搜索结果标题
    - url: 结果链接
    - body: 内容摘要
    - button: 进一步搜索建议
    
    输出格式（存入上下文）/ Output format (for context):
    - title: 标题
    - url: 链接
    - abstract: 精炼摘要（从body提取核心信息）
    - key_content: 任务相关关键内容（button、资源url等）
    
    Args:
        raw_result: 工具返回的原始JSON结果 / Raw JSON result from tool
        
    Returns:
        str: 精炼后的JSON结果 / Refined JSON result for context
    """
    try:
        data = json.loads(raw_result)
    except (json.JSONDecodeError, TypeError):
        # 非JSON格式，直接返回原结果
        return raw_result
    
    # 检查是否为搜索结果格式
    if not isinstance(data, dict) or "results" not in data:
        return raw_result
    
    # 精炼搜索结果
    refined = {
        "query": data.get("query", ""),
        "engine": data.get("engine", ""),
        "total_results": data.get("total_results", 0),
        "refined_results": []
    }
    
    for item in data.get("results", []):
        # 从body提取精炼摘要（取前200字符作为abstract）
        body = item.get("body", "")
        abstract = body[:200].strip()
        if len(body) > 200:
            abstract += "..."
        
        # 构建key_content：包含button建议和其他关键信息
        key_content = {
            "further_search": item.get("button", []),
            "source_url": item.get("url", "")
        }
        
        refined_item = {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "abstract": abstract,
            "key_content": key_content
        }
        refined["refined_results"].append(refined_item)
    
    return json.dumps(refined, ensure_ascii=False, indent=2)


def is_search_result(result: str) -> bool:
    """
    检查结果是否为搜索工具的结果 / Check if result is from search tool
    
    Args:
        result: 工具执行结果 / Tool execution result
        
    Returns:
        bool: 是否为搜索结果 / Whether it's a search result
    """
    try:
        data = json.loads(result)
        # 检查搜索结果的特征字段
        return (
            isinstance(data, dict) and 
            "results" in data and 
            "query" in data and
            "engine" in data
        )
    except (json.JSONDecodeError, TypeError):
        return False


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


def redact_sensitive_text(text: str) -> str:
    """
    脱敏敏感内容
    """
    if not text:
        return text
    patterns = [
        (r'(?i)(api[_-]?key\s*[:=]\s*)([^\s"\']+)', r"\1***"),
        (r'(?i)(token\s*[:=]\s*)([^\s"\']+)', r"\1***"),
        (r'(?i)(secret\s*[:=]\s*)([^\s"\']+)', r"\1***"),
        (r'(?i)(password\s*[:=]\s*)([^\s"\']+)', r"\1***"),
        (r'(sk-[A-Za-z0-9]{16,})', "***"),
        (r'([A-Za-z0-9_\-]{24,})', "***"),
    ]
    result = text
    for pattern, repl in patterns:
        result = re.sub(pattern, repl, result)
    return result


def redact_sensitive_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    脱敏字典内容
    """
    def _redact(value: Any) -> Any:
        if isinstance(value, str):
            return redact_sensitive_text(value)
        if isinstance(value, dict):
            return {k: _redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_redact(v) for v in value]
        return value

    return _redact(payload)
