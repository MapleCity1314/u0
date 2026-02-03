import re
from typing import Optional

import pandas as pd

from services.modules.akshare import cached_call, has_func

REQUEST_TIMEOUT = 25


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


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
        if "净值日期" in c or c.lower() in ("date", "日期"):
            date_col = c
        if "单位净值" in c or c.lower() in ("unit_net_value", "nav"):
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

    df = cached_call("fund_value_estimation_em", timeout=REQUEST_TIMEOUT, ttl=30)
    return _clean_df(df)


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


def estimate_with_holdings(symbol: str, index_ret: float | None) -> tuple[float, float, str]:
    holdings = get_fund_holdings(symbol)
    if holdings is None or holdings.empty:
        return (index_ret or 0.0, 0.0, "index_only")

    holdings = parse_latest_quarter(holdings)

    code_col = None
    weight_col = None
    for c in holdings.columns:
        if "股票代码" in c or c.lower() in ("stock_code", "code"):
            code_col = c
        if "占净值比例" in c or "持仓占比" in c or c.lower() in ("weight", "ratio"):
            weight_col = c
    if code_col is None or weight_col is None:
        return (index_ret or 0.0, 0.0, "index_only")

    df = holdings[[code_col, weight_col]].copy()
    df.columns = ["code", "weight"]
    df["code"] = df["code"].astype(str).str.zfill(6)
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df = df.dropna(subset=["code", "weight"])

    total_weight = float(df["weight"].sum())
    if total_weight <= 0:
        return (index_ret or 0.0, 0.0, "index_only")

    etf_spot = get_etf_spot_return_map()
    stock_spot = get_stock_spot()
    stock_ret = _spot_series(stock_spot) if stock_spot is not None else None
    industry_spot = get_industry_spot_pct_change()

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
            industry = get_stock_industry(code)
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
    return (ret_sum, coverage, source)


def estimate_with_industry_allocation(
    symbol: str, index_ret: float | None
) -> tuple[float, float, str]:
    alloc = get_fund_industry_allocation(symbol)
    if alloc is None or alloc.empty:
        return (index_ret or 0.0, 0.0, "index_only")

    alloc = parse_latest_date(alloc)

    industry_col = None
    weight_col = None
    for c in alloc.columns:
        if "行业" in c:
            industry_col = c
        if "占净值比例" in c or "持仓占比" in c or c.lower() in ("weight", "ratio"):
            weight_col = c
    if industry_col is None or weight_col is None:
        return (index_ret or 0.0, 0.0, "index_only")

    df = alloc[[industry_col, weight_col]].copy()
    df.columns = ["industry", "weight"]
    df["industry"] = df["industry"].astype(str)
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df = df.dropna(subset=["industry", "weight"])

    total_weight = float(df["weight"].sum())
    if total_weight <= 0:
        return (index_ret or 0.0, 0.0, "index_only")

    industry_spot = get_industry_spot_pct_change()
    if industry_spot is None:
        return (index_ret or 0.0, 0.0, "index_only")

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

    source = "industry"
    if missing_weight > 0 and index_ret is not None:
        ret_sum += missing_weight * index_ret
        source = "industry+index"

    coverage = covered / (total_weight / 100.0) if total_weight > 0 else 0.0
    return (ret_sum, coverage, source)


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
        if "季度" in c:
            quarter_col = c
            break
    if quarter_col is None:
        return df

    def _parse(text: str) -> Optional[tuple[int, int]]:
        if not isinstance(text, str):
            return None
        m = re.search(r"(\d{4})年\s*([1-4])季度", text)
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
        if "截止时间" in c or c.lower() in ("date", "截止日期"):
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


def _model_estimate(
    code: str, last_nav: float | None, index_ret: float | None
) -> tuple[float | None, float | None, str | None, float | None]:
    est_ret, coverage, source = estimate_with_holdings(code, index_ret)
    if coverage < 0.6:
        ind_ret, ind_cov, ind_src = estimate_with_industry_allocation(code, index_ret)
        est_ret = est_ret * coverage + ind_ret * (1.0 - coverage)
        source = f"{source}+{ind_src}"
        coverage = max(coverage, ind_cov)
    est_nav = last_nav * (1.0 + est_ret) if last_nav is not None else None
    return (est_ret, est_nav, source, coverage)


def estimate_fund(
    code: str, index_code: str | None = None, source: str = "auto"
) -> dict:
    fund_df = get_fund_nav_daily(code)
    last_nav = float(fund_df["nav"].iloc[-1]) if not fund_df.empty else None

    index_ret = None
    if index_code:
        index_spot = get_index_spot_pct_change()
        if index_spot is not None and index_code in index_spot.index:
            index_ret = float(index_spot.loc[index_code])

    est_df = get_fund_value_estimation()
    fund_name = None
    if est_df is not None:
        code_col = None
        name_col = None
        for c in est_df.columns:
            if "基金代码" in c or c.lower() in ("code", "基金代码"):
                code_col = c
            if "基金名称" in c or c.lower() in ("name", "基金名称"):
                name_col = c
        if code_col is not None and name_col is not None:
            row = est_df[est_df[code_col].astype(str) == str(code)]
            if not row.empty:
                fund_name = str(row.iloc[0][name_col])

    em_ret, em_nav, em_source = _eastmoney_estimate(est_df, code, last_nav)
    model_ret, model_nav, model_source, model_cov = _model_estimate(code, last_nav, index_ret)

    preferred_source = source
    if source == "auto":
        if em_ret is not None:
            preferred_source = "eastmoney"
        else:
            preferred_source = "model"

    if preferred_source == "eastmoney":
        est_ret, est_nav, final_source, coverage = em_ret, em_nav, em_source, 1.0
    elif preferred_source == "model":
        est_ret, est_nav, final_source, coverage = model_ret, model_nav, model_source, model_cov
    else:
        if em_ret is not None:
            est_ret, est_nav, final_source, coverage = em_ret, em_nav, em_source, 1.0
        else:
            est_ret, est_nav, final_source, coverage = model_ret, model_nav, model_source, model_cov

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
    }
