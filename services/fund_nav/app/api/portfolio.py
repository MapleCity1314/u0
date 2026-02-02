from fastapi import APIRouter, Depends

from ..data import akshare_client as data
from ..models.schemas import ApiResponse, PositionDetail
from ..storage.sqlite import User
from ..core.state import store
from .auth import get_current_user

router = APIRouter()


def _ensure_positions(user: User, codes: list[str]):
    for code in codes:
        if store.get_position(user.id, code) is None:
            store.upsert_position(user.id, code, units=None, cost=None)


def _portfolio_summary(user: User, days: int = 7):
    codes = store.list_watch(user.id)
    _ensure_positions(user, codes)

    positions = store.list_positions(user.id)
    position_map = {p["code"]: p for p in positions}

    funds: list[dict] = []
    positions: list[dict] = []
    total_series = None
    total_value = 0.0
    est_pnl = 0.0
    total_pnl = 0.0

    for code in codes:
        est = data.estimate_fund(code)
        history = data.get_fund_nav_recent(code, days=days)
        nav_series = (
            [
                {"date": row["date"].strftime("%Y-%m-%d"), "nav": row["nav"]}
                for _, row in history.iterrows()
            ]
            if history is not None
            else []
        )
        curve = data.estimate_curve(code, history) if history is not None else []

        pos = position_map.get(code)
        units = pos["units"] if pos else 0.0
        cost = pos["cost"] if pos else None

        last_nav = est.get("last_nav")
        if last_nav is not None and cost is None:
            store.upsert_position(user.id, code, units=units, cost=last_nav)
            cost = last_nav
        if last_nav is not None:
            total_value += units * last_nav
            if est.get("est_return") is not None:
                est_pnl += units * last_nav * est.get("est_return")
            if cost is not None:
                total_pnl += units * (last_nav - cost)

        if total_series is None and nav_series:
            total_series = [{"date": row["date"], "value": 0.0} for row in nav_series]

        if total_series is not None and nav_series:
            for idx, row in enumerate(nav_series):
                if idx < len(total_series):
                    total_series[idx]["value"] += units * row["nav"]

        funds.append(
            {
                "code": code,
                "name": est.get("name"),
                "last_nav": last_nav,
                "est_return": est.get("est_return"),
                "est_nav": est.get("est_nav"),
                "source": est.get("source"),
                "coverage": est.get("coverage"),
                "units": units,
                "cost": cost,
                "nav_history": nav_series,
                "est_curve": curve,
            }
        )

        positions.append(
            PositionDetail(
                code=code,
                name=est.get("name"),
                units=units,
                cost=cost,
                last_nav=last_nav,
                market_value=units * last_nav if last_nav is not None else None,
                daily_return=est.get("est_return"),
                daily_pnl=units * last_nav * est.get("est_return") if last_nav is not None and est.get("est_return") is not None else None,
                total_pnl=units * (last_nav - cost) if last_nav is not None and cost is not None else None,
            ).dict()
        )

    est_return = est_pnl / total_value if total_value > 0 else 0.0
    return {
        "funds": funds,
        "positions": positions,
        "total_curve": total_series or [],
        "est_return": est_return,
        "est_pnl": est_pnl,
        "total_pnl": total_pnl,
        "total_value": total_value,
    }


@router.get("/summary", response_model=ApiResponse)
def summary(user: User = Depends(get_current_user)):
    data = _portfolio_summary(user)
    return ApiResponse(ok=True, data=data)
