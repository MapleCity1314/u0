from fastapi import APIRouter, Query

from ..data import akshare_client as data
from ..models.schemas import ApiResponse

router = APIRouter()


@router.get("/", response_model=ApiResponse)
def health():
    return ApiResponse(ok=True, data={"status": "ok"})


@router.get("/data", response_model=ApiResponse)
def health_data(probe: bool = Query(default=False)):
    status = {
        "fund_value_estimation_em": hasattr(data.ak, "fund_value_estimation_em"),
        "stock_zh_a_spot_em": hasattr(data.ak, "stock_zh_a_spot_em"),
        "stock_zh_a_spot": hasattr(data.ak, "stock_zh_a_spot"),
        "fund_etf_spot_em": hasattr(data.ak, "fund_etf_spot_em"),
        "stock_zh_index_spot_em": hasattr(data.ak, "stock_zh_index_spot_em"),
        "stock_board_industry_spot_em": hasattr(data.ak, "stock_board_industry_spot_em"),
        "fund_portfolio_hold_em": hasattr(data.ak, "fund_portfolio_hold_em"),
        "fund_portfolio_industry_allocation_em": hasattr(
            data.ak, "fund_portfolio_industry_allocation_em"
        ),
    }

    if probe:
        status["probe"] = {}
        try:
            df = data.get_fund_value_estimation()
            status["probe"]["fund_value_estimation_em"] = bool(df is not None and not df.empty)
        except Exception:
            status["probe"]["fund_value_estimation_em"] = False

        try:
            df = data.get_stock_spot()
            status["probe"]["stock_zh_a_spot"] = bool(df is not None and not df.empty)
        except Exception:
            status["probe"]["stock_zh_a_spot"] = False

        try:
            s = data.get_index_spot_pct_change()
            status["probe"]["stock_zh_index_spot_em"] = bool(s is not None and len(s) > 0)
        except Exception:
            status["probe"]["stock_zh_index_spot_em"] = False

    return ApiResponse(ok=True, data=status)
