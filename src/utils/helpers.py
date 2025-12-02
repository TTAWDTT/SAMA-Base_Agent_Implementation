# ==============================================================================
# 工具函数模块 / Utility Functions Module
# ==============================================================================
# 提供各种通用工具函数
# Provides various utility functions
# ==============================================================================

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


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
        # 非JSON格式，直接返回原结果 / Not JSON format, return as-is
        return raw_result
    
    # 检查是否为搜索结果格式 / Check if it's search result format
    if not isinstance(data, dict) or "results" not in data:
        return raw_result
    
    # 精炼搜索结果 / Refine search results
    refined = {
        "query": data.get("query", ""),
        "engine": data.get("engine", ""),
        "total_results": data.get("total_results", 0),
        "refined_results": []
    }
    
    for item in data.get("results", []):
        # 从body提取精炼摘要（取前200字符作为abstract）
        # Extract refined abstract from body (first 200 chars)
        body = item.get("body", "")
        abstract = body[:200].strip()
        if len(body) > 200:
            abstract += "..."
        
        # 构建key_content：包含button建议和其他关键信息
        # Build key_content: includes button suggestions and other key info
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
        # 检查搜索结果的特征字段 / Check for search result characteristic fields
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
