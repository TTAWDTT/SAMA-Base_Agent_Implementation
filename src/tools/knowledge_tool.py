# ==============================================================================
# 知识库检索工具
# ==============================================================================

from __future__ import annotations

from typing import Optional

from pydantic import Field

from src.core.config import get_config
from src.runtime.knowledge_base import search
from src.tools.base import BaseTool, ToolInput


class KnowledgeSearchInput(ToolInput):
    query: str = Field(description="检索问题")
    top_k: Optional[int] = Field(default=None, description="返回结果数量")


class KnowledgeSearchTool(BaseTool):
    name = "knowledge_search"
    description = "本地知识库检索工具"
    description_zh = "本地知识库检索工具"
    description_en = "Local knowledge base search tool"
    required_permissions = ["knowledge"]
    input_schema = KnowledgeSearchInput

    def _run(self, query: str, top_k: Optional[int] = None) -> str:
        config = get_config().knowledge_base
        if not config.enabled:
            return "知识库已关闭。"
        result = search(query, config=config, top_k=top_k)
        return self._format_result(result)

    def _format_result(self, result: dict) -> str:
        items = result.get("results", [])
        if not items:
            return "未找到匹配内容。"
        lines = ["检索结果："]
        for idx, item in enumerate(items, 1):
            lines.append(f"{idx}. {item.get('path')}#chunk={item.get('chunk_id')} (score={item.get('score')})")
            lines.append(f"   {item.get('snippet')}")
        return "\n".join(lines)
