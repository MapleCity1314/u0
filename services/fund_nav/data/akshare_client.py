import os
import re
import threading
import json
import html as html_lib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

import pandas as pd
import httpx

from services.modules.akshare import cached_call, has_func

REQUEST_TIMEOUT = 60
BG_REFRESH_INTERVAL_SEC = int(os.getenv("FUND_NAV_BG_REFRESH_INTERVAL_SEC", "20"))
BG_REFRESH_ENABLED = os.getenv("FUND_NAV_BG_REFRESH_ENABLED", "false").lower() in (
    "1",
    "true",
    "yes",
)
_bg_started = False


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _col_has(text: str, *tokens: str) -> bool:
    return any(token in text for token in tokens)


def get_fund_nav_daily(symbol: str) -> pd.DataFrame:
    df = cached_call(
        "fund_open_fund_info_em",
        kwargs={"symbol": symbol, "indicator": "单位净值走势"},
        timeout=REQUEST_TIMEOUT,
        ttl=300,
    )
    df = _clean_df(df)

    date_col = None
    nav_col = None
    for c in df.columns:
        if _col_has(c, "净值日期") or c.lower() in ("date", "日期"):
            date_col = c
        if _col_has(c, "单位净值") or c.lower() in ("unit_net_value", "nav"):
            nav_col = c
    if date_col is None or nav_col is None:
        raise RuntimeError("基金净值字段识别失败")

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col).rename(columns={date_col: "date", nav_col: "nav"})
    df["fund_ret"] = df["nav"].pct_change()
    df = df.dropna(subset=["fund_ret"])
    return df[["date", "nav", "fund_ret"]]


def get_fund_nav_recent(symbol: str, days: int = 7) -> Optional[pd.DataFrame]:
    df = get_fund_nav_daily(symbol)
    if df is None or df.empty:
        return None
    df = df.sort_values("date").tail(days)
    return df[["date", "nav"]]


def estimate_curve(symbol: str, history: Optional[pd.DataFrame]) -> list[dict]:
    if history is None or history.empty:
        return []
    est = estimate_fund(symbol)
    est_ret = est.get("est_return")
    last_nav = est.get("last_nav")
    if est_ret is None or last_nav is None:
        return []

    curve = [
        {"date": row["date"].strftime("%Y-%m-%d"), "nav": row["nav"]}
        for _, row in history.iterrows()
    ]

    est_nav = last_nav * (1.0 + est_ret)
    last_date = history["date"].iloc[-1].strftime("%Y-%m-%d")
    curve.append({"date": f"{last_date}(est)", "nav": est_nav})
    return curve


def get_fund_value_estimation() -> Optional[pd.DataFrame]:
    if not has_func("fund_value_estimation_em"):
        return None

    try:
        df = cached_call("fund_value_estimation_em", timeout=REQUEST_TIMEOUT, ttl=30)
    except Exception as e:
        import logging
        logging.error(f"get_fund_value_estimation failed: {type(e).__name__}: {str(e)}")
        return None
    return _clean_df(df)


def get_all_fund_names() -> Optional[pd.DataFrame]:
    """Get comprehensive fund list (code + name) from akshare."""
    if not has_func("fund_name_em"):
        return None

    try:
        df = cached_call("fund_name_em", timeout=REQUEST_TIMEOUT, ttl=3600)
    except Exception as e:
        import logging
        logging.error(f"get_all_fund_names failed: {type(e).__name__}: {str(e)}")
        return None
    return _clean_df(df)


def _parse_trade_calendar(df: pd.DataFrame) -> Optional[pd.Series]:
    df = _clean_df(df)
    date_col = None
    for c in df.columns:
        if _col_has(c, "交易日", "日期", "date", "trade_date") or c.lower() in ("date", "trade_date"):
            date_col = c
            break
    if date_col is None:
        return None
    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if dates.empty:
        return None
    return dates.dt.normalize()


def get_trade_calendar(
    start: str | None = None,
    end: str | None = None,
) -> list[str]:
    candidates = [
        ("tool_trade_date_hist_sina", None),
        ("stock_zh_a_trade_date", None),
    ]
    series = None
    for name, kwargs in candidates:
        if not has_func(name):
            continue
        try:
            df = cached_call(name, kwargs=kwargs, timeout=REQUEST_TIMEOUT, ttl=3600)
            series = _parse_trade_calendar(df)
            if series is not None:
                break
        except Exception:
            continue

    if series is None:
        end_dt = pd.Timestamp(end) if end else pd.Timestamp.now()
        start_dt = pd.Timestamp(start) if start else end_dt - pd.Timedelta(days=365)
        dates = pd.date_range(start=start_dt, end=end_dt, freq="B")
        series = pd.Series(dates.normalize())

    if start:
        series = series[series >= pd.Timestamp(start)]
    if end:
        series = series[series <= pd.Timestamp(end)]

    out = sorted(set(series.dt.strftime("%Y-%m-%d").tolist()))
    return out


