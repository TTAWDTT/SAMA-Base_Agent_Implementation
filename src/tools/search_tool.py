import json
from typing import Any, Dict, List, Optional

from pydantic import Field

from src.core.config import get_config
from src.tools.base import BaseTool, ToolInput


class SearchInput(ToolInput):
    """搜索输入"""
    query: str = Field(description="搜索查询")
    max_results: int = Field(default=5, description="最大结果数")


class WebSearchTool(BaseTool):
    """
    网络搜索工具。

    执行网络搜索并返回结构化结果，支持Tavily与DuckDuckGo回退。
    """
    
    name: str = "web_search"
    subprocess_safe: bool = True
    
    description: str = """网络搜索工具，执行网络搜索并返回结构化结果。

## 使用说明

- **query**（必填）：搜索查询
- **max_results**（可选）：最大结果数，默认5
"""
    
    description_zh: str = description
    
    input_schema = SearchInput
    
    def __init__(self):
        """初始化"""
        super().__init__()
        config = get_config()
        self.enabled = config.tools.search_tool.enabled
        self.api_key = config.tools.search_tool.api_key
        self.engine = config.tools.search_tool.engine
        self._last_tavily_error = None
    
    def _run(self, query: str, max_results: int = 5) -> str:
        """
        执行搜索

        搜索策略：
        1. 优先使用Tavily搜索（需要API密钥）
        2. Tavily失败时回退到DuckDuckGo

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            str: JSON格式的搜索结果
        """
        if not self.enabled:
            return json.dumps({
                "error": "搜索工具未启用",
                "hint": "请在 config.yaml 中配置 search_tool.enabled=true"
            }, ensure_ascii=False)
        
        self._last_tavily_error = None
        engine = (self.engine or "auto").strip().lower()

        if engine in ("duckduckgo", "ddg"):
            return self._search_with_duckduckgo(query, max_results, None)

        if engine in ("tavily", "tavily_only"):
            if not self.api_key:
                return json.dumps({
                    "error": "Tavily API密钥未配置",
                    "hint": "请在 config.yaml 中配置 search_tool.api_key 或切换 engine=duckduckgo"
                }, ensure_ascii=False)
            tavily_result = self._search_with_tavily(query, max_results)
            if tavily_result:
                return tavily_result
            return json.dumps({
                "error": "Tavily搜索失败",
                "detail": self._last_tavily_error or "未知错误",
                "hint": "请检查 API 密钥或切换 engine=duckduckgo"
            }, ensure_ascii=False)

        if self.api_key:
            tavily_result = self._search_with_tavily(query, max_results)
            if tavily_result:
                return tavily_result
            self.logger.warning("Tavily搜索失败，回退到DuckDuckGo")
        else:
            self.logger.info("Tavily API密钥未配置，使用DuckDuckGo")
            self._last_tavily_error = "Tavily API密钥缺失或为空"
        
        return self._search_with_duckduckgo(query, max_results, self._last_tavily_error)
    
    def _format_results(self, query: str, results: List[Dict], engine: str, notice: Optional[str] = None) -> str:
        """
        格式化搜索结果为统一结构

        Args:
            query: 搜索查询
            results: 原始搜索结果
            engine: 搜索引擎名称

        Returns:
            str: JSON格式的结构化结果
        """
        formatted = {
            "query": query,
            "engine": engine,
            "total_results": len(results),
            "results": results,
            "llm_instruction": "处理搜索结果时，请提取并保留以下字段：title（标题）、url（链接）、abstract（精炼摘要）、key_content（与任务相关的关键内容，包括进一步搜索的按钮建议、相关资源链接等）"
        }
        if notice:
            formatted["notice"] = notice
        return json.dumps(formatted, ensure_ascii=False, indent=2)
    
    def _search_with_tavily(self, query: str, max_results: int) -> Optional[str]:
        """
        使用Tavily执行搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            Optional[str]: JSON格式搜索结果，失败返回 None
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
                    "message": f"未找到关于 '{query}' 的搜索结果"
                }, ensure_ascii=False)
            
            # 转换为统一格式
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
            self.logger.warning("Tavily库未安装")
            self._last_tavily_error = "Tavily 库未安装"
            return None
        except Exception as e:
            self.logger.error(f"Tavily搜索出错: {str(e)}")
            self._last_tavily_error = f"Tavily 搜索出错: {str(e)}"
            return None
    
    def _fetch_duckduckgo_results(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            from duckduckgo_search import DDGS
            client = DDGS()
            if hasattr(client, "__enter__"):
                with client as ddgs_client:
                    return list(ddgs_client.text(query, max_results=max_results))
            return list(client.text(query, max_results=max_results))
        except ImportError:
            from duckduckgo_search import ddgs as ddgs_factory
            try:
                client = ddgs_factory()
            except TypeError:
                client = ddgs_factory
            if hasattr(client, "__enter__"):
                with client as ddgs_client:
                    return list(ddgs_client.text(query, max_results=max_results))
            if hasattr(client, "text"):
                return list(client.text(query, max_results=max_results))
            return list(client(query, max_results=max_results))

    def _search_with_duckduckgo(self, query: str, max_results: int, tavily_error: Optional[str] = None) -> str:
        """
        使用DuckDuckGo执行搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数

        Returns:
            str: JSON格式搜索结果
        """
        try:
            raw_results = self._fetch_duckduckgo_results(query, max_results)
            if not raw_results:
                return json.dumps({
                    "query": query,
                    "engine": "duckduckgo",
                    "total_results": 0,
                    "results": [],
                    "message": f"未找到关于 '{query}' 的搜索结果"
                }, ensure_ascii=False)
            
            # 转换为统一格式
            results = []
            for item in raw_results:
                result = {
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "body": item.get("body", "")[:500],
                    "button": self._generate_related_queries(query, item.get("title", ""))
                }
                results.append(result)
            
            notice = f"已回退到 DuckDuckGo: {tavily_error}" if tavily_error else None
            return self._format_results(query, results, "duckduckgo", notice)
            
        except ImportError:
            payload = {
                "error": "搜索库未安装",
                "hint": "请运行: pip install duckduckgo-search"
            }
            if tavily_error:
                payload["tavily_error"] = tavily_error
            return json.dumps(payload, ensure_ascii=False)
        except Exception as e:
            payload = {
                "error": f"DuckDuckGo搜索出错: {str(e)}"
            }
            if tavily_error:
                payload["tavily_error"] = tavily_error
            return json.dumps(payload, ensure_ascii=False)
    
    def _generate_related_queries(self, original_query: str, title: str) -> List[str]:
        """
        生成相关搜索建议

        基于原始查询和结果标题生成进一步搜索的按钮建议

        Args:
            original_query: 原始搜索查询
            title: 结果标题

        Returns:
            List[str]: 相关搜索建议列表
        """
        buttons = []
        
        # 基于标题提取关键词生成建议
        if title:
            # 提取标题中的关键部分
            keywords = title.split()[:3]
            if keywords:
                buttons.append(f"{original_query} {keywords[0]}")
        
        # 添加常见的深入搜索模式
        buttons.extend([
            f"{original_query} 详细介绍",
            f"{original_query} 最新",
            f"{original_query} 教程"
        ])
        
        return buttons[:3]  # 限制返回3个建议
