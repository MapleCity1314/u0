"""
基金净值查询工具

提供基金净值、估值、搜索等功能。
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
    name="get_fund_nav",
    description="获取基金的最新净值信息，包括单位净值、累计净值、涨跌幅等",
    category=ToolCategory.SYSTEM,
    tags=["fund", "nav", "valuation"],
)
async def get_fund_nav(ctx: ToolContext, fund_code: str) -> str:
    """
    获取基金的最新净值信息。

    Args:
        ctx: 工具执行上下文
        fund_code: 基金代码，如 "000001"

    Returns:
        基金净值信息的 JSON 字符串，包含单位净值、累计净值、净值日期、涨跌幅等
    """
    if not fund_code:
        return json.dumps({"error": "请提供基金代码"}, ensure_ascii=False)

    # 清理基金代码
    fund_code = fund_code.strip()

    try:
        # 尝试使用系统内部服务
        from services.fund_nav.core.fetcher import fetch_fund_nav

        nav_data = await fetch_fund_nav(fund_code)

        if nav_data:
            return json.dumps({
                "fund_code": fund_code,
                "fund_name": nav_data.get("name", ""),
                "nav": nav_data.get("nav"),
                "acc_nav": nav_data.get("acc_nav"),
                "nav_date": nav_data.get("nav_date"),
                "daily_return": nav_data.get("daily_return"),
                "fund_type": nav_data.get("fund_type"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "error": f"未找到基金 {fund_code} 的净值信息",
                "fund_code": fund_code,
            }, ensure_ascii=False)

    except ImportError:
        # 如果内部服务不可用，尝试使用 akshare
        try:
            import akshare as ak

            # 获取开放式基金净值
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return json.dumps({
                    "fund_code": fund_code,
                    "nav": float(latest["单位净值"]) if "单位净值" in latest else None,
                    "nav_date": str(latest["净值日期"]) if "净值日期" in latest else None,
                    "source": "akshare",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"AkShare fetch failed: {e}")

        # 返回模拟数据
        logger.warning("Fund NAV service not available, returning mock data")
        return json.dumps({
            "fund_code": fund_code,
            "fund_name": "示例基金",
            "nav": 1.2345,
            "acc_nav": 2.3456,
            "nav_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "daily_return": 0.52,
            "note": "模拟数据（净值服务未连接）",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to get fund NAV: {e}")
        return json.dumps({
            "error": f"获取基金净值失败: {str(e)}",
            "fund_code": fund_code,
        }, ensure_ascii=False)


@tool(
    name="get_fund_estimate",
    description="获取基金的实时估值信息，包括估算净值、估算涨跌幅（仅交易时段有效）",
    category=ToolCategory.SYSTEM,
    tags=["fund", "estimate", "valuation", "realtime"],
)
async def get_fund_estimate(
    ctx: ToolContext,
    fund_code: str,
    source: str = "auto",
) -> str:
    """
    获取基金的实时估值信息。

    Args:
        ctx: 工具执行上下文
        fund_code: 基金代码
        source: 估值来源，可选 auto/eastmoney/model

    Returns:
        基金估值信息的 JSON 字符串
    """
    if not fund_code:
        return json.dumps({"error": "请提供基金代码"}, ensure_ascii=False)

    fund_code = fund_code.strip()

    try:
        from services.fund_nav.core.estimator import estimate_fund_nav

        estimate_data = await estimate_fund_nav(fund_code, source=source)

        if estimate_data:
            return json.dumps({
                "fund_code": fund_code,
                "fund_name": estimate_data.get("name", ""),
                "estimate_nav": estimate_data.get("estimate_nav"),
                "estimate_return": estimate_data.get("estimate_return"),
                "estimate_time": estimate_data.get("estimate_time"),
                "last_nav": estimate_data.get("last_nav"),
                "last_nav_date": estimate_data.get("last_nav_date"),
                "source": estimate_data.get("source", source),
                "is_trading_hours": estimate_data.get("is_trading_hours", False),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "error": f"未找到基金 {fund_code} 的估值信息",
                "fund_code": fund_code,
            }, ensure_ascii=False)

    except ImportError:
        # 尝试使用 akshare
        try:
            import akshare as ak

            df = ak.fund_etf_fund_info_em(fund=fund_code)
            if df is not None and not df.empty:
                return json.dumps({
                    "fund_code": fund_code,
                    "estimate_nav": float(df.iloc[-1].get("净值估算", 0)),
                    "source": "akshare",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"AkShare estimate failed: {e}")

        logger.warning("Fund estimate service not available, returning mock data")
        return json.dumps({
            "fund_code": fund_code,
            "fund_name": "示例基金",
            "estimate_nav": 1.2400,
            "estimate_return": 0.45,
            "estimate_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "last_nav": 1.2345,
            "is_trading_hours": True,
            "source": "mock",
            "note": "模拟数据（估值服务未连接）",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to get fund estimate: {e}")
        return json.dumps({
            "error": f"获取基金估值失败: {str(e)}",
            "fund_code": fund_code,
        }, ensure_ascii=False)


@tool(
    name="search_funds",
    description="搜索基金，支持按名称、代码、类型等条件搜索",
    category=ToolCategory.SYSTEM,
    tags=["fund", "search"],
)
async def search_funds(
    ctx: ToolContext,
    query: str,
    fund_type: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    搜索基金。

    Args:
        ctx: 工具执行上下文
        query: 搜索关键词（基金名称或代码）
        fund_type: 基金类型过滤，可选 stock/bond/money/hybrid/index/qdii
        limit: 返回结果数量限制，默认 10

    Returns:
        搜索结果的 JSON 字符串
    """
    if not query:
        return json.dumps({"error": "请提供搜索关键词"}, ensure_ascii=False)

    query = query.strip()
    limit = min(max(1, limit), 50)  # 限制在 1-50 之间

    try:
        from services.fund_nav.core.searcher import search_funds as do_search

        results = await do_search(query, fund_type=fund_type, limit=limit)

        if results:
            return json.dumps({
                "query": query,
                "fund_type": fund_type,
                "results": results,
                "total": len(results),
                "limit": limit,
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "query": query,
                "fund_type": fund_type,
                "results": [],
                "total": 0,
                "message": "未找到匹配的基金",
            }, ensure_ascii=False)

    except ImportError:
        # 尝试使用 akshare
        try:
            import akshare as ak

            # 获取所有基金列表
            df = ak.fund_name_em()
            if df is not None and not df.empty:
                # 简单搜索
                mask = (
                    df["基金代码"].str.contains(query, na=False) |
                    df["基金简称"].str.contains(query, na=False, case=False)
                )
                filtered = df[mask].head(limit)

                results = []
                for _, row in filtered.iterrows():
                    results.append({
                        "code": row["基金代码"],
                        "name": row["基金简称"],
                        "type": row.get("基金类型", ""),
                    })

                return json.dumps({
                    "query": query,
                    "results": results,
                    "total": len(results),
                    "source": "akshare",
                }, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"AkShare search failed: {e}")

        logger.warning("Fund search service not available, returning mock data")
        return json.dumps({
            "query": query,
            "results": [
                {"code": "000001", "name": "华夏成长混合", "type": "混合型-偏股"},
                {"code": "000002", "name": "华夏回报混合A", "type": "混合型-偏债"},
                {"code": "110011", "name": "易方达中小盘混合", "type": "混合型-偏股"},
            ],
            "total": 3,
            "note": "模拟数据（搜索服务未连接）",
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to search funds: {e}")
        return json.dumps({
            "error": f"搜索基金失败: {str(e)}",
            "query": query,
        }, ensure_ascii=False)


@tool(
    name="get_fund_detail",
    description="获取基金的详细信息，包括基金经理、规模、成立日期、投资策略、持仓情况等",
    category=ToolCategory.SYSTEM,
    tags=["fund", "detail", "info"],
)
async def get_fund_detail(ctx: ToolContext, fund_code: str) -> str:
    """
    获取基金的详细信息。

    Args:
        ctx: 工具执行上下文
        fund_code: 基金代码

    Returns:
        基金详细信息的 JSON 字符串
    """
    if not fund_code:
        return json.dumps({"error": "请提供基金代码"}, ensure_ascii=False)

    fund_code = fund_code.strip()

    try:
        from services.fund_nav.core.fetcher import fetch_fund_detail

        detail = await fetch_fund_detail(fund_code)

        if detail:
            return json.dumps({
                "fund_code": fund_code,
                "fund_name": detail.get("name", ""),
                "fund_type": detail.get("type", ""),
                "fund_company": detail.get("company", ""),
                "fund_manager": detail.get("manager", ""),
                "establish_date": detail.get("establish_date", ""),
                "fund_size": detail.get("size", ""),
                "benchmark": detail.get("benchmark", ""),
                "investment_scope": detail.get("investment_scope", ""),
                "risk_level": detail.get("risk_level", ""),
                "fee_rate": detail.get("fee_rate", {}),
                "top_holdings": detail.get("top_holdings", []),
                "sector_allocation": detail.get("sector_allocation", []),
                "performance": detail.get("performance", {}),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "error": f"未找到基金 {fund_code} 的详细信息",
                "fund_code": fund_code,
            }, ensure_ascii=False)

    except ImportError:
        # 尝试使用 akshare 获取部分信息
        try:
            import akshare as ak

            # 获取基金基本信息
            info = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if info is not None:
                return json.dumps({
                    "fund_code": fund_code,
                    "fund_name": info.get("基金名称", ""),
                    "fund_type": info.get("基金类型", ""),
                    "fund_company": info.get("基金公司", ""),
                    "fund_manager": info.get("基金经理", ""),
                    "establish_date": info.get("成立日期", ""),
                    "fund_size": info.get("基金规模", ""),
                    "source": "akshare",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"AkShare detail fetch failed: {e}")

        logger.warning("Fund detail service not available, returning mock data")
        return json.dumps({
            "fund_code": fund_code,
            "fund_name": "示例成长混合基金",
            "fund_type": "混合型-偏股",
            "fund_company": "示例基金管理有限公司",
            "fund_manager": "张三",
            "establish_date": "2015-06-01",
            "fund_size": "50.23亿元",
            "benchmark": "沪深300指数收益率×60%+中证综合债指数收益率×40%",
            "risk_level": "中高风险(R4)",
            "fee_rate": {
                "management_fee": "1.50%",
                "custody_fee": "0.25%",
                "purchase_fee": "1.50%",
                "redemption_fee": "0.50%",
            },
            "top_holdings": [
                {"stock_code": "600519", "stock_name": "贵州茅台", "weight": "8.52%"},
                {"stock_code": "000858", "stock_name": "五粮液", "weight": "5.23%"},
                {"stock_code": "000333", "stock_name": "美的集团", "weight": "4.81%"},
            ],
            "performance": {
                "ytd": "12.35%",
                "1y": "25.67%",
                "3y": "45.23%",
                "since_inception": "156.78%",
            },
            "note": "模拟数据（详情服务未连接）",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to get fund detail: {e}")
        return json.dumps({
            "error": f"获取基金详情失败: {str(e)}",
            "fund_code": fund_code,
        }, ensure_ascii=False)


@tool(
    name="get_fund_history",
    description="获取基金的历史净值数据",
    category=ToolCategory.SYSTEM,
    tags=["fund", "nav", "history"],
)
async def get_fund_history(
    ctx: ToolContext,
    fund_code: str,
    days: int = 30,
) -> str:
    """
    获取基金的历史净值数据。

    Args:
        ctx: 工具执行上下文
        fund_code: 基金代码
        days: 获取最近多少天的数据，默认 30 天

    Returns:
        历史净值数据的 JSON 字符串
    """
    if not fund_code:
        return json.dumps({"error": "请提供基金代码"}, ensure_ascii=False)

    fund_code = fund_code.strip()
    days = min(max(1, days), 365)  # 限制在 1-365 之间

    try:
        from services.fund_nav.core.fetcher import fetch_fund_history

        history = await fetch_fund_history(fund_code, days=days)

        if history:
            return json.dumps({
                "fund_code": fund_code,
                "days": days,
                "data": history,
                "count": len(history),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "error": f"未找到基金 {fund_code} 的历史数据",
                "fund_code": fund_code,
            }, ensure_ascii=False)

    except ImportError:
        # 尝试使用 akshare
        try:
            import akshare as ak
            from datetime import timedelta

            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if df is not None and not df.empty:
                # 取最近 N 天
                df = df.tail(days)
                history = []
                for _, row in df.iterrows():
                    history.append({
                        "date": str(row.get("净值日期", "")),
                        "nav": float(row.get("单位净值", 0)),
                        "acc_nav": float(row.get("累计净值", 0)) if "累计净值" in row else None,
                        "daily_return": float(row.get("日增长率", 0)) if "日增长率" in row else None,
                    })

                return json.dumps({
                    "fund_code": fund_code,
                    "days": days,
                    "data": history,
                    "count": len(history),
                    "source": "akshare",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"AkShare history fetch failed: {e}")

        logger.warning("Fund history service not available, returning mock data")
        # 生成模拟历史数据
        from datetime import timedelta
        mock_history = []
        base_nav = 1.2
        for i in range(days):
            date = datetime.now(timezone.utc) - timedelta(days=days - i - 1)
            nav = base_nav + (i * 0.005) + ((i % 3) - 1) * 0.01
            mock_history.append({
                "date": date.strftime("%Y-%m-%d"),
                "nav": round(nav, 4),
                "daily_return": round(((i % 3) - 1) * 0.5, 2),
            })

        return json.dumps({
            "fund_code": fund_code,
            "days": days,
            "data": mock_history,
            "count": len(mock_history),
            "note": "模拟数据（历史服务未连接）",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to get fund history: {e}")
        return json.dumps({
            "error": f"获取基金历史数据失败: {str(e)}",
            "fund_code": fund_code,
        }, ensure_ascii=False)


@tool(
    name="compare_funds",
    description="对比多只基金的业绩表现",
    category=ToolCategory.SYSTEM,
    tags=["fund", "compare", "analysis"],
)
async def compare_funds(
    ctx: ToolContext,
    fund_codes: str,
    period: str = "1y",
) -> str:
    """
    对比多只基金的业绩表现。

    Args:
        ctx: 工具执行上下文
        fund_codes: 基金代码列表，用逗号分隔，如 "000001,000002,110011"
        period: 对比周期，可选 1m/3m/6m/1y/3y/5y

    Returns:
        基金对比结果的 JSON 字符串
    """
    if not fund_codes:
        return json.dumps({"error": "请提供基金代码列表"}, ensure_ascii=False)

    # 解析基金代码列表
    codes = [c.strip() for c in fund_codes.split(",") if c.strip()]
    if len(codes) < 2:
        return json.dumps({"error": "请至少提供 2 只基金进行对比"}, ensure_ascii=False)
    if len(codes) > 10:
        return json.dumps({"error": "最多支持对比 10 只基金"}, ensure_ascii=False)

    valid_periods = ["1m", "3m", "6m", "1y", "3y", "5y"]
    if period not in valid_periods:
        period = "1y"

    try:
        from services.fund_nav.core.analyzer import compare_funds as do_compare

        result = await do_compare(codes, period=period)
        return json.dumps(result, ensure_ascii=False)

    except ImportError:
        logger.warning("Fund compare service not available, returning mock data")

        # 生成模拟对比数据
        comparisons = []
        for i, code in enumerate(codes):
            base_return = 10 + i * 5 + (hash(code) % 20 - 10)
            comparisons.append({
                "fund_code": code,
                "fund_name": f"示例基金{i + 1}",
                "return": round(base_return, 2),
                "volatility": round(15 + i * 2, 2),
                "max_drawdown": round(-8 - i * 1.5, 2),
                "sharpe_ratio": round(1.2 + i * 0.1, 2),
            })

        # 按收益率排序
        comparisons.sort(key=lambda x: x["return"], reverse=True)

        return json.dumps({
            "fund_codes": codes,
            "period": period,
            "comparison": comparisons,
            "best_performer": comparisons[0]["fund_code"],
            "note": "模拟数据（对比服务未连接）",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to compare funds: {e}")
        return json.dumps({
            "error": f"基金对比失败: {str(e)}",
            "fund_codes": codes,
        }, ensure_ascii=False)
