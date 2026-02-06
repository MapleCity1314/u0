"""
自选股工具

提供用户自选列表的查询和管理功能。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from services.agent.tools.base import (
    Tool,
    ToolCategory,
    ToolContext,
    ToolParameter,
    tool,
)

logger = logging.getLogger(__name__)


@tool(
    name="get_watchlist",
    description="获取当前用户的自选基金列表",
    category=ToolCategory.SYSTEM,
    tags=["watchlist", "fund", "portfolio"],
)
async def get_watchlist(ctx: ToolContext) -> str:
    """
    获取当前用户的自选基金列表。

    Args:
        ctx: 工具执行上下文，必须包含 user_id

    Returns:
        自选列表的 JSON 字符串，包含基金代码、添加时间等信息
    """
    if not ctx.user_id:
        return json.dumps({"error": "用户未登录，无法获取自选列表"}, ensure_ascii=False)

    try:
        from sqlalchemy import select
        from services.users.models.watchlist_item import WatchlistItem
        from services.core.database import get_async_session

        async with get_async_session() as session:
            stmt = (
                select(WatchlistItem)
                .where(WatchlistItem.user_id == UUID(ctx.user_id))
                .order_by(WatchlistItem.created_at.desc())
            )
            result = await session.execute(stmt)
            items = result.scalars().all()

            if not items:
                return json.dumps({
                    "message": "自选列表为空",
                    "watchlist": [],
                    "total_count": 0,
                }, ensure_ascii=False)

            watchlist = []
            for item in items:
                watchlist.append({
                    "id": item.id,
                    "code": item.code,
                    "name": item.name if hasattr(item, "name") else None,
                    "note": item.note if hasattr(item, "note") else None,
                    "added_at": item.created_at.isoformat() if item.created_at else None,
                })

            return json.dumps({
                "watchlist": watchlist,
                "total_count": len(watchlist),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        logger.warning("Database module not available, returning mock data")
        return json.dumps({
            "watchlist": [
                {
                    "code": "000001",
                    "name": "华夏成长混合",
                    "added_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "code": "110011",
                    "name": "易方达中小盘混合",
                    "added_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "code": "161725",
                    "name": "招商中证白酒指数",
                    "added_at": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "total_count": 3,
            "note": "模拟数据（数据库未连接）",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to get watchlist: {e}")
        return json.dumps({"error": f"获取自选列表失败: {str(e)}"}, ensure_ascii=False)


@tool(
    name="add_to_watchlist",
    description="将基金添加到用户的自选列表",
    category=ToolCategory.SYSTEM,
    tags=["watchlist", "fund", "portfolio"],
)
async def add_to_watchlist(
    ctx: ToolContext,
    fund_code: str,
    note: Optional[str] = None,
) -> str:
    """
    将基金添加到用户的自选列表。

    Args:
        ctx: 工具执行上下文
        fund_code: 基金代码
        note: 备注信息（可选）

    Returns:
        操作结果的 JSON 字符串
    """
    if not ctx.user_id:
        return json.dumps({"error": "用户未登录，无法添加自选"}, ensure_ascii=False)

    if not fund_code:
        return json.dumps({"error": "请提供基金代码"}, ensure_ascii=False)

    fund_code = fund_code.strip()

    try:
        from sqlalchemy import select
        from services.users.models.watchlist_item import WatchlistItem
        from services.core.database import get_async_session

        async with get_async_session() as session:
            # 检查是否已存在
            stmt = (
                select(WatchlistItem)
                .where(WatchlistItem.user_id == UUID(ctx.user_id))
                .where(WatchlistItem.code == fund_code)
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                return json.dumps({
                    "success": False,
                    "message": f"基金 {fund_code} 已在自选列表中",
                    "fund_code": fund_code,
                }, ensure_ascii=False)

            # 尝试获取基金名称
            fund_name = None
            try:
                from services.fund_nav.core.fetcher import fetch_fund_info
                info = await fetch_fund_info(fund_code)
                if info:
                    fund_name = info.get("name")
            except Exception:
                pass

            # 创建新的自选项
            new_item = WatchlistItem(
                user_id=UUID(ctx.user_id),
                code=fund_code,
                name=fund_name,
                note=note,
            )
            session.add(new_item)
            await session.commit()

            return json.dumps({
                "success": True,
                "message": f"已将基金 {fund_code} 添加到自选列表",
                "fund_code": fund_code,
                "fund_name": fund_name,
                "added_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        logger.warning("Database module not available, returning mock result")
        return json.dumps({
            "success": True,
            "message": f"已将基金 {fund_code} 添加到自选列表",
            "fund_code": fund_code,
            "note": "模拟操作（数据库未连接）",
            "added_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to add to watchlist: {e}")
        return json.dumps({
            "success": False,
            "error": f"添加自选失败: {str(e)}",
            "fund_code": fund_code,
        }, ensure_ascii=False)


@tool(
    name="remove_from_watchlist",
    description="从用户的自选列表中移除基金",
    category=ToolCategory.SYSTEM,
    tags=["watchlist", "fund", "portfolio"],
)
async def remove_from_watchlist(ctx: ToolContext, fund_code: str) -> str:
    """
    从用户的自选列表中移除基金。

    Args:
        ctx: 工具执行上下文
        fund_code: 基金代码

    Returns:
        操作结果的 JSON 字符串
    """
    if not ctx.user_id:
        return json.dumps({"error": "用户未登录，无法移除自选"}, ensure_ascii=False)

    if not fund_code:
        return json.dumps({"error": "请提供基金代码"}, ensure_ascii=False)

    fund_code = fund_code.strip()

    try:
        from sqlalchemy import select, delete
        from services.users.models.watchlist_item import WatchlistItem
        from services.core.database import get_async_session

        async with get_async_session() as session:
            # 检查是否存在
            stmt = (
                select(WatchlistItem)
                .where(WatchlistItem.user_id == UUID(ctx.user_id))
                .where(WatchlistItem.code == fund_code)
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                return json.dumps({
                    "success": False,
                    "message": f"基金 {fund_code} 不在自选列表中",
                    "fund_code": fund_code,
                }, ensure_ascii=False)

            # 删除自选项
            delete_stmt = (
                delete(WatchlistItem)
                .where(WatchlistItem.user_id == UUID(ctx.user_id))
                .where(WatchlistItem.code == fund_code)
            )
            await session.execute(delete_stmt)
            await session.commit()

            return json.dumps({
                "success": True,
                "message": f"已将基金 {fund_code} 从自选列表中移除",
                "fund_code": fund_code,
                "removed_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        logger.warning("Database module not available, returning mock result")
        return json.dumps({
            "success": True,
            "message": f"已将基金 {fund_code} 从自选列表中移除",
            "fund_code": fund_code,
            "note": "模拟操作（数据库未连接）",
            "removed_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to remove from watchlist: {e}")
        return json.dumps({
            "success": False,
            "error": f"移除自选失败: {str(e)}",
            "fund_code": fund_code,
        }, ensure_ascii=False)


@tool(
    name="get_watchlist_with_quotes",
    description="获取自选列表及其最新行情数据，包括净值、涨跌幅等",
    category=ToolCategory.SYSTEM,
    tags=["watchlist", "fund", "quotes", "realtime"],
)
async def get_watchlist_with_quotes(ctx: ToolContext) -> str:
    """
    获取自选列表及其最新行情数据。

    Args:
        ctx: 工具执行上下文

    Returns:
        带行情数据的自选列表 JSON 字符串
    """
    if not ctx.user_id:
        return json.dumps({"error": "用户未登录，无法获取自选列表"}, ensure_ascii=False)

    try:
        from sqlalchemy import select
        from services.users.models.watchlist_item import WatchlistItem
        from services.core.database import get_async_session

        async with get_async_session() as session:
            stmt = (
                select(WatchlistItem)
                .where(WatchlistItem.user_id == UUID(ctx.user_id))
                .order_by(WatchlistItem.created_at.desc())
            )
            result = await session.execute(stmt)
            items = result.scalars().all()

            if not items:
                return json.dumps({
                    "message": "自选列表为空",
                    "watchlist": [],
                    "total_count": 0,
                }, ensure_ascii=False)

            watchlist = []
            for item in items:
                fund_data = {
                    "id": item.id,
                    "code": item.code,
                    "name": item.name if hasattr(item, "name") else None,
                    "note": item.note if hasattr(item, "note") else None,
                    "added_at": item.created_at.isoformat() if item.created_at else None,
                }

                # 尝试获取最新行情
                try:
                    from services.fund_nav.core.estimator import estimate_fund_nav
                    quote = await estimate_fund_nav(item.code)
                    if quote:
                        fund_data.update({
                            "nav": quote.get("last_nav"),
                            "nav_date": quote.get("last_nav_date"),
                            "estimate_nav": quote.get("estimate_nav"),
                            "estimate_return": quote.get("estimate_return"),
                            "estimate_time": quote.get("estimate_time"),
                        })
                except Exception as e:
                    logger.warning(f"Failed to get quote for {item.code}: {e}")

                watchlist.append(fund_data)

            return json.dumps({
                "watchlist": watchlist,
                "total_count": len(watchlist),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        logger.warning("Database module not available, returning mock data")
        return json.dumps({
            "watchlist": [
                {
                    "code": "000001",
                    "name": "华夏成长混合",
                    "nav": 1.5230,
                    "nav_date": "2024-01-15",
                    "estimate_nav": 1.5345,
                    "estimate_return": 0.75,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "code": "110011",
                    "name": "易方达中小盘混合",
                    "nav": 4.8920,
                    "nav_date": "2024-01-15",
                    "estimate_nav": 4.9150,
                    "estimate_return": 0.47,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "code": "161725",
                    "name": "招商中证白酒指数",
                    "nav": 1.2345,
                    "nav_date": "2024-01-15",
                    "estimate_nav": 1.2210,
                    "estimate_return": -1.09,
                    "added_at": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "total_count": 3,
            "note": "模拟数据（数据库未连接）",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to get watchlist with quotes: {e}")
        return json.dumps({"error": f"获取自选行情失败: {str(e)}"}, ensure_ascii=False)


@tool(
    name="update_watchlist_note",
    description="更新自选基金的备注信息",
    category=ToolCategory.SYSTEM,
    tags=["watchlist", "fund"],
)
async def update_watchlist_note(
    ctx: ToolContext,
    fund_code: str,
    note: str,
) -> str:
    """
    更新自选基金的备注信息。

    Args:
        ctx: 工具执行上下文
        fund_code: 基金代码
        note: 新的备注信息

    Returns:
        操作结果的 JSON 字符串
    """
    if not ctx.user_id:
        return json.dumps({"error": "用户未登录，无法更新备注"}, ensure_ascii=False)

    if not fund_code:
        return json.dumps({"error": "请提供基金代码"}, ensure_ascii=False)

    fund_code = fund_code.strip()

    try:
        from sqlalchemy import select, update
        from services.users.models.watchlist_item import WatchlistItem
        from services.core.database import get_async_session

        async with get_async_session() as session:
            # 检查是否存在
            stmt = (
                select(WatchlistItem)
                .where(WatchlistItem.user_id == UUID(ctx.user_id))
                .where(WatchlistItem.code == fund_code)
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                return json.dumps({
                    "success": False,
                    "message": f"基金 {fund_code} 不在自选列表中",
                    "fund_code": fund_code,
                }, ensure_ascii=False)

            # 更新备注
            update_stmt = (
                update(WatchlistItem)
                .where(WatchlistItem.user_id == UUID(ctx.user_id))
                .where(WatchlistItem.code == fund_code)
                .values(note=note)
            )
            await session.execute(update_stmt)
            await session.commit()

            return json.dumps({
                "success": True,
                "message": f"已更新基金 {fund_code} 的备注",
                "fund_code": fund_code,
                "note": note,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        logger.warning("Database module not available, returning mock result")
        return json.dumps({
            "success": True,
            "message": f"已更新基金 {fund_code} 的备注",
            "fund_code": fund_code,
            "note": note,
            "mock": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Failed to update watchlist note: {e}")
        return json.dumps({
            "success": False,
            "error": f"更新备注失败: {str(e)}",
            "fund_code": fund_code,
        }, ensure_ascii=False)
