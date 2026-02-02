import time
import threading
from typing import Any, Optional

import akshare as ak
import pandas as pd

FUND_CODES = ["022485", "024663"]
INDEX_CODES = ["000510", "970070"]
SLEEP_SEC = 3
MAX_RETRIES = 2
REQUEST_TIMEOUT = 20


class TimeoutError(Exception):
    pass


def call_with_timeout(func, args=(), kwargs=None, timeout=REQUEST_TIMEOUT) -> Any:
    if kwargs is None:
        kwargs = {}

    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    if exception[0] is not None:
        raise exception[0]
    return result[0]


def _ok(df: Optional[pd.DataFrame]) -> str:
    if df is None:
        return "None"
    if df.empty:
        return "empty"
    return f"rows={len(df)} cols={len(df.columns)}"


def try_call(name: str, func, kwargs=None):
    try:
        df = call_with_timeout(func, kwargs=kwargs or {})
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]
        print(f"OK  {name:35s}  {_ok(df)}")
        return df
    except Exception as e:
        print(f"ERR {name:35s}  {str(e)[:120]}")
        return None


def main():
    print("=== AkShare 数据源连通性测试 ===")

    while True:
        print("\n--- 股票实时行情 ---")
        try_call("stock_zh_a_spot_em", ak.stock_zh_a_spot_em)
        if hasattr(ak, "stock_zh_a_spot"):
            try_call("stock_zh_a_spot", ak.stock_zh_a_spot)

        print("\n--- ETF 实时行情 ---")
        if hasattr(ak, "fund_etf_spot_em"):
            try_call("fund_etf_spot_em", ak.fund_etf_spot_em)

        print("\n--- 指数实时行情 ---")
        try_call("stock_zh_index_spot_em", ak.stock_zh_index_spot_em, {"symbol": "沪深重要指数"})

        print("\n--- 行业板块实时行情 ---")
        if hasattr(ak, "stock_board_industry_spot_em"):
            try_call("stock_board_industry_spot_em", ak.stock_board_industry_spot_em)

        print("\n--- 基金估值 ---")
        if hasattr(ak, "fund_value_estimation_em"):
            try_call("fund_value_estimation_em", ak.fund_value_estimation_em)

        print("\n--- 基金持仓/行业配置 ---")
        for code in FUND_CODES:
            if hasattr(ak, "fund_portfolio_hold_em"):
                try_call(f"fund_portfolio_hold_em({code})", ak.fund_portfolio_hold_em, {"symbol": code, "date": str(pd.Timestamp.now().year)})
            if hasattr(ak, "fund_portfolio_industry_allocation_em"):
                try_call(
                    f"fund_portfolio_industry_allocation_em({code})",
                    ak.fund_portfolio_industry_allocation_em,
                    {"symbol": code, "date": str(pd.Timestamp.now().year)},
                )

        print("\n--- 基金净值 ---")
        for code in FUND_CODES:
            try_call(
                f"fund_open_fund_info_em({code})",
                ak.fund_open_fund_info_em,
                {"symbol": code, "indicator": "单位净值走势"},
            )

        print("\n--- 指数历史 ---")
        for code in INDEX_CODES:
            if hasattr(ak, "index_zh_a_hist"):
                try_call(
                    f"index_zh_a_hist({code})",
                    ak.index_zh_a_hist,
                    {
                        "symbol": code,
                        "period": "daily",
                        "start_date": (pd.Timestamp.now() - pd.Timedelta(days=30)).strftime("%Y%m%d"),
                        "end_date": pd.Timestamp.now().strftime("%Y%m%d"),
                    },
                )

        time.sleep(SLEEP_SEC)


if __name__ == "__main__":
    main()