def get_latest_trading_date(
    tz: str = "Asia/Shanghai",
) -> str:
    try:
        now = datetime.now(ZoneInfo(tz))
    except Exception:
        now = datetime.now()
    today = now.date()
    end = today.strftime("%Y-%m-%d")
    start = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    calendar = get_trade_calendar(start=start, end=end)
    if calendar:
        return calendar[-1]
    # Fallback: assume weekdays are trading days.
    d = today
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def extract_fund_estimate(df: pd.DataFrame, symbol: str) -> Optional[dict]:
    if df is None or df.empty:
        return None

    code_col = None
    est_val_col = None
    est_pct_col = None
    for c in df.columns:
        if "基金代码" in c or c.lower() in ("code", "基金代码"):
            code_col = c
        if "估算值" in c and "估算" in c:
            est_val_col = c
        if "估算增长率" in c or "估算涨跌幅" in c:
            est_pct_col = c

    if code_col is None:
        return None

    row = df[df[code_col].astype(str) == str(symbol)]
    if row.empty:
        return None
    row = row.iloc[0]

    if est_pct_col is not None:
        pct = pd.to_numeric(str(row.get(est_pct_col)).replace("%", ""), errors="coerce")
        if pd.notna(pct):
            return {"kind": "pct", "value": float(pct) / 100.0}

    if est_val_col is not None:
        val = pd.to_numeric(row.get(est_val_col), errors="coerce")
        if pd.notna(val):
            return {"kind": "value", "value": float(val)}

    return None


def get_stock_spot() -> Optional[pd.DataFrame]:
    def fetch_em():
        return _clean_df(
            cached_call("stock_zh_a_spot_em", timeout=REQUEST_TIMEOUT, ttl=20)
        )

    def fetch_alt():
        return _clean_df(cached_call("stock_zh_a_spot", timeout=REQUEST_TIMEOUT, ttl=20))

    spot = None
    try:
        spot = fetch_em()
    except Exception:
        if has_func("stock_zh_a_spot"):
            try:
                spot = fetch_alt()
            except Exception:
                spot = None

    return spot


def get_stock_spot_v2() -> Optional[pd.DataFrame]:
    candidates = [
        ("stock_zh_a_spot_em", None),
        ("stock_zh_a_spot", None),
        ("stock_zh_a_spot_sina", None),
    ]
    for name, kwargs in candidates:
        if not has_func(name):
            continue
        try:
            return _clean_df(cached_call(name, kwargs=kwargs, timeout=REQUEST_TIMEOUT, ttl=20))
        except Exception:
            continue
    return None
def get_etf_spot_return_map() -> Optional[pd.Series]:
    if not has_func("fund_etf_spot_em"):
        return None

    try:
        spot = _clean_df(cached_call("fund_etf_spot_em", timeout=REQUEST_TIMEOUT, ttl=20))
    except Exception:
        return None

    code_col = None
    last_col = None
    prev_col = None
    iopv_col = None
    pct_col = None
    for c in spot.columns:
        if "代码" in c or c.lower() in ("code",):
            code_col = c
        if "最新价" in c or c.lower() in ("price", "latest"):
            last_col = c
        if "昨收" in c or "前收" in c or c.lower() in ("pre_close", "prev_close"):
            prev_col = c
        if "IOPV" in c or "实时估值" in c:
            iopv_col = c
        if "涨跌幅" in c or c.lower() in ("pct", "change_pct", "涨跌幅(%)"):
            pct_col = c

    if code_col is None:
        return None

    out = []
    for _, row in spot.iterrows():
        code = str(row[code_col]).zfill(6)
        ret = None
        if iopv_col is not None and prev_col is not None:
            iopv = pd.to_numeric(row.get(iopv_col), errors="coerce")
            prev = pd.to_numeric(row.get(prev_col), errors="coerce")
            if pd.notna(iopv) and pd.notna(prev) and prev > 0:
                ret = float((iopv - prev) / prev)
        if ret is None and last_col is not None and prev_col is not None:
            last = pd.to_numeric(row.get(last_col), errors="coerce")
            prev = pd.to_numeric(row.get(prev_col), errors="coerce")
            if pd.notna(last) and pd.notna(prev) and prev > 0:
                ret = float((last - prev) / prev)
        if ret is None and pct_col is not None:
            pct = pd.to_numeric(row.get(pct_col), errors="coerce")
            if pd.notna(pct):
                ret = float(pct) / 100.0
        if ret is None:
            continue
        out.append((code, ret))

    if not out:
        return None

    return pd.Series(dict(out))


