# ==============================================================================
# 搜索工具 / Search Tool
# ==============================================================================
# 提供网络搜索功能，主搜索引擎为Tavily，备用为DuckDuckGo
# Provides web search functionality, primary engine is Tavily, fallback is DuckDuckGo
#
# 返回字段规范 / Return Field Specification:
# - title: 搜索结果标题 / Search result title
# - url: 结果链接 / Result URL
# - body: 内容摘要 / Content summary
# - button: 进一步搜索跳转建议 / Suggested further search queries
#
# LLM处理后保留字段 / Fields retained after LLM processing:
# - title: 标题
# - url: 链接
# - abstract: 摘要
# - key_content: 与任务相关的关键内容（包括button、相关文案、资源url等）
# ==============================================================================

import json
from typing import Any, Dict, List, Optional

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
    
    执行网络搜索并返回结构化结果，主搜索引擎为Tavily，备用为DuckDuckGo
    Performs web search and returns structured results, primary engine is Tavily, fallback is DuckDuckGo
    
    返回字段 / Return Fields:
    - title: 搜索结果标题 / Search result title
    - url: 结果链接 / Result URL  
    - body: 内容摘要 / Content summary
    - button: 进一步搜索建议 / Suggested further search queries
    
    LLM处理后应提取 / LLM should extract:
    - title: 标题
    - url: 链接
    - abstract: 精炼摘要
    - key_content: 任务相关关键内容（button、相关资源url等）
    """
    
    name: str = "web_search"
    description: str = "搜索网络获取信息，返回结构化结果（title/url/body/button）。LLM处理后保留title/url/abstract/key_content。参数：query（搜索查询），max_results（最大结果数，默认5）/ Search the web for information, returns structured results (title/url/body/button). After LLM processing, retain title/url/abstract/key_content. Parameters: query (search query), max_results (maximum results, default 5)"
    description_zh: str = "搜索网络获取信息，返回结构化结果（title/url/body/button）。LLM处理后保留title/url/abstract/key_content。参数：query（搜索查询），max_results（最大结果数，默认5）"
    description_en: str = "Search the web for information, returns structured results (title/url/body/button). After LLM processing, retain title/url/abstract/key_content. Parameters: query (search query), max_results (maximum results, default 5)"
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
        
        搜索策略 / Search strategy:
        1. 优先使用Tavily搜索（需要API密钥）/ Primary: Tavily search (requires API key)
        2. 如果Tavily失败，自动回退到DuckDuckGo / Fallback: DuckDuckGo if Tavily fails
        
        Args:
            query: 搜索查询 / Search query
            max_results: 最大结果数 / Maximum results
            
        Returns:
            str: JSON格式的搜索结果 / Search results in JSON format
        """
        if not self.enabled:
            return json.dumps({
                "error": "搜索工具未启用 / Search tool not enabled",
                "hint": "请在config.yaml中配置search_tool.enabled=true / Please set search_tool.enabled=true in config.yaml"
            }, ensure_ascii=False)
        
        # 尝试使用Tavily搜索 / Try Tavily search
        if self.api_key:
            tavily_result = self._search_with_tavily(query, max_results)
            if tavily_result:
                return tavily_result
            self.logger.warning("Tavily搜索失败，回退到DuckDuckGo / Tavily search failed, falling back to DuckDuckGo")
        else:
            self.logger.info("Tavily API密钥未配置，使用DuckDuckGo / Tavily API key not configured, using DuckDuckGo")
        
        # 回退到DuckDuckGo搜索 / Fallback to DuckDuckGo search
        return self._search_with_duckduckgo(query, max_results)
    
    def _format_results(self, query: str, results: List[Dict], engine: str) -> str:
        """
        格式化搜索结果为统一结构 / Format search results to unified structure
        
        Args:
            query: 搜索查询 / Search query
            results: 原始搜索结果 / Raw search results
            engine: 搜索引擎名称 / Search engine name
            
        Returns:
            str: JSON格式的结构化结果 / Structured results in JSON format
        """
        formatted = {
            "query": query,
            "engine": engine,
            "total_results": len(results),
            "results": results,
            "llm_instruction": "处理搜索结果时，请提取并保留以下字段：title（标题）、url（链接）、abstract（精炼摘要）、key_content（与任务相关的关键内容，包括进一步搜索的button建议、相关资源url等）/ When processing search results, extract and retain: title, url, abstract (refined summary), key_content (task-relevant key content including suggested search buttons, related resource urls, etc.)"
        }
        return json.dumps(formatted, ensure_ascii=False, indent=2)
    
    def _search_with_tavily(self, query: str, max_results: int) -> Optional[str]:
        """
        使用Tavily执行搜索 / Execute search with Tavily
        
        Args:
            query: 搜索查询 / Search query
            max_results: 最大结果数 / Maximum results
            
        Returns:
            Optional[str]: JSON格式搜索结果，失败返回None / Search results in JSON, None if failed
        """
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=self.api_key)
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="basic"
            )
            
            raw_results = response.get("results", [])
            if not raw_results:
                return json.dumps({
                    "query": query,
                    "engine": "tavily",
                    "total_results": 0,
                    "results": [],
                    "message": f"未找到关于 '{query}' 的搜索结果 / No results found for '{query}'"
                }, ensure_ascii=False)
            
            # 转换为统一格式 / Convert to unified format
            results = []
            for item in raw_results:
                result = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "body": item.get("content", "")[:500],
                    "button": self._generate_related_queries(query, item.get("title", ""))
                }
                results.append(result)
            
            return self._format_results(query, results, "tavily")
            
        except ImportError:
            self.logger.warning("Tavily库未安装 / Tavily library not installed")
            return None
        except Exception as e:
            self.logger.error(f"Tavily搜索出错 / Tavily search error: {str(e)}")
            return None
    
    def _search_with_duckduckgo(self, query: str, max_results: int) -> str:
        """
        使用DuckDuckGo执行搜索 / Execute search with DuckDuckGo
        
        Args:
            query: 搜索查询 / Search query
            max_results: 最大结果数 / Maximum results
            
        Returns:
            str: JSON格式搜索结果 / Search results in JSON format
        """
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
            
            if not raw_results:
                return json.dumps({
                    "query": query,
                    "engine": "duckduckgo",
                    "total_results": 0,
                    "results": [],
                    "message": f"未找到关于 '{query}' 的搜索结果 / No results found for '{query}'"
                }, ensure_ascii=False)
            
            # 转换为统一格式 / Convert to unified format
            results = []
            for item in raw_results:
                result = {
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "body": item.get("body", "")[:500],
                    "button": self._generate_related_queries(query, item.get("title", ""))
                }
                results.append(result)
            
            return self._format_results(query, results, "duckduckgo")
            
        except ImportError:
            return json.dumps({
                "error": "搜索库未安装 / Search library not installed",
                "hint": "请运行: pip install duckduckgo-search / Please run: pip install duckduckgo-search"
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"DuckDuckGo搜索出错 / DuckDuckGo search error: {str(e)}"
            }, ensure_ascii=False)
    
    def _generate_related_queries(self, original_query: str, title: str) -> List[str]:
        """
        生成相关搜索建议 / Generate related search suggestions
        
        基于原始查询和结果标题生成进一步搜索的button建议
        Generate further search button suggestions based on original query and result title
        
        Args:
            original_query: 原始搜索查询 / Original search query
            title: 结果标题 / Result title
            
        Returns:
            List[str]: 相关搜索建议列表 / List of related search suggestions
        """
        buttons = []
        
        # 基于标题提取关键词生成建议 / Generate suggestions based on title keywords
        if title:
            # 提取标题中的关键部分 / Extract key parts from title
            keywords = title.split()[:3]
            if keywords:
                buttons.append(f"{original_query} {keywords[0]}")
        
        # 添加常见的深入搜索模式 / Add common deep search patterns
        buttons.extend([
            f"{original_query} 详细介绍",
            f"{original_query} 最新",
            f"{original_query} 教程"
        ])
        
        return buttons[:3]  # 限制返回3个建议 / Limit to 3 suggestions
