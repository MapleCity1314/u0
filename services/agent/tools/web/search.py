"""
网络搜索工具

提供强大的网络搜索能力，支持多个搜索引擎和多种搜索模式。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote_plus

from services.agent.tools.base import (
    Tool,
    ToolCategory,
    ToolContext,
    ToolParameter,
    tool,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Search Provider Abstraction
# ============================================================================


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    url: str
    snippet: str
    source: Optional[str] = None
    published_date: Optional[str] = None
    score: Optional[float] = None
    raw_content: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
        }
        if self.source:
            result["source"] = self.source
        if self.published_date:
            result["published_date"] = self.published_date
        if self.score is not None:
            result["score"] = self.score
        return result


class SearchProvider(ABC):
    """搜索提供商基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """提供商名称"""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs,
    ) -> list[SearchResult]:
        """执行搜索"""
        pass


class TavilySearchProvider(SearchProvider):
    """Tavily 搜索提供商（推荐用于 AI 应用）"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")

    @property
    def name(self) -> str:
        return "tavily"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "basic",
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
        include_answer: bool = True,
        include_raw_content: bool = False,
        **kwargs,
    ) -> list[SearchResult]:
        if not self.api_key:
            raise ValueError("Tavily API key is required")

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=self.api_key)

            response = client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
                include_domains=include_domains or [],
                exclude_domains=exclude_domains or [],
                include_answer=include_answer,
                include_raw_content=include_raw_content,
            )

            results = []
            for item in response.get("results", []):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        source=item.get("source"),
                        published_date=item.get("published_date"),
                        score=item.get("score"),
                        raw_content=item.get("raw_content") if include_raw_content else None,
                    )
                )

            return results

        except ImportError:
            raise ImportError("tavily-python package is required: pip install tavily-python")


class SerperSearchProvider(SearchProvider):
    """Serper 搜索提供商（Google 搜索 API）"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"

    @property
    def name(self) -> str:
        return "serper"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        country: str = "cn",
        locale: str = "zh-cn",
        **kwargs,
    ) -> list[SearchResult]:
        if not self.api_key:
            raise ValueError("Serper API key is required")

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "q": query,
                        "gl": country,
                        "hl": locale,
                        "num": max_results,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("organic", [])[:max_results]:
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        source=item.get("source"),
                        published_date=item.get("date"),
                    )
                )

            return results

        except ImportError:
            raise ImportError("httpx package is required: pip install httpx")


class DuckDuckGoSearchProvider(SearchProvider):
    """DuckDuckGo 搜索提供商（免费，无需 API Key）"""

    @property
    def name(self) -> str:
        return "duckduckgo"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        region: str = "cn-zh",
        **kwargs,
    ) -> list[SearchResult]:
        try:
            from duckduckgo_search import DDGS

            # DuckDuckGo 搜索是同步的，在线程池中运行
            loop = asyncio.get_event_loop()
            results_data = await loop.run_in_executor(
                None,
                lambda: list(DDGS().text(query, region=region, max_results=max_results)),
            )

            results = []
            for item in results_data:
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("href", ""),
                        snippet=item.get("body", ""),
                        source=item.get("source"),
                    )
                )

            return results

        except ImportError:
            raise ImportError(
                "duckduckgo-search package is required: pip install duckduckgo-search"
            )