def get_etf_spot_return_map_v2() -> Optional[pd.Series]:
    candidates = [
        ("fund_etf_spot_em", None),
        ("fund_etf_spot", None),
    ]

    def _parse_spot(spot: pd.DataFrame) -> Optional[pd.Series]:
        code_col = None
        last_col = None
        prev_col = None
        iopv_col = None
        pct_col = None
        for c in spot.columns:
            if _col_has(c, "??", "????", "????") or c.lower() in ("code",):
                code_col = c
            if _col_has(c, "???", "??") or c.lower() in ("price", "latest"):
                last_col = c
            if _col_has(c, "??", "??") or c.lower() in ("pre_close", "prev_close"):
                prev_col = c
            if _col_has(c, "IOPV", "????", "????"):
                iopv_col = c
            if _col_has(c, "???", "??", "??") or c.lower() in ("pct", "change_pct"):
                pct_col = c

        if code_col is None:
            return None

        out = []
        for _, row in spot.iterrows():
            code = str(row[code_col]).zfill(6)
            ret = None
            if iopv_col is not None and prev_col is not None:
                iopv = pd.to_numeric(row.get(iopv_col), errors="coerce")
                prev = pd.to_numeric(row.get(prev_col), errors="coerce")
                if pd.notna(iopv) and pd.notna(prev) and prev > 0:
                    ret = float((iopv - prev) / prev)
            if ret is None and last_col is not None and prev_col is not None:
                last = pd.to_numeric(row.get(last_col), errors="coerce")
                prev = pd.to_numeric(row.get(prev_col), errors="coerce")
                if pd.notna(last) and pd.notna(prev) and prev > 0:
                    ret = float((last - prev) / prev)
            if ret is None and pct_col is not None:
                pct = pd.to_numeric(row.get(pct_col), errors="coerce")
                if pd.notna(pct):
                    ret = float(pct) / 100.0
            if ret is None:
                continue
            out.append((code, ret))

        if not out:
            return None
        return pd.Series(dict(out))

    for name, kwargs in candidates:
        if not has_func(name):
            continue
        try:
            spot = _clean_df(cached_call(name, kwargs=kwargs, timeout=REQUEST_TIMEOUT, ttl=20))
        except Exception:
            continue
        parsed = _parse_spot(spot)
        if parsed is not None:
            return parsed

    return None
def get_index_spot_pct_change() -> Optional[pd.Series]:
    def fetch():
        spot = _clean_df(
            cached_call(
                "stock_zh_index_spot_em",
                kwargs={"symbol": "沪深重要指数"},
                timeout=REQUEST_TIMEOUT,
                ttl=20,
            )
        )
        code_col = "代码" if "代码" in spot.columns else None
        pct_col = "涨跌幅" if "涨跌幅" in spot.columns else None
        if code_col is None or pct_col is None:
            return None
        return spot.set_index(code_col)[pct_col] / 100.0

    try:
        data = fetch()
    except Exception:
        return None
    if data is None:
        return None
    return data


def get_index_spot_pct_change_v2() -> Optional[pd.Series]:
    candidates = [
        ("stock_zh_index_spot_em", {"symbol": "??????"}),
        ("stock_zh_index_spot", None),
        ("stock_zh_index_spot_sina", None),
    ]

    for name, kwargs in candidates:
        if not has_func(name):
            continue
        try:
            spot = _clean_df(cached_call(name, kwargs=kwargs, timeout=REQUEST_TIMEOUT, ttl=20))
        except Exception:
            continue

        code_col = None
        pct_col = None
        for c in spot.columns:
            if _col_has(c, "??") or c.lower() in ("code",):
                code_col = c
            if _col_has(c, "???", "??") or c.lower() in ("pct", "change_pct"):
                pct_col = c
        if code_col is None or pct_col is None:
            continue
        return spot.set_index(code_col)[pct_col] / 100.0

    return None


def _get_index_daily_return(index_code: str) -> float | None:
    candidates = [
        ("index_zh_a_hist", "daily"),
        ("stock_zh_index_daily_em", None),
    ]

    def _parse_hist(df: pd.DataFrame) -> float | None:
        df = _clean_df(df)
        date_col = None
        close_col = None
        for c in df.columns:
            if _col_has(c, "??") or c.lower() in ("date",):
                date_col = c
            if _col_has(c, "??") or c.lower() in ("close",):
                close_col = c
        if date_col is None or close_col is None:
            return None
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col, close_col]).sort_values(date_col)
        if len(df) < 2:
            return None
        prev = pd.to_numeric(df[close_col].iloc[-2], errors="coerce")
        last = pd.to_numeric(df[close_col].iloc[-1], errors="coerce")
        if pd.isna(prev) or pd.isna(last) or prev <= 0:
            return None
        return float((last - prev) / prev)

    for name, mode in candidates:
        if not has_func(name):
            continue
        try:
            if name == "index_zh_a_hist":
                code = index_code
                if code.lower().startswith(("sh", "sz")) and len(code) >= 8:
                    code = code[2:]
                df = cached_call(
                    name,
                    kwargs={
                        "symbol": code,
                        "period": mode,
                    },
                    timeout=REQUEST_TIMEOUT,
                    ttl=300,
                )
            else:
                df = cached_call(name, kwargs={"symbol": index_code}, timeout=REQUEST_TIMEOUT, ttl=300)
            ret = _parse_hist(df)
            if ret is not None:
                return ret
        except Exception:
            continue

    return None

def get_industry_spot_pct_change() -> Optional[pd.Series]:
    if not has_func("stock_board_industry_spot_em"):
        return None

    def fetch():
        spot = _clean_df(
            cached_call("stock_board_industry_spot_em", timeout=REQUEST_TIMEOUT, ttl=20)
        )
        name_col = None
        pct_col = None
        for c in spot.columns:
            if "板块" in c or "行业" in c or c.lower() in ("name", "板块名称"):
                name_col = c
            if "涨跌幅" in c or c.lower() in ("pct", "change_pct", "涨跌幅(%)"):
                pct_col = c
        if name_col is None or pct_col is None:
            return None
        return spot.set_index(name_col)[pct_col] / 100.0

    try:
        data = fetch()
    except Exception:
        return None
    if data is None:
        return None
    return data


