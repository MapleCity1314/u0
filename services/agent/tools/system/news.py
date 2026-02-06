"""
新闻资讯获取工具

提供财经新闻、市场快讯的获取和搜索功能。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from services.agent.tools.base import (
    Tool,
    ToolCategory,
    ToolContext,
    ToolParameter,
    tool,
)

logger = logging.getLogger(__name__)


@tool(
    name="get_news",
    description="获取最新的财经新闻和市场快讯，支持按市场和来源筛选",
    category=ToolCategory.SYSTEM,
    tags=["news", "market", "realtime"],
)
async def get_news(
    ctx: ToolContext,
    market: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    获取最新的财经新闻和市场快讯。

    Args:
        ctx: 工具执行上下文
        market: 市场筛选，可选 cn/us/hk/global，默认全部
        source: 新闻来源筛选
        limit: 返回条数限制，默认 10

    Returns:
        新闻列表的 JSON 字符串，包含标题、摘要、来源、发布时间等
    """
    limit = min(max(1, limit), 50)  # 限制在 1-50 之间

    try:
        from sqlalchemy import select, desc
        from services.news.models.news_item import NewsItem
        from services.core.database import get_async_session

        async with get_async_session() as session:
            stmt = select(NewsItem).order_by(desc(NewsItem.published_at))

            # 应用筛选条件
            if market:
                stmt = stmt.where(NewsItem.market == market.lower())
            if source:
                stmt = stmt.where(NewsItem.source == source)

            stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            news_items = result.scalars().all()

            if not news_items:
                return json.dumps({
                    "message": "暂无新闻",
                    "news": [],
                    "total": 0,
                    "market": market,
                    "source": source,
                }, ensure_ascii=False)

            news_list = []
            for item in news_items:
                news_list.append({
                    "id": item.id,
                    "title": item.title,
                    "summary": item.summary[:200] if item.summary else "",
                    "source": item.source,
                    "market": item.market,
                    "url": item.url,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "tags": item.tags if hasattr(item, "tags") else [],
                })

            return json.dumps({
                "news": news_list,
                "total": len(news_list),
                "market": market,
                "source": source,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        # 如果数据库模块未安装，尝试其他方式获取新闻
        try:
            import akshare as ak

            # 使用 akshare 获取财经新闻
            if market == "cn" or market is None:
                df = ak.stock_news_em()
                if df is not None and not df.empty:
                    df = df.head(limit)
                    news_list = []
                    for _, row in df.iterrows():
                        news_list.append({
                            "title": row.get("新闻标题", ""),
                            "summary": row.get("新闻内容", "")[:200] if row.get("新闻内容") else "",
                            "source": row.get("来源", "eastmoney"),
                            "market": "cn",
                            "url": row.get("新闻链接", ""),
                            "published_at": str(row.get("发布时间", "")),
                        })

                    return json.dumps({
                        "news": news_list,
                        "total": len(news_list),
                        "market": market,
                        "source": "akshare",
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    }, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"AkShare news fetch failed: {e}")

        # 返回模拟数据
        logger.warning("News service not available, returning mock data")
        mock_news = [
            {
                "id": 1,
                "title": "央行：继续实施稳健的货币政策",
                "summary": "中国人民银行表示将继续实施稳健的货币政策，保持流动性合理充裕...",
                "source": "央行官网",
                "market": "cn",
                "url": "https://example.com/news/1",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["央行", "货币政策"],
            },
            {
                "id": 2,
                "title": "A股三大指数集体高开，创业板指涨超1%",
                "summary": "今日A股三大指数集体高开，沪指涨0.5%，深成指涨0.8%，创业板指涨1.2%...",
                "source": "财联社",
                "market": "cn",
                "url": "https://example.com/news/2",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["A股", "行情"],
            },
            {
                "id": 3,
                "title": "美联储议息会议纪要：通胀压力有所缓解",
                "summary": "美联储公布的最新议息会议纪要显示，委员会认为通胀压力正在缓解...",
                "source": "华尔街日报",
                "market": "us",
                "url": "https://example.com/news/3",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["美联储", "利率"],
            },
            {
                "id": 4,
                "title": "基金四季报陆续披露，明星基金经理调仓动向曝光",
                "summary": "随着基金四季报的陆续披露，多位明星基金经理的最新持仓情况浮出水面...",
                "source": "中国基金报",
                "market": "cn",
                "url": "https://example.com/news/4",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["基金", "调仓"],
            },
            {
                "id": 5,
                "title": "港股恒生指数高开高走，科技股领涨",
                "summary": "港股恒生指数今日高开高走，截至发稿涨1.5%，恒生科技指数涨2.3%...",
                "source": "港股通",
                "market": "hk",
                "url": "https://example.com/news/5",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["港股", "科技股"],
            },
        ]

        # 根据 market 筛选
        if market:
            mock_news = [n for n in mock_news if n["market"] == market.lower()]

        return json.dumps({
            "news": mock_news[:limit],
            "total": len(mock_news[:limit]),
            "market": market,
            "source": source,
            "note": "模拟数据（新闻服务未连接）",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to get news: {e}")
        return json.dumps({
            "error": f"获取新闻失败: {str(e)}",
            "market": market,
            "source": source,
        }, ensure_ascii=False)


@tool(
    name="search_news",
    description="搜索财经新闻，支持关键词搜索和时间范围筛选",
    category=ToolCategory.SYSTEM,
    tags=["news", "search", "market"],
)
async def search_news(
    ctx: ToolContext,
    query: str,
    market: Optional[str] = None,
    days: int = 7,
    limit: int = 10,
) -> str:
    """
    搜索财经新闻。

    Args:
        ctx: 工具执行上下文
        query: 搜索关键词
        market: 市场筛选，可选 cn/us/hk/global
        days: 搜索最近多少天的新闻，默认 7 天
        limit: 返回条数限制，默认 10

    Returns:
        搜索结果的 JSON 字符串
    """
    if not query:
        return json.dumps({"error": "请提供搜索关键词"}, ensure_ascii=False)

    query = query.strip()
    days = min(max(1, days), 90)  # 限制在 1-90 天
    limit = min(max(1, limit), 50)  # 限制在 1-50 之间

    try:
        from sqlalchemy import select, desc, or_, func
        from datetime import timedelta
        from services.news.models.news_item import NewsItem
        from services.core.database import get_async_session

        async with get_async_session() as session:
            # 计算时间范围
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

            # 构建搜索查询（使用 PostgreSQL 全文搜索或 LIKE）
            stmt = (
                select(NewsItem)
                .where(NewsItem.published_at >= cutoff_time)
                .where(
                    or_(
                        NewsItem.title.ilike(f"%{query}%"),
                        NewsItem.summary.ilike(f"%{query}%"),
                    )
                )
                .order_by(desc(NewsItem.published_at))
            )

            if market:
                stmt = stmt.where(NewsItem.market == market.lower())

            stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            news_items = result.scalars().all()

            if not news_items:
                return json.dumps({
                    "query": query,
                    "message": "未找到相关新闻",
                    "news": [],
                    "total": 0,
                    "market": market,
                    "days": days,
                }, ensure_ascii=False)

            news_list = []
            for item in news_items:
                news_list.append({
                    "id": item.id,
                    "title": item.title,
                    "summary": item.summary[:200] if item.summary else "",
                    "source": item.source,
                    "market": item.market,
                    "url": item.url,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "relevance": _calculate_relevance(query, item.title, item.summary),
                })

            # 按相关性排序
            news_list.sort(key=lambda x: x.get("relevance", 0), reverse=True)

            return json.dumps({
                "query": query,
                "news": news_list,
                "total": len(news_list),
                "market": market,
                "days": days,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        logger.warning("News search service not available, returning mock data")

        # 返回基于关键词的模拟数据
        mock_results = _generate_mock_search_results(query, market, limit)

        return json.dumps({
            "query": query,
            "news": mock_results,
            "total": len(mock_results),
            "market": market,
            "days": days,
            "note": "模拟数据（搜索服务未连接）",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to search news: {e}")
        return json.dumps({
            "error": f"搜索新闻失败: {str(e)}",
            "query": query,
        }, ensure_ascii=False)


@tool(
    name="get_market_sentiment",
    description="获取市场情绪分析，基于最新新闻和舆情数据",
    category=ToolCategory.SYSTEM,
    tags=["news", "sentiment", "analysis"],
)
async def get_market_sentiment(
    ctx: ToolContext,
    market: str = "cn",
) -> str:
    """
    获取市场情绪分析。

    Args:
        ctx: 工具执行上下文
        market: 市场，可选 cn/us/hk，默认 cn

    Returns:
        市场情绪分析的 JSON 字符串
    """
    valid_markets = ["cn", "us", "hk", "global"]
    if market.lower() not in valid_markets:
        market = "cn"

    try:
        from services.news.core import analyze_sentiment

        sentiment = await analyze_sentiment(market=market)

        return json.dumps({
            "market": market,
            "sentiment_score": sentiment.get("score"),
            "sentiment_label": sentiment.get("label"),  # bullish/bearish/neutral
            "confidence": sentiment.get("confidence"),
            "key_topics": sentiment.get("key_topics", []),
            "news_count": sentiment.get("news_count"),
            "analysis_period": sentiment.get("period"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except ImportError:
        logger.warning("Sentiment analysis service not available, returning mock data")

        # 返回模拟情绪数据
        import random
        random.seed(hash(market + datetime.now(timezone.utc).strftime("%Y-%m-%d")))

        score = random.uniform(-1, 1)
        if score > 0.3:
            label = "bullish"
        elif score < -0.3:
            label = "bearish"
        else:
            label = "neutral"

        mock_topics = {
            "cn": ["政策利好", "经济复苏", "科技创新", "消费升级", "新能源"],
            "us": ["美联储政策", "科技股走势", "通胀数据", "就业市场", "企业财报"],
            "hk": ["港股通资金", "科技股估值", "地产政策", "内地经济", "人民币汇率"],
            "global": ["地缘政治", "全球通胀", "供应链", "能源价格", "贸易关系"],
        }

        return json.dumps({
            "market": market,
            "sentiment_score": round(score, 2),
            "sentiment_label": label,
            "confidence": round(random.uniform(0.6, 0.9), 2),
            "key_topics": random.sample(mock_topics.get(market, mock_topics["cn"]), 3),
            "news_count": random.randint(50, 200),
            "analysis_period": "24h",
            "note": "模拟数据（情绪分析服务未连接）",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to get market sentiment: {e}")
        return json.dumps({
            "error": f"获取市场情绪失败: {str(e)}",
            "market": market,
        }, ensure_ascii=False)


@tool(
    name="get_news_detail",
    description="获取新闻详情，包括完整内容",
    category=ToolCategory.SYSTEM,
    tags=["news", "detail"],
)
async def get_news_detail(ctx: ToolContext, news_id: int) -> str:
    """
    获取新闻详情。

    Args:
        ctx: 工具执行上下文
        news_id: 新闻 ID

    Returns:
        新闻详情的 JSON 字符串
    """
    if not news_id:
        return json.dumps({"error": "请提供新闻 ID"}, ensure_ascii=False)

    try:
        from sqlalchemy import select
        from services.news.models.news_item import NewsItem
        from services.core.database import get_async_session

        async with get_async_session() as session:
            stmt = select(NewsItem).where(NewsItem.id == news_id)
            result = await session.execute(stmt)
            news_item = result.scalar_one_or_none()

            if not news_item:
                return json.dumps({
                    "error": f"未找到 ID 为 {news_id} 的新闻",
                    "news_id": news_id,
                }, ensure_ascii=False)

            return json.dumps({
                "id": news_item.id,
                "title": news_item.title,
                "content": news_item.content if hasattr(news_item, "content") else news_item.summary,
                "summary": news_item.summary,
                "source": news_item.source,
                "market": news_item.market,
                "url": news_item.url,
                "published_at": news_item.published_at.isoformat() if news_item.published_at else None,
                "tags": news_item.tags if hasattr(news_item, "tags") else [],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        logger.warning("News detail service not available, returning mock data")

        return json.dumps({
            "id": news_id,
            "title": "示例新闻标题",
            "content": "这是新闻的完整内容。包括更多的详细信息和分析...",
            "summary": "这是新闻摘要",
            "source": "示例来源",
            "market": "cn",
            "url": f"https://example.com/news/{news_id}",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "tags": ["示例", "新闻"],
            "note": "模拟数据（新闻详情服务未连接）",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to get news detail: {e}")
        return json.dumps({
            "error": f"获取新闻详情失败: {str(e)}",
            "news_id": news_id,
        }, ensure_ascii=False)


def _calculate_relevance(query: str, title: str, summary: str) -> float:
    """计算搜索结果的相关性分数"""
    query_lower = query.lower()
    title_lower = (title or "").lower()
    summary_lower = (summary or "").lower()

    score = 0.0

    # 标题匹配权重更高
    if query_lower in title_lower:
        score += 0.6
        # 完全匹配加分
        if query_lower == title_lower:
            score += 0.2

    # 摘要匹配
    if query_lower in summary_lower:
        score += 0.3

    # 关键词部分匹配
    query_words = query_lower.split()
    for word in query_words:
        if len(word) > 1:
            if word in title_lower:
                score += 0.1
            if word in summary_lower:
                score += 0.05

    return min(score, 1.0)


def _generate_mock_search_results(query: str, market: Optional[str], limit: int) -> list:
    """生成模拟的搜索结果"""
    templates = [
        {
            "title": f"【重磅】{query}最新动态：市场反应积极",
            "summary": f"关于{query}的最新消息显示，市场整体反应积极，分析师普遍看好后续走势...",
            "market": "cn",
        },
        {
            "title": f"{query}行业研究报告：机遇与挑战并存",
            "summary": f"本报告深入分析了{query}行业的发展现状，指出当前面临的机遇与挑战...",
            "market": "cn",
        },
        {
            "title": f"专家解读：{query}政策变化对市场的影响",
            "summary": f"针对{query}相关政策的最新变化，多位业内专家进行了深入解读...",
            "market": "cn",
        },
        {
            "title": f"外资机构看好{query}领域投资机会",
            "summary": f"多家外资机构近期发布研报，表示看好{query}领域的长期投资价值...",
            "market": "global",
        },
        {
            "title": f"{query}概念股集体走强，板块涨幅居前",
            "summary": f"受{query}利好消息刺激，相关概念股今日集体走强，板块整体涨幅超过2%...",
            "market": "cn",
        },
    ]

    results = []
    for i, template in enumerate(templates[:limit]):
        if market and template["market"] != market.lower():
            continue
        results.append({
            "id": i + 1,
            "title": template["title"],
            "summary": template["summary"],
            "source": "模拟来源",
            "market": template["market"],
            "url": f"https://example.com/search/{i + 1}",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "relevance": round(0.9 - i * 0.1, 2),
        })

    return results