class BingSearchProvider(SearchProvider):
    """Bing 搜索提供商"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BING_API_KEY")
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"

    @property
    def name(self) -> str:
        return "bing"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        market: str = "zh-CN",
        **kwargs,
    ) -> list[SearchResult]:
        if not self.api_key:
            raise ValueError("Bing API key is required")

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    headers={"Ocp-Apim-Subscription-Key": self.api_key},
                    params={
                        "q": query,
                        "count": max_results,
                        "mkt": market,
                        "responseFilter": "Webpages",
                    },
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("webPages", {}).get("value", [])[:max_results]:
                results.append(
                    SearchResult(
                        title=item.get("name", ""),
                        url=item.get("url", ""),
                        snippet=item.get("snippet", ""),
                        published_date=item.get("dateLastCrawled"),
                    )
                )

            return results

        except ImportError:
            raise ImportError("httpx package is required: pip install httpx")


# ============================================================================
# Search Provider Factory
# ============================================================================


def get_search_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> SearchProvider:
    """
    获取搜索提供商实例

    Args:
        provider_name: 提供商名称，默认从环境变量获取
        api_key: API Key，默认从环境变量获取

    Returns:
        搜索提供商实例
    """
    if provider_name is None:
        provider_name = os.getenv("AGENT_SEARCH_PROVIDER", "duckduckgo")

    provider_name = provider_name.lower()

    if provider_name == "tavily":
        return TavilySearchProvider(api_key)
    elif provider_name == "serper":
        return SerperSearchProvider(api_key)
    elif provider_name == "duckduckgo":
        return DuckDuckGoSearchProvider()
    elif provider_name == "bing":
        return BingSearchProvider(api_key)
    else:
        # 默认使用 DuckDuckGo（免费）
        logger.warning(f"Unknown search provider: {provider_name}, falling back to DuckDuckGo")
        return DuckDuckGoSearchProvider()


# ============================================================================
# Search Tools
# ============================================================================


@tool(
    name="web_search",
    description="在互联网上搜索信息，支持搜索新闻、文章、产品、公司信息等任何公开内容",
    category=ToolCategory.WEB,
    tags=["search", "web", "internet", "research"],
)
async def web_search(
    ctx: ToolContext,
    query: str,
    max_results: int = 10,
    search_type: str = "general",
) -> str:
    """
    在互联网上搜索信息。

    Args:
        ctx: 工具执行上下文
        query: 搜索关键词或问题
        max_results: 最大返回结果数，默认 10
        search_type: 搜索类型，可选 general/news/finance，默认 general

    Returns:
        搜索结果的 JSON 字符串，包含标题、链接、摘要等
    """
    if not query:
        return json.dumps({"error": "请提供搜索关键词"}, ensure_ascii=False)

    query = query.strip()
    max_results = min(max(1, max_results), 20)

    # 根据搜索类型调整查询
    if search_type == "news":
        query = f"{query} 最新新闻"
    elif search_type == "finance":
        query = f"{query} 财经 投资"

    try:
        provider = get_search_provider()
        logger.info(f"Searching with {provider.name}: {query}")

        results = await provider.search(query, max_results=max_results)

        if not results:
            return json.dumps({
                "query": query,
                "results": [],
                "total": 0,
                "message": "未找到相关结果",
                "provider": provider.name,
            }, ensure_ascii=False)

        return json.dumps({
            "query": query,
            "results": [r.to_dict() for r in results],
            "total": len(results),
            "provider": provider.name,
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Search failed: {e}")

        # 尝试备用搜索引擎
        try:
            fallback = DuckDuckGoSearchProvider()
            results = await fallback.search(query, max_results=max_results)

            return json.dumps({
                "query": query,
                "results": [r.to_dict() for r in results],
                "total": len(results),
                "provider": fallback.name,
                "note": "使用备用搜索引擎",
                "searched_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)
        except Exception as fallback_error:
            logger.error(f"Fallback search also failed: {fallback_error}")
            return json.dumps({
                "error": f"搜索失败: {str(e)}",
                "query": query,
            }, ensure_ascii=False)


@tool(
    name="search_news",
    description="搜索最新的新闻报道和资讯",
    category=ToolCategory.WEB,
    tags=["search", "news", "realtime"],
)
async def search_news(
    ctx: ToolContext,
    query: str,
    max_results: int = 10,
    language: str = "zh",
) -> str:
    """
    搜索最新的新闻报道。

    Args:
        ctx: 工具执行上下文
        query: 搜索关键词
        max_results: 最大返回结果数，默认 10
        language: 语言，zh 中文 / en 英文，默认 zh

    Returns:
        新闻搜索结果的 JSON 字符串
    """
    if not query:
        return json.dumps({"error": "请提供搜索关键词"}, ensure_ascii=False)

    query = query.strip()
    max_results = min(max(1, max_results), 20)

    # 针对新闻的查询优化
    news_query = f"{query} 新闻 最新" if language == "zh" else f"{query} news latest"

    try:
        # 尝试使用 Tavily（针对新闻效果更好）
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            provider = TavilySearchProvider(tavily_key)
            results = await provider.search(
                news_query,
                max_results=max_results,
                search_depth="advanced",
            )
        else:
            # 回退到默认搜索
            provider = get_search_provider()
            results = await provider.search(news_query, max_results=max_results)

        if not results:
            return json.dumps({
                "query": query,
                "results": [],
                "total": 0,
                "message": "未找到相关新闻",
            }, ensure_ascii=False)

        return json.dumps({
            "query": query,
            "results": [r.to_dict() for r in results],
            "total": len(results),
            "provider": provider.name,
            "search_type": "news",
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"News search failed: {e}")
        return json.dumps({
            "error": f"新闻搜索失败: {str(e)}",
            "query": query,
        }, ensure_ascii=False)


@tool(
    name="search_finance",
    description="搜索财经信息，包括股票、基金、市场分析、投资建议等",
    category=ToolCategory.WEB,
    tags=["search", "finance", "investment", "market"],
)
async def search_finance(
    ctx: ToolContext,
    query: str,
    max_results: int = 10,
) -> str:
    """
    搜索财经信息。

    Args:
        ctx: 工具执行上下文
        query: 搜索关键词（如公司名称、股票代码、投资话题等）
        max_results: 最大返回结果数，默认 10

    Returns:
        财经搜索结果的 JSON 字符串
    """
    if not query:
        return json.dumps({"error": "请提供搜索关键词"}, ensure_ascii=False)

    query = query.strip()
    max_results = min(max(1, max_results), 20)

    # 针对财经的查询优化
    finance_query = f"{query} 财经 投资 分析"

    # 财经相关的推荐域名
    finance_domains = [
        "eastmoney.com",
        "sina.com.cn",
        "163.com",
        "qq.com",
        "10jqka.com.cn",
        "xueqiu.com",
        "caixin.com",
        "cls.cn",
        "wallstreetcn.com",
    ]

    try:
        # 尝试使用 Tavily 并限制域名
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            provider = TavilySearchProvider(tavily_key)
            results = await provider.search(
                finance_query,
                max_results=max_results,
                search_depth="advanced",
                include_domains=finance_domains,
            )
        else:
            provider = get_search_provider()
            results = await provider.search(finance_query, max_results=max_results)

        if not results:
            return json.dumps({
                "query": query,
                "results": [],
                "total": 0,
                "message": "未找到相关财经信息",
            }, ensure_ascii=False)

        return json.dumps({
            "query": query,
            "results": [r.to_dict() for r in results],
            "total": len(results),
            "provider": provider.name,
            "search_type": "finance",
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Finance search failed: {e}")
        return json.dumps({
            "error": f"财经搜索失败: {str(e)}",
            "query": query,
        }, ensure_ascii=False)


@tool(
    name="search_company",
    description="搜索公司信息，包括公司简介、财务数据、新闻动态等",
    category=ToolCategory.WEB,
    tags=["search", "company", "business", "research"],
)
async def search_company(
    ctx: ToolContext,
    company_name: str,
    info_type: str = "all",
) -> str:
    """
    搜索公司信息。

    Args:
        ctx: 工具执行上下文
        company_name: 公司名称或股票代码
        info_type: 信息类型，可选 all/profile/news/finance，默认 all

    Returns:
        公司信息的 JSON 字符串
    """
    if not company_name:
        return json.dumps({"error": "请提供公司名称"}, ensure_ascii=False)

    company_name = company_name.strip()

    # 根据信息类型构建查询
    if info_type == "profile":
        query = f"{company_name} 公司简介 主营业务"
    elif info_type == "news":
        query = f"{company_name} 公司新闻 最新动态"
    elif info_type == "finance":
        query = f"{company_name} 财务数据 业绩报告"
    else:
        query = f"{company_name} 公司 信息"

    try:
        provider = get_search_provider()
        results = await provider.search(query, max_results=10)

        if not results:
            return json.dumps({
                "company_name": company_name,
                "info_type": info_type,
                "results": [],
                "total": 0,
                "message": "未找到相关公司信息",
            }, ensure_ascii=False)

        return json.dumps({
            "company_name": company_name,
            "info_type": info_type,
            "results": [r.to_dict() for r in results],
            "total": len(results),
            "provider": provider.name,
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Company search failed: {e}")
        return json.dumps({
            "error": f"公司搜索失败: {str(e)}",
            "company_name": company_name,
        }, ensure_ascii=False)


@tool(
    name="search_research_report",
    description="搜索研究报告和分析文章",
    category=ToolCategory.WEB,
    tags=["search", "research", "report", "analysis"],
)
async def search_research_report(
    ctx: ToolContext,
    topic: str,
    report_type: str = "all",
    max_results: int = 10,
) -> str:
    """
    搜索研究报告和分析文章。

    Args:
        ctx: 工具执行上下文
        topic: 研究主题（如行业名称、公司名称、投资主题等）
        report_type: 报告类型，可选 all/industry/company/strategy，默认 all
        max_results: 最大返回结果数，默认 10

    Returns:
        研究报告搜索结果的 JSON 字符串
    """
    if not topic:
        return json.dumps({"error": "请提供研究主题"}, ensure_ascii=False)

    topic = topic.strip()
    max_results = min(max(1, max_results), 20)

    # 根据报告类型构建查询
    type_keywords = {
        "industry": "行业研究 行业报告",
        "company": "公司研报 深度分析",
        "strategy": "投资策略 市场展望",
        "all": "研究报告 分析",
    }

    query = f"{topic} {type_keywords.get(report_type, type_keywords['all'])}"

    # 研报相关的推荐域名
    research_domains = [
        "eastmoney.com",
        "xueqiu.com",
        "research.cicc.com",
        "gtja.com",
        "htsc.com.cn",
        "china-invs.cn",
    ]

    try:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            provider = TavilySearchProvider(tavily_key)
            results = await provider.search(
                query,
                max_results=max_results,
                search_depth="advanced",
            )
        else:
            provider = get_search_provider()
            results = await provider.search(query, max_results=max_results)

        if not results:
            return json.dumps({
                "topic": topic,
                "report_type": report_type,
                "results": [],
                "total": 0,
                "message": "未找到相关研究报告",
            }, ensure_ascii=False)

        return json.dumps({
            "topic": topic,
            "report_type": report_type,
            "results": [r.to_dict() for r in results],
            "total": len(results),
            "provider": provider.name,
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Research report search failed: {e}")
        return json.dumps({
            "error": f"研报搜索失败: {str(e)}",
            "topic": topic,
        }, ensure_ascii=False)


@tool(
    name="deep_search",
    description="深度搜索，获取更详细的搜索结果，包括原始内容提取",
    category=ToolCategory.WEB,
    tags=["search", "deep", "content", "research"],
)
async def deep_search(
    ctx: ToolContext,
    query: str,
    max_results: int = 5,
) -> str:
    """
    执行深度搜索，获取更详细的内容。

    Args:
        ctx: 工具执行上下文
        query: 搜索关键词
        max_results: 最大返回结果数，默认 5（深度搜索较慢，建议少量结果）

    Returns:
        深度搜索结果的 JSON 字符串，包含原始内容
    """
    if not query:
        return json.dumps({"error": "请提供搜索关键词"}, ensure_ascii=False)

    query = query.strip()
    max_results = min(max(1, max_results), 10)

    try:
        # 深度搜索需要 Tavily
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            return json.dumps({
                "error": "深度搜索需要 Tavily API Key",
                "suggestion": "请设置 TAVILY_API_KEY 环境变量，或使用 web_search 工具",
            }, ensure_ascii=False)

        provider = TavilySearchProvider(tavily_key)
        results = await provider.search(
            query,
            max_results=max_results,
            search_depth="advanced",
            include_raw_content=True,
            include_answer=True,
        )

        if not results:
            return json.dumps({
                "query": query,
                "results": [],
                "total": 0,
                "message": "未找到相关结果",
            }, ensure_ascii=False)

        # 包含原始内容的结果
        detailed_results = []
        for r in results:
            result_dict = r.to_dict()
            if r.raw_content:
                # 截取前 2000 字符
                result_dict["content"] = r.raw_content[:2000]
                if len(r.raw_content) > 2000:
                    result_dict["content_truncated"] = True
            detailed_results.append(result_dict)

        return json.dumps({
            "query": query,
            "results": detailed_results,
            "total": len(detailed_results),
            "provider": provider.name,
            "search_depth": "advanced",
            "searched_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Deep search failed: {e}")
        return json.dumps({
            "error": f"深度搜索失败: {str(e)}",
            "query": query,
        }, ensure_ascii=False)