def get_industry_spot_pct_change_v2() -> Optional[pd.Series]:
    candidates = [
        ("stock_board_industry_spot_em", None),
        ("stock_board_industry_spot", None),
    ]

    for name, kwargs in candidates:
        if not has_func(name):
            continue
        try:
            spot = _clean_df(cached_call(name, kwargs=kwargs, timeout=REQUEST_TIMEOUT, ttl=20))
        except Exception:
            continue

        name_col = None
        pct_col = None
        for c in spot.columns:
            if _col_has(c, "??", "??", "??", "????") or c.lower() in ("name",):
                name_col = c
            if _col_has(c, "???", "??") or c.lower() in ("pct", "change_pct"):
                pct_col = c
        if name_col is None or pct_col is None:
            continue
        return spot.set_index(name_col)[pct_col] / 100.0

    return None


def _get_industry_daily_return(industry_name: str) -> float | None:
    candidates = [
        ("stock_board_industry_hist_em", None),
        ("stock_board_industry_hist", None),
    ]

    def _parse_hist(df: pd.DataFrame) -> float | None:
        df = _clean_df(df)
        date_col = None
        close_col = None
        for c in df.columns:
            if _col_has(c, "??") or c.lower() in ("date",):
                date_col = c
            if _col_has(c, "??") or c.lower() in ("close",):
                close_col = c
        if date_col is None or close_col is None:
            return None
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col, close_col]).sort_values(date_col)
        if len(df) < 2:
            return None
        prev = pd.to_numeric(df[close_col].iloc[-2], errors="coerce")
        last = pd.to_numeric(df[close_col].iloc[-1], errors="coerce")
        if pd.isna(prev) or pd.isna(last) or prev <= 0:
            return None
        return float((last - prev) / prev)

    for name, _ in candidates:
        if not has_func(name):
            continue
        try:
            df = cached_call(name, kwargs={"symbol": industry_name}, timeout=REQUEST_TIMEOUT, ttl=300)
            ret = _parse_hist(df)
            if ret is not None:
                return ret
        except Exception:
            continue

    return None

def start_background_refresh(interval: int | None = None) -> None:
    global _bg_started
    if _bg_started or not BG_REFRESH_ENABLED:
        return
    _bg_started = True
    refresh_interval = interval or BG_REFRESH_INTERVAL_SEC

    def loop() -> None:
        while True:
            try:
                get_fund_value_estimation()
                get_index_spot_pct_change()
                get_industry_spot_pct_change()
                get_etf_spot_return_map()
                get_stock_spot()
            except Exception:
                pass
            threading.Event().wait(refresh_interval)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()


def get_stock_industry(code: str) -> Optional[str]:
    if not has_func("stock_individual_info_em"):
        return None
    try:
        info = _clean_df(
            cached_call(
                "stock_individual_info_em",
                kwargs={"symbol": code},
                timeout=REQUEST_TIMEOUT,
                ttl=300,
            )
        )
    except Exception:
        return None

    industry = None
    for c in info.columns:
        if "行业" in c and not info[c].isna().all():
            industry = str(info[c].iloc[0])
            break
    if industry is None and info.shape[1] >= 2:
        key_col = info.columns[0]
        val_col = info.columns[1]
        mask = info[key_col].astype(str).str.contains("行业", na=False)
        if mask.any():
            industry = str(info.loc[mask, val_col].iloc[0])
    return industry


def get_stock_industry_v2(code: str) -> Optional[str]:
    if not has_func("stock_individual_info_em"):
        return None
    try:
        info = _clean_df(
            cached_call(
                "stock_individual_info_em",
                kwargs={"symbol": code},
                timeout=REQUEST_TIMEOUT,
                ttl=300,
            )
        )
    except Exception:
        return None

    industry = None
    for c in info.columns:
        if _col_has(c, "行业") and not info[c].isna().all():
            industry = str(info[c].iloc[0])
            break
    if industry is None and info.shape[1] >= 2:
        key_col = info.columns[0]
        val_col = info.columns[1]
        mask = info[key_col].astype(str).str.contains("行业", na=False)
        if mask.any():
            industry = str(info.loc[mask, val_col].iloc[0])
    return industry


def _spot_series(spot: pd.DataFrame) -> pd.Series:
    code_col = None
    pct_col = None
    for c in spot.columns:
        if "代码" in c or c.lower() in ("code", "股票代码"):
            code_col = c
        if "涨跌幅" in c or c.lower() in ("pct", "change_pct", "涨跌幅(%)"):
            pct_col = c
    if code_col is None or pct_col is None:
        raise RuntimeError("股票实时字段识别失败")
    return spot.set_index(code_col)[pct_col] / 100.0


