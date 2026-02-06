"""
持仓查询工具

提供用户持仓数据的查询和分析功能。
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
    name="get_positions",
    description="获取当前用户的所有基金持仓列表，包括持仓份额、成本、金额等信息",
    category=ToolCategory.SYSTEM,
    tags=["position", "portfolio", "fund"],
)
async def get_positions(ctx: ToolContext) -> str:
    """
    获取当前用户的所有基金持仓列表。

    Args:
        ctx: 工具执行上下文，必须包含 user_id

    Returns:
        持仓列表的 JSON 字符串，包含每个持仓的基金代码、份额、成本、金额等信息
    """
    if not ctx.user_id:
        return json.dumps({"error": "用户未登录，无法获取持仓信息"}, ensure_ascii=False)

    try:
        from sqlalchemy import select
        from services.users.models.position import Position
        from services.core.database import get_async_session

        async with get_async_session() as session:
            stmt = (
                select(Position)
                .where(Position.user_id == UUID(ctx.user_id))
                .where(Position.is_active == True)
                .order_by(Position.created_at.desc())
            )
            result = await session.execute(stmt)
            positions = result.scalars().all()

            if not positions:
                return json.dumps({
                    "message": "暂无持仓记录",
                    "positions": [],
                    "total_count": 0,
                }, ensure_ascii=False)

            position_list = []
            for pos in positions:
                position_list.append({
                    "id": pos.id,
                    "code": pos.code,
                    "units": pos.units,
                    "cost": pos.cost,
                    "amount": pos.amount,
                    "opened_at": pos.opened_at.isoformat() if pos.opened_at else None,
                    "source": pos.source,
                    "created_at": pos.created_at.isoformat() if pos.created_at else None,
                })

            return json.dumps({
                "positions": position_list,
                "total_count": len(position_list),
            }, ensure_ascii=False)

    except ImportError:
        # 如果数据库模块未安装，返回模拟数据
        logger.warning("Database module not available, returning mock data")
        return json.dumps({
            "positions": [
                {
                    "code": "000001",
                    "units": 1000.0,
                    "cost": 1.5,
                    "amount": 1500.0,
                    "source": "manual",
                },
            ],
            "total_count": 1,
            "note": "模拟数据（数据库未连接）",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        return json.dumps({"error": f"获取持仓失败: {str(e)}"}, ensure_ascii=False)


@tool(
    name="get_position_detail",
    description="获取用户某只基金的持仓详情，包括持仓份额、成本、当前估值等",
    category=ToolCategory.SYSTEM,
    tags=["position", "portfolio", "fund"],
)
async def get_position_detail(ctx: ToolContext, fund_code: str) -> str:
    """
    获取用户某只基金的持仓详情。

    Args:
        ctx: 工具执行上下文
        fund_code: 基金代码

    Returns:
        持仓详情的 JSON 字符串
    """
    if not ctx.user_id:
        return json.dumps({"error": "用户未登录，无法获取持仓信息"}, ensure_ascii=False)

    if not fund_code:
        return json.dumps({"error": "请提供基金代码"}, ensure_ascii=False)

    try:
        from sqlalchemy import select
        from services.users.models.position import Position
        from services.core.database import get_async_session

        async with get_async_session() as session:
            stmt = (
                select(Position)
                .where(Position.user_id == UUID(ctx.user_id))
                .where(Position.code == fund_code)
                .where(Position.is_active == True)
            )
            result = await session.execute(stmt)
            position = result.scalar_one_or_none()

            if not position:
                return json.dumps({
                    "message": f"未找到基金 {fund_code} 的持仓记录",
                    "fund_code": fund_code,
                    "has_position": False,
                }, ensure_ascii=False)

            # 尝试获取最新净值来计算收益
            current_nav = None
            current_value = None
            profit = None
            profit_rate = None

            try:
                from services.fund_nav.core.estimator import get_fund_nav
                nav_info = await get_fund_nav(fund_code)
                if nav_info and nav_info.get("nav"):
                    current_nav = float(nav_info["nav"])
                    if position.units:
                        current_value = position.units * current_nav
                        if position.amount:
                            profit = current_value - position.amount
                            profit_rate = (profit / position.amount) * 100
            except Exception as e:
                logger.warning(f"Failed to get fund NAV: {e}")

            return json.dumps({
                "fund_code": position.code,
                "has_position": True,
                "units": position.units,
                "cost": position.cost,
                "amount": position.amount,
                "opened_at": position.opened_at.isoformat() if position.opened_at else None,
                "current_nav": current_nav,
                "current_value": round(current_value, 2) if current_value else None,
                "profit": round(profit, 2) if profit else None,
                "profit_rate": round(profit_rate, 2) if profit_rate else None,
            }, ensure_ascii=False)

    except ImportError:
        logger.warning("Database module not available, returning mock data")
        return json.dumps({
            "fund_code": fund_code,
            "has_position": True,
            "units": 1000.0,
            "cost": 1.5,
            "amount": 1500.0,
            "current_nav": 1.55,
            "current_value": 1550.0,
            "profit": 50.0,
            "profit_rate": 3.33,
            "note": "模拟数据（数据库未连接）",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to get position detail: {e}")
        return json.dumps({"error": f"获取持仓详情失败: {str(e)}"}, ensure_ascii=False)


@tool(
    name="get_portfolio_summary",
    description="获取用户的持仓组合摘要，包括总资产、总收益、持仓数量等统计信息",
    category=ToolCategory.SYSTEM,
    tags=["position", "portfolio", "analysis"],
)
async def get_portfolio_summary(ctx: ToolContext) -> str:
    """
    获取用户的持仓组合摘要。

    Args:
        ctx: 工具执行上下文

    Returns:
        组合摘要的 JSON 字符串
    """
    if not ctx.user_id:
        return json.dumps({"error": "用户未登录，无法获取持仓信息"}, ensure_ascii=False)

    try:
        from sqlalchemy import select, func
        from services.users.models.position import Position
        from services.core.database import get_async_session

        async with get_async_session() as session:
            # 获取持仓统计
            stmt = (
                select(
                    func.count(Position.id).label("count"),
                    func.sum(Position.amount).label("total_amount"),
                )
                .where(Position.user_id == UUID(ctx.user_id))
                .where(Position.is_active == True)
            )
            result = await session.execute(stmt)
            row = result.one()

            position_count = row.count or 0
            total_amount = float(row.total_amount) if row.total_amount else 0.0

            # 获取所有持仓以计算当前市值
            positions_stmt = (
                select(Position)
                .where(Position.user_id == UUID(ctx.user_id))
                .where(Position.is_active == True)
            )
            positions_result = await session.execute(positions_stmt)
            positions = positions_result.scalars().all()

            # 尝试计算当前总市值
            total_current_value = 0.0
            valued_positions = 0

            for pos in positions:
                if pos.units:
                    try:
                        from services.fund_nav.core.estimator import get_fund_nav
                        nav_info = await get_fund_nav(pos.code)
                        if nav_info and nav_info.get("nav"):
                            current_nav = float(nav_info["nav"])
                            total_current_value += pos.units * current_nav
                            valued_positions += 1
                    except Exception:
                        pass

            total_profit = total_current_value - total_amount if valued_positions > 0 else None
            profit_rate = (total_profit / total_amount * 100) if total_profit and total_amount > 0 else None

            return json.dumps({
                "position_count": position_count,
                "total_cost": round(total_amount, 2),
                "total_current_value": round(total_current_value, 2) if valued_positions > 0 else None,
                "total_profit": round(total_profit, 2) if total_profit else None,
                "profit_rate": round(profit_rate, 2) if profit_rate else None,
                "valued_positions": valued_positions,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False)

    except ImportError:
        logger.warning("Database module not available, returning mock data")
        return json.dumps({
            "position_count": 3,
            "total_cost": 10000.0,
            "total_current_value": 10500.0,
            "total_profit": 500.0,
            "profit_rate": 5.0,
            "valued_positions": 3,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "note": "模拟数据（数据库未连接）",
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {e}")
        return json.dumps({"error": f"获取持仓摘要失败: {str(e)}"}, ensure_ascii=False)


class GetPositionsTool(Tool):
    """获取持仓列表工具类（可选的类形式实现）"""

    name = "get_positions_v2"
    description = "获取当前用户的所有基金持仓列表"
    category = ToolCategory.SYSTEM
    tags = ["position", "portfolio", "fund"]

    parameters = [
        ToolParameter(
            name="include_valuation",
            type="boolean",
            description="是否包含实时估值信息",
            required=False,
            default=False,
        ),
        ToolParameter(
            name="sort_by",
            type="string",
            description="排序字段: amount, profit, code",
            required=False,
            default="amount",
            enum=["amount", "profit", "code"],
        ),
    ]

    async def execute(
        self,
        ctx: ToolContext,
        include_valuation: bool = False,
        sort_by: str = "amount",
    ) -> Any:
        """执行持仓查询"""
        # 复用函数工具的逻辑
        result = await get_positions(ctx)
        return result
