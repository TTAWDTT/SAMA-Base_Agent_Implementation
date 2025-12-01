# ==============================================================================
# 搜索工具 / Search Tool
# ==============================================================================
# 提供网络搜索功能（需要配置API）
# Provides web search functionality (requires API configuration)
# ==============================================================================

from typing import Any, List, Optional

from pydantic import Field

from src.core.config import get_config
from src.tools.base import BaseTool, ToolInput


class SearchInput(ToolInput):
    """搜索输入 / Search Input"""
    query: str = Field(description="搜索查询 / Search query")
    max_results: int = Field(default=5, description="最大结果数 / Maximum results")


class WebSearchTool(BaseTool):
    """
    网络搜索工具 / Web Search Tool
    
    执行网络搜索并返回结果
    Performs web search and returns results
    
    注意：此工具需要配置搜索API
    Note: This tool requires search API configuration
    """
    
    name: str = "web_search"
    description: str = "搜索网络获取信息。参数：query（搜索查询），max_results（最大结果数，默认5）/ Search the web for information. Parameters: query (search query), max_results (maximum results, default 5)"
    description_zh: str = "搜索网络获取信息。参数：query（搜索查询），max_results（最大结果数，默认5）"
    description_en: str = "Search the web for information. Parameters: query (search query), max_results (maximum results, default 5)"
    input_schema = SearchInput
    
    def __init__(self):
        """初始化 / Initialize"""
        super().__init__()
        config = get_config()
        self.enabled = config.tools.search_tool.enabled
        self.api_key = config.tools.search_tool.api_key
        self.engine = config.tools.search_tool.engine
    
    def _run(self, query: str, max_results: int = 5) -> str:
        """
        执行搜索 / Execute search
        
        Args:
            query: 搜索查询 / Search query
            max_results: 最大结果数 / Maximum results
            
        Returns:
            str: 搜索结果 / Search results
        """
        if not self.enabled:
            return "搜索工具未启用。请在config.yaml中配置search_tool.enabled=true并提供API密钥。/ Search tool is not enabled. Please configure search_tool.enabled=true in config.yaml and provide API key."
        
        if not self.api_key:
            return "搜索API密钥未配置。请在config.yaml中配置search_tool.api_key。/ Search API key not configured. Please configure search_tool.api_key in config.yaml."
        
        # 这里是搜索实现的占位符
        # Here is a placeholder for search implementation
        # 实际使用时需要集成具体的搜索API（如Google、Bing、DuckDuckGo等）
        # In actual use, you need to integrate specific search APIs (such as Google, Bing, DuckDuckGo, etc.)
        
        return f"搜索功能演示 / Search function demo:\n查询 / Query: {query}\n\n此功能需要配置搜索API才能使用。/ This feature requires search API configuration to use.\n\n支持的搜索引擎 / Supported search engines:\n- Google Custom Search\n- Bing Search API\n- DuckDuckGo (免费 / free)"


class DuckDuckGoSearchTool(BaseTool):
    """
    DuckDuckGo搜索工具 / DuckDuckGo Search Tool
    
    使用DuckDuckGo进行网络搜索（无需API密钥）
    Uses DuckDuckGo for web search (no API key required)
    """
    
    name: str = "duckduckgo_search"
    description: str = "使用DuckDuckGo搜索网络。参数：query（搜索查询），max_results（最大结果数，默认5）/ Search the web using DuckDuckGo. Parameters: query (search query), max_results (maximum results, default 5)"
    description_zh: str = "使用DuckDuckGo搜索网络。参数：query（搜索查询），max_results（最大结果数，默认5）"
    description_en: str = "Search the web using DuckDuckGo. Parameters: query (search query), max_results (maximum results, default 5)"
    input_schema = SearchInput
    
    def _run(self, query: str, max_results: int = 5) -> str:
        """
        执行DuckDuckGo搜索 / Execute DuckDuckGo search
        
        Args:
            query: 搜索查询 / Search query
            max_results: 最大结果数 / Maximum results
            
        Returns:
            str: 搜索结果 / Search results
        """
        try:
            # 尝试导入duckduckgo_search
            # Try to import duckduckgo_search
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            
            if not results:
                return f"未找到关于 '{query}' 的搜索结果 / No search results found for '{query}'"
            
            output = f"搜索结果 / Search Results for '{query}':\n\n"
            for i, result in enumerate(results, 1):
                output += f"{i}. {result.get('title', 'No title')}\n"
                output += f"   链接 / URL: {result.get('href', 'No URL')}\n"
                output += f"   摘要 / Summary: {result.get('body', 'No summary')[:200]}...\n\n"
            
            return output
            
        except ImportError:
            return "DuckDuckGo搜索库未安装。请运行: pip install duckduckgo-search / DuckDuckGo search library not installed. Please run: pip install duckduckgo-search"
        except Exception as e:
            return f"搜索出错 / Search error: {str(e)}"