def _spot_series_v2(spot: pd.DataFrame) -> pd.Series:
    code_col = None
    pct_col = None
    for c in spot.columns:
        if _col_has(c, "代码") or c.lower() in ("code", "stock_code"):
            code_col = c
        if _col_has(c, "涨跌幅", "涨跌") or c.lower() in ("pct", "change_pct"):
            pct_col = c
    if code_col is None or pct_col is None:
        raise RuntimeError("股票实时字段识别失败")
    return spot.set_index(code_col)[pct_col] / 100.0


def estimate_with_holdings(symbol: str, index_ret: float | None) -> tuple[float, float, str, bool]:
    holdings = get_fund_holdings(symbol)
    if holdings is None or holdings.empty:
        return (index_ret or 0.0, 0.0, "index_only", False)

    holdings = parse_latest_quarter(holdings)

    code_col = None
    weight_col = None
    for c in holdings.columns:
        if _col_has(c, "????") or c.lower() in ("stock_code", "code"):
            code_col = c
        if _col_has(c, "?????", "????") or c.lower() in ("weight", "ratio"):
            weight_col = c
    if code_col is None or weight_col is None:
        return (index_ret or 0.0, 0.0, "index_only", False)

    df = holdings[[code_col, weight_col]].copy()
    df.columns = ["code", "weight"]
    df["code"] = df["code"].astype(str).str.zfill(6)
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df = df.dropna(subset=["code", "weight"])

    total_weight = float(df["weight"].sum())
    if total_weight <= 0:
        return (index_ret or 0.0, 0.0, "index_only", False)

    etf_spot = get_etf_spot_return_map_v2()
    stock_spot = get_stock_spot_v2()
    stock_ret = _spot_series_v2(stock_spot) if stock_spot is not None else None
    industry_spot = get_industry_spot_pct_change_v2()
    realtime_used = any([etf_spot is not None, stock_ret is not None, industry_spot is not None])

    ret_sum = 0.0
    direct_weight = 0.0
    missing_weight = 0.0

    for _, row in df.iterrows():
        code = str(row["code"]).zfill(6)
        weight = float(row["weight"]) / 100.0

        if etf_spot is not None and code in etf_spot.index:
            ret_sum += weight * float(etf_spot.loc[code])
            direct_weight += weight
            continue

        if stock_ret is not None and code in stock_ret.index:
            ret_sum += weight * float(stock_ret.loc[code])
            direct_weight += weight
            continue

        ind_ret = None
        if industry_spot is not None:
            industry = get_stock_industry_v2(code)
            if industry and industry in industry_spot.index:
                ind_ret = float(industry_spot.loc[industry])

        if ind_ret is not None:
            ret_sum += weight * ind_ret
        else:
            missing_weight += weight

    residual_weight = max(0.0, 1.0 - total_weight / 100.0)
    missing_weight += residual_weight

    source = "holdings+industry"
    if missing_weight > 0 and index_ret is not None:
        ret_sum += missing_weight * index_ret
        source = "holdings+industry+index"

    coverage = direct_weight / (total_weight / 100.0) if total_weight > 0 else 0.0
    return (ret_sum, coverage, source, realtime_used)
def estimate_with_industry_allocation(
    symbol: str, index_ret: float | None
) -> tuple[float, float, str, bool]:
    alloc = get_fund_industry_allocation(symbol)
    if alloc is None or alloc.empty:
        return (index_ret or 0.0, 0.0, "index_only", False)

    alloc = parse_latest_date(alloc)

    industry_col = None
    weight_col = None
    for c in alloc.columns:
        if _col_has(c, "??"):
            industry_col = c
        if _col_has(c, "?????", "????") or c.lower() in ("weight", "ratio"):
            weight_col = c
    if industry_col is None or weight_col is None:
        return (index_ret or 0.0, 0.0, "index_only", False)

    df = alloc[[industry_col, weight_col]].copy()
    df.columns = ["industry", "weight"]
    df["industry"] = df["industry"].astype(str)
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df = df.dropna(subset=["industry", "weight"])

    total_weight = float(df["weight"].sum())
    if total_weight <= 0:
        return (index_ret or 0.0, 0.0, "index_only", False)

    industry_spot = get_industry_spot_pct_change_v2()
    realtime_used = industry_spot is not None
    source_base = "industry"
    if industry_spot is None:
        ret_map = {}
        for industry in df["industry"].unique().tolist():
            ret = _get_industry_daily_return(str(industry))
            if ret is not None:
                ret_map[str(industry)] = ret
        if not ret_map:
            return (index_ret or 0.0, 0.0, "index_only", False)
        industry_spot = pd.Series(ret_map)
        source_base = "industry_daily"

    ret_sum = 0.0
    covered = 0.0
    missing_weight = 0.0
    for _, row in df.iterrows():
        industry = str(row["industry"])
        weight = float(row["weight"]) / 100.0
        if industry in industry_spot.index:
            ret_sum += weight * float(industry_spot.loc[industry])
            covered += weight
        else:
            missing_weight += weight

    residual_weight = max(0.0, 1.0 - total_weight / 100.0)
    missing_weight += residual_weight

    source = source_base
    if missing_weight > 0 and index_ret is not None:
        ret_sum += missing_weight * index_ret
        source = f"{source_base}+index"

    coverage = covered / (total_weight / 100.0) if total_weight > 0 else 0.0
    return (ret_sum, coverage, source, realtime_used)
def get_fund_holdings(symbol: str) -> Optional[pd.DataFrame]:
    if not has_func("fund_portfolio_hold_em"):
        return None
    years = [pd.Timestamp.now().year, pd.Timestamp.now().year - 1]
    for year in years:
        try:
            df = _clean_df(
                cached_call(
                    "fund_portfolio_hold_em",
                    kwargs={"symbol": symbol, "date": str(year)},
                    timeout=REQUEST_TIMEOUT,
                    ttl=6 * 3600,
                )
            )
        except Exception:
            continue
        if df is None or df.empty:
            continue
        return df
    return None


def get_fund_industry_allocation(symbol: str) -> Optional[pd.DataFrame]:
    if not has_func("fund_portfolio_industry_allocation_em"):
        return None
    years = [pd.Timestamp.now().year, pd.Timestamp.now().year - 1]
    for year in years:
        try:
            df = _clean_df(
                cached_call(
                    "fund_portfolio_industry_allocation_em",
                    kwargs={"symbol": symbol, "date": str(year)},
                    timeout=REQUEST_TIMEOUT,
                    ttl=6 * 3600,
                )
            )
        except Exception:
            continue
        if df is None or df.empty:
            continue
        return df
    return None


def parse_latest_quarter(df: pd.DataFrame) -> pd.DataFrame:
    quarter_col = None
    for c in df.columns:
        if _col_has(c, "??"):
            quarter_col = c
            break
    if quarter_col is None:
        return df

    def _parse(text: str) -> Optional[tuple[int, int]]:
        if not isinstance(text, str):
            return None
        m = re.search(r"(\d{4})?\s*([1-4])??", text)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2))

    df = df.copy()
    df["_q"] = df[quarter_col].apply(_parse)
    df = df.dropna(subset=["_q"])
    if df.empty:
        return df
    df = df.sort_values("_q")
    latest = df["_q"].iloc[-1]
    return df[df["_q"] == latest]
def parse_latest_date(df: pd.DataFrame) -> pd.DataFrame:
    date_col = None
    for c in df.columns:
        if _col_has(c, "????", "????") or c.lower() in ("date", "??"):
            date_col = c
            break
    if date_col is None:
        return df
    df = df.copy()
    df["_d"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["_d"])
    if df.empty:
        return df
    latest = df["_d"].max()
    return df[df["_d"] == latest]
def _eastmoney_estimate(
    est_df: Optional[pd.DataFrame], code: str, last_nav: float | None
) -> tuple[float | None, float | None, str | None]:
    if est_df is None:
        return (None, None, None)
    est_override = extract_fund_estimate(est_df, code)
    if est_override is None:
        return (None, None, None)
    if est_override["kind"] == "value" and last_nav:
        est_ret = (float(est_override["value"]) / last_nav) - 1.0
        est_nav = float(est_override["value"])
        return (est_ret, est_nav, "eastmoney_est_value")
    if est_override["kind"] == "pct":
        est_ret = float(est_override["value"])
        est_nav = last_nav * (1.0 + est_ret) if last_nav is not None else None
        return (est_ret, est_nav, "eastmoney_est_pct")
    return (None, None, None)




def _http_get_text(url: str, params: dict | None = None, headers: dict | None = None) -> str | None:
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.text
    except Exception:
        return None


def _tiantian_estimate(code: str) -> dict | None:
    url = f"https://fundgz.1234567.com.cn/js/{code}.js"
    text = _http_get_text(url, headers={"Referer": "https://fund.eastmoney.com/"})
    if not text:
        return None
    m = re.search(r"jsonpgz\((\{.*?\})\)", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except Exception:
        return None
    try:
        est_nav = float(data.get("gsz")) if data.get("gsz") else None
        est_ret = float(data.get("gszzl")) / 100.0 if data.get("gszzl") else None
    except Exception:
        return None
    if est_nav is None and est_ret is None:
        return None
    return {
        "est_nav": est_nav,
        "est_return": est_ret,
        "time": data.get("gztime"),
    }


def _parse_eastmoney_holdings_html(html_text: str) -> list[tuple[str, float]]:
    rows = re.findall(r"<tr>.*?</tr>", html_text, flags=re.S)
    out: list[tuple[str, float]] = []
    for row in rows:
        code_m = re.search(r">(\d{6})<", row)
        if not code_m:
            continue
        pct_m = re.findall(r">\s*([0-9.]+)\s*%\s*<", row)
        if not pct_m:
            continue
        try:
            weight = float(pct_m[-1])
        except Exception:
            continue
        out.append((code_m.group(1), weight))
    return out


def _eastmoney_holdings(code: str) -> list[tuple[str, float]] | None:
    try:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception:
        now = datetime.now()
    year = now.year
    month = now.month
    url = "https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
    params = {
        "type": "jjcc",
        "code": code,
        "topline": "10",
        "year": str(year),
        "month": str(month),
    }
    text = _http_get_text(url, params=params, headers={"Referer": "https://fundf10.eastmoney.com/"})
    if not text:
        return None
    m = re.search(r'content:"(.*?)"', text, flags=re.S)
    if not m:
        return None
    raw = m.group(1)
    try:
        unescaped = bytes(raw, "utf-8").decode("unicode_escape")
    except Exception:
        unescaped = raw
    unescaped = unescaped.replace("\\/", "/")
    unescaped = html_lib.unescape(unescaped)
    holdings = _parse_eastmoney_holdings_html(unescaped)
    return holdings or None


def _normalize_code(code: str) -> str:
    c = code.strip().upper()
    if c.startswith("SH") or c.startswith("SZ"):
        c = c[2:]
    if c.endswith(".SH") or c.endswith(".SZ"):
        c = c[:-3]
    return c.zfill(6)


def _tencent_quote_returns(codes: list[str]) -> dict[str, float]:
    if not codes:
        return {}
    symbols = []
    for c in codes:
        base = _normalize_code(c)
        prefix = "sh" if base.startswith("6") else "sz"
        symbols.append(f"{prefix}{base}")
    url = "https://qt.gtimg.cn/q=" + ",".join(symbols)
    text = _http_get_text(url, headers={"Referer": "https://qt.qq.com/"})
    if not text:
        return {}
    out: dict[str, float] = {}
    for line in text.split(";"):
        if not line.strip():
            continue
        m = re.search(r'v_([a-zA-Z0-9]+)="(.*)"', line)
        if not m:
            continue
        data = m.group(2).split("~")
        if len(data) < 5:
            continue
        try:
            price = float(data[3])
            prev = float(data[4])
            if prev <= 0:
                continue
            ret = (price - prev) / prev
        except Exception:
            continue
        code6 = _normalize_code(data[2]) if len(data) > 2 else _normalize_code(m.group(1))
        out[code6] = ret
    return out


def _estimate_plan_b(code: str, last_nav: float | None) -> dict | None:
    holdings = _eastmoney_holdings(code)
    if holdings:
        codes = [c for c, _ in holdings]
        quote_map = _tencent_quote_returns(codes)
        ret_sum = 0.0
        covered = 0.0
        total_weight = 0.0
        for c, w in holdings:
            total_weight += w
            ret = quote_map.get(_normalize_code(c))
            if ret is None:
                continue
            weight = w / 100.0
            ret_sum += weight * ret
            covered += weight
        if total_weight > 0 and covered > 0:
            coverage = covered / (total_weight / 100.0)
            if coverage >= 0.4:
                est_nav = last_nav * (1.0 + ret_sum) if last_nav is not None else None
                return {
                    "est_return": ret_sum,
                    "est_nav": est_nav,
                    "source": "planb_holdings_tencent",
                    "coverage": coverage,
                    "is_realtime": True,
                }
    tt = _tiantian_estimate(code)
    if tt is not None:
        est_nav = tt.get("est_nav")
        est_ret = tt.get("est_return")
        if est_ret is None and est_nav is not None and last_nav:
            est_ret = est_nav / last_nav - 1.0
        return {
            "est_return": est_ret,
            "est_nav": est_nav,
            "source": "planb_tiantian",
            "coverage": None,
            "is_realtime": True,
        }
    return None

def _model_estimate(
    code: str,
    last_nav: float | None,
    index_ret: float | None,
    index_realtime: bool,
) -> tuple[float | None, float | None, str | None, float | None, bool]:
    est_ret, coverage, source, realtime_used = estimate_with_holdings(code, index_ret)
    if coverage < 0.6:
        ind_ret, ind_cov, ind_src, ind_realtime = estimate_with_industry_allocation(code, index_ret)
        # 估值公开
        est_ret = est_ret * coverage + ind_ret * (1.0 - coverage)
        source = f"{source}+{ind_src}"
        coverage = max(coverage, ind_cov)
        realtime_used = realtime_used or ind_realtime
    realtime_used = realtime_used or index_realtime
    est_nav = last_nav * (1.0 + est_ret) if last_nav is not None else None
    return (est_ret, est_nav, source, coverage, realtime_used)


def _infer_index_code_from_name(name: str | None) -> str | None:
    if not name:
        return None
    upper = name.upper()
    if "沪深300" in name or "HS300" in upper:
        return "000300"
    if "中证500" in name or "ZZ500" in upper:
        return "000905"
    if "中证1000" in name or "ZZ1000" in upper:
        return "000852"
    if "中证A500" in name or "A500" in upper:
        return "000510"
    if "上证50" in name or "SSE50" in upper:
        return "000016"
    if "上证180" in name or "SSE180" in upper:
        return "000010"
    if "深证成指" in name or "深证成份" in name or "SZCZ" in upper or "SZCI" in upper:
        return "399001"
    if "创业板" in name or "CYB" in upper:
        return "399006"
    if "科创50" in name or "STAR50" in upper:
        return "000688"
    return None


def _lookup_index_ret(index_spot: pd.Series, index_code: str) -> float | None:
    candidates = []
    code = index_code.strip()
    candidates.append(code)
    if code.lower().startswith(("sh", "sz")) and len(code) >= 8:
        candidates.append(code[2:])
    if code.endswith((".SH", ".SZ")) and len(code) >= 9:
        candidates.append(code[:-3])
    if len(code) == 6:
        candidates.append(f"{code}.SH")
        candidates.append(f"{code}.SZ")
        candidates.append(f"sh{code}")
        candidates.append(f"sz{code}")

    for c in candidates:
        if c in index_spot.index:
            return float(index_spot.loc[c])
    return None


def estimate_fund(
    code: str,
    index_code: str | None = None,
    source: str = "model",
    name_hint: str | None = None,
) -> dict:
    fund_df = get_fund_nav_daily(code)
    last_nav = float(fund_df["nav"].iloc[-1]) if not fund_df.empty else None

    est_df = get_fund_value_estimation()
    fund_name = None
    if est_df is not None:
        code_col = None
        name_col = None
        for c in est_df.columns:
            if _col_has(c, "基金代码", "代码") or c.lower() in ("code",):
                code_col = c
            if _col_has(c, "基金名称", "名称") or c.lower() in ("name",):
                name_col = c
        if code_col is not None and name_col is not None:
            row = est_df[est_df[code_col].astype(str) == str(code)]
            if not row.empty:
                fund_name = str(row.iloc[0][name_col])

    if fund_name is None:
        name_df = get_all_fund_names()
        if name_df is not None:
            code_col = None
            name_col = None
            for c in name_df.columns:
                if _col_has(c, "基金代码", "代码") or c.lower() in ("code",):
                    code_col = c
                if _col_has(c, "基金名称", "名称") or c.lower() in ("name",):
                    name_col = c
            if code_col is not None and name_col is not None:
                row = name_df[name_df[code_col].astype(str) == str(code)]
                if not row.empty:
                    fund_name = str(row.iloc[0][name_col])

    if fund_name is None and name_hint:
        fund_name = name_hint

    if index_code is None:
        index_code = _infer_index_code_from_name(fund_name or name_hint)

    index_ret = None
    index_realtime = False
    if index_code:
        index_spot = get_index_spot_pct_change_v2()
        if index_spot is None:
            index_spot = get_index_spot_pct_change()
        if index_spot is not None:
            index_ret = _lookup_index_ret(index_spot, index_code)
            if index_ret is not None:
                index_realtime = True
        if index_ret is None:
            index_ret = _get_index_daily_return(index_code)

    if index_ret is None and not fund_df.empty and 'fund_ret' in fund_df.columns:
        try:
            index_ret = float(fund_df['fund_ret'].iloc[-1])
        except Exception:
            index_ret = None

    em_ret, em_nav, em_source = _eastmoney_estimate(est_df, code, last_nav)
    model_ret, model_nav, model_source, model_cov, model_realtime = _model_estimate(code, last_nav, index_ret, index_realtime)

    preferred_source = source
    if source == "auto":
        if em_ret is not None:
            preferred_source = "eastmoney"
        else:
            preferred_source = "model"

    if preferred_source == "planb":
        planb = _estimate_plan_b(code, last_nav)
        if planb and planb.get("is_realtime"):
            est_ret = planb.get("est_return")
            est_nav = planb.get("est_nav")
            final_source = planb.get("source")
            coverage = planb.get("coverage")
            is_realtime = True
            fallback_used = True
            fallback_source = planb.get("source")
        else:
            est_ret, est_nav, final_source, coverage = model_ret, model_nav, model_source, model_cov
            is_realtime = bool(model_realtime)
    elif preferred_source == "eastmoney":
        est_ret, est_nav, final_source, coverage = em_ret, em_nav, em_source, 1.0
        is_realtime = em_ret is not None
    elif preferred_source == "model":
        est_ret, est_nav, final_source, coverage = model_ret, model_nav, model_source, model_cov
        is_realtime = bool(model_realtime)
    else:
        if em_ret is not None:
            est_ret, est_nav, final_source, coverage = em_ret, em_nav, em_source, 1.0
            is_realtime = True
        else:
            est_ret, est_nav, final_source, coverage = model_ret, model_nav, model_source, model_cov
            is_realtime = bool(model_realtime)

    fallback_used = False
    fallback_source = None
    if not is_realtime:
        planb = _estimate_plan_b(code, last_nav)
        if planb and planb.get("is_realtime"):
            est_ret = planb.get("est_return")
            est_nav = planb.get("est_nav")
            final_source = planb.get("source")
            coverage = planb.get("coverage")
            is_realtime = True
            fallback_used = True
            fallback_source = planb.get("source")

    return {
        "code": code,
        "name": fund_name,
        "last_nav": last_nav,
        "est_return": est_ret,
        "est_nav": est_nav,
        "source": final_source,
        "coverage": coverage,
        "preferred_source": preferred_source,
        "est_return_em": em_ret,
        "est_nav_em": em_nav,
        "source_em": em_source,
        "est_return_model": model_ret,
        "est_nav_model": model_nav,
        "source_model": model_source,
        "coverage_model": model_cov,
        "is_realtime": is_realtime,
        "fallback_used": fallback_used,
        "fallback_source": fallback_source,
    }
