import re
import time
import threading
from typing import Any, Optional, Tuple

import akshare as ak
import pandas as pd

from config import FUNDS, MIN_DIRECT_COVERAGE, USE_EASTMONEY_ESTIMATE, USE_INDEX_FALLBACK

SLEEP_SEC = 60
MAX_RETRIES = 3
RETRY_DELAY = 2.0
API_CALL_DELAY = 1.0
REQUEST_TIMEOUT = 30

# Caches
HOLDINGS_CACHE: dict[str, pd.DataFrame] = {}
INDUSTRY_ALLOC_CACHE: dict[str, pd.DataFrame] = {}
INDUSTRY_CACHE: dict[str, Optional[str]] = {}
INDEX_SPOT_CACHE: Optional[pd.Series] = None
STOCK_SPOT_CACHE: Optional[pd.DataFrame] = None
INDUSTRY_SPOT_CACHE: Optional[pd.Series] = None
FUND_EST_CACHE: Optional[pd.DataFrame] = None


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


def get_fund_nav_daily(symbol: str) -> pd.DataFrame:
    for attempt in range(MAX_RETRIES):
        try:
            print(f"  获取基金 {symbol} 净值数据...", end="", flush=True)
            df = call_with_timeout(
                ak.fund_open_fund_info_em,
                kwargs={"symbol": symbol, "indicator": "单位净值走势"},
                timeout=REQUEST_TIMEOUT,
            )
            print(" ✓")
            df = df.copy()
            df.columns = [c.strip() for c in df.columns]

            date_col = None
            nav_col = None
            for c in df.columns:
                if "净值日期" in c or c.lower() in ("date", "日期"):
                    date_col = c
                if "单位净值" in c or c.lower() in ("unit_net_value", "nav"):
                    nav_col = c

            if date_col is None or nav_col is None:
                raise RuntimeError(f"基金净值字段识别失败，当前列：{df.columns.tolist()}")

            df[date_col] = pd.to_datetime(df[date_col])
            df = df.sort_values(date_col).rename(columns={date_col: "date", nav_col: "nav"})
            df["fund_ret"] = df["nav"].pct_change()
            df = df.dropna(subset=["fund_ret"])
            return df[["date", "nav", "fund_ret"]]
        except Exception:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f" ✗ 重试中({attempt + 1}/{MAX_RETRIES})...", end="", flush=True)
                time.sleep(wait_time)
            else:
                print(" ✗ 失败")
                raise

    raise RuntimeError(f"get_fund_nav_daily failed after {MAX_RETRIES} attempts")


def _parse_quarter(text: str) -> Optional[Tuple[int, int]]:
    if not isinstance(text, str):
        return None
    m = re.search(r"(\d{4})年\s*([1-4])季度", text)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def get_latest_holdings(symbol: str) -> Optional[pd.DataFrame]:
    if symbol in HOLDINGS_CACHE:
        return HOLDINGS_CACHE[symbol]

    years = [pd.Timestamp.now().year, pd.Timestamp.now().year - 1]
    last_df = None
    for year in years:
        for attempt in range(MAX_RETRIES):
            try:
                print(f"  获取基金 {symbol} 持仓({year})...", end="", flush=True)
                df = call_with_timeout(
                    ak.fund_portfolio_hold_em,
                    kwargs={"symbol": symbol, "date": str(year)},
                    timeout=REQUEST_TIMEOUT,
                )
                print(" ✓")
                if df is None or df.empty:
                    last_df = None
                    break
                df = df.copy()
                df.columns = [c.strip() for c in df.columns]
                last_df = df
                break
            except Exception:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f" ✗ 重试中({attempt + 1}/{MAX_RETRIES})...", end="", flush=True)
                    time.sleep(wait_time)
                else:
                    print(" ✗ 失败")
                    last_df = None
        if last_df is not None and not last_df.empty:
            break

    if last_df is None or last_df.empty:
        HOLDINGS_CACHE[symbol] = None
        return None

    quarter_col = None
    code_col = None
    name_col = None
    weight_col = None
    for c in last_df.columns:
        if "季度" in c:
            quarter_col = c
        if "股票代码" in c or c.lower() in ("stock_code", "code"):
            code_col = c
        if "股票名称" in c or c.lower() in ("stock_name", "name"):
            name_col = c
        if "占净值比例" in c or "持仓占比" in c or c.lower() in ("weight", "ratio"):
            weight_col = c

    if code_col is None or weight_col is None:
        HOLDINGS_CACHE[symbol] = None
        return None

    if quarter_col is not None:
        last_df["_q"] = last_df[quarter_col].apply(_parse_quarter)
        last_df = last_df.dropna(subset=["_q"])
        if not last_df.empty:
            last_df = last_df.sort_values("_q")
            latest = last_df["_q"].iloc[-1]
            last_df = last_df[last_df["_q"] == latest]

    out = last_df[[code_col, weight_col]].copy()
    if name_col is not None:
        out["name"] = last_df[name_col].astype(str)
    out.columns = ["code", "weight", "name"] if name_col is not None else ["code", "weight"]
    out["code"] = out["code"].astype(str).str.zfill(6)
    out["weight"] = pd.to_numeric(out["weight"], errors="coerce")
    out = out.dropna(subset=["code", "weight"]).copy()

    HOLDINGS_CACHE[symbol] = out
    return out


def get_fund_industry_allocation(symbol: str) -> Optional[pd.DataFrame]:
    if symbol in INDUSTRY_ALLOC_CACHE:
        return INDUSTRY_ALLOC_CACHE[symbol]
    if not hasattr(ak, "fund_portfolio_industry_allocation_em"):
        INDUSTRY_ALLOC_CACHE[symbol] = None
        return None

    years = [pd.Timestamp.now().year, pd.Timestamp.now().year - 1]
    last_df = None
    for year in years:
        for attempt in range(MAX_RETRIES):
            try:
                print(f"  获取基金 {symbol} 行业配置({year})...", end="", flush=True)
                df = call_with_timeout(
                    ak.fund_portfolio_industry_allocation_em,
                    kwargs={"symbol": symbol, "date": str(year)},
                    timeout=REQUEST_TIMEOUT,
                )
                print(" ✓")
                if df is None or df.empty:
                    last_df = None
                    break
                df = df.copy()
                df.columns = [c.strip() for c in df.columns]
                last_df = df
                break
            except Exception:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f" ✗ 重试中({attempt + 1}/{MAX_RETRIES})...", end="", flush=True)
                    time.sleep(wait_time)
                else:
                    print(" ✗ 失败")
                    last_df = None
        if last_df is not None and not last_df.empty:
            break

    if last_df is None or last_df.empty:
        INDUSTRY_ALLOC_CACHE[symbol] = None
        return None

    industry_col = None
    weight_col = None
    date_col = None
    for c in last_df.columns:
        if "行业" in c:
            industry_col = c
        if "占净值比例" in c or "持仓占比" in c or c.lower() in ("weight", "ratio"):
            weight_col = c
        if "截止时间" in c or c.lower() in ("date", "截止日期"):
            date_col = c

    if industry_col is None or weight_col is None:
        INDUSTRY_ALLOC_CACHE[symbol] = None
        return None

    if date_col is not None:
        last_df["_d"] = pd.to_datetime(last_df[date_col], errors="coerce")
        last_df = last_df.dropna(subset=["_d"])
        if not last_df.empty:
            latest = last_df["_d"].max()
            last_df = last_df[last_df["_d"] == latest]

    out = last_df[[industry_col, weight_col]].copy()
    out.columns = ["industry", "weight"]
    out["industry"] = out["industry"].astype(str)
    out["weight"] = pd.to_numeric(out["weight"], errors="coerce")
    out = out.dropna(subset=["industry", "weight"]).copy()

    INDUSTRY_ALLOC_CACHE[symbol] = out
    return out


def get_stock_spot() -> Optional[pd.DataFrame]:
    global STOCK_SPOT_CACHE
    for attempt in range(MAX_RETRIES):
        try:
            spot = call_with_timeout(ak.stock_zh_a_spot_em, timeout=REQUEST_TIMEOUT)
            spot = spot.copy()
            spot.columns = [c.strip() for c in spot.columns]
            STOCK_SPOT_CACHE = spot
            return spot
        except Exception:
            if hasattr(ak, "stock_zh_a_spot"):
                try:
                    spot = call_with_timeout(ak.stock_zh_a_spot, timeout=REQUEST_TIMEOUT)
                    spot = spot.copy()
                    spot.columns = [c.strip() for c in spot.columns]
                    STOCK_SPOT_CACHE = spot
                    return spot
                except Exception:
                    pass
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
            else:
                break
    return STOCK_SPOT_CACHE


def _spot_series(spot: pd.DataFrame) -> Tuple[pd.Series, str, str]:
    code_col = None
    pct_col = None
    for c in spot.columns:
        if "代码" in c or c.lower() in ("code", "股票代码"):
            code_col = c
        if "涨跌幅" in c or c.lower() in ("pct", "change_pct", "涨跌幅(%)"):
            pct_col = c
    if code_col is None or pct_col is None:
        raise RuntimeError(f"股票实时字段识别失败，当前列：{spot.columns.tolist()}")
    s = spot.set_index(code_col)[pct_col]
    return s, code_col, pct_col


def get_etf_spot_return_map() -> Optional[pd.Series]:
    spot = None
    if hasattr(ak, "fund_etf_spot_em"):
        try:
            spot = call_with_timeout(ak.fund_etf_spot_em, timeout=REQUEST_TIMEOUT)
        except Exception:
            spot = None

    if spot is None or spot.empty:
        return None

    spot = spot.copy()
    spot.columns = [c.strip() for c in spot.columns]
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


def get_index_spot_pct_change() -> pd.Series:
    global INDEX_SPOT_CACHE
    for attempt in range(MAX_RETRIES):
        try:
            spot = call_with_timeout(
                ak.stock_zh_index_spot_em,
                kwargs={"symbol": "沪深重要指数"},
                timeout=REQUEST_TIMEOUT,
            )
            spot = spot.copy()
            spot.columns = [c.strip() for c in spot.columns]
            code_col = "代码" if "代码" in spot.columns else None
            pct_col = "涨跌幅" if "涨跌幅" in spot.columns else None
            if code_col is None or pct_col is None:
                raise RuntimeError(f"指数实时字段识别失败，当前列：{spot.columns.tolist()}")
            INDEX_SPOT_CACHE = spot.set_index(code_col)[pct_col] / 100.0
            return INDEX_SPOT_CACHE
        except Exception:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
            else:
                raise
    raise RuntimeError("get_index_spot_pct_change failed")


def get_industry_spot_pct_change() -> Optional[pd.Series]:
    global INDUSTRY_SPOT_CACHE
    for attempt in range(MAX_RETRIES):
        try:
            spot = call_with_timeout(ak.stock_board_industry_spot_em, timeout=REQUEST_TIMEOUT)
            spot = spot.copy()
            spot.columns = [c.strip() for c in spot.columns]
            name_col = None
            pct_col = None
            for c in spot.columns:
                if "板块" in c or "行业" in c or c.lower() in ("name", "板块名称"):
                    name_col = c
                if "涨跌幅" in c or c.lower() in ("pct", "change_pct", "涨跌幅(%)"):
                    pct_col = c
            if name_col is None or pct_col is None:
                return None
            INDUSTRY_SPOT_CACHE = spot.set_index(name_col)[pct_col] / 100.0
            return INDUSTRY_SPOT_CACHE
        except Exception:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
            else:
                return None
    return None


def get_fund_value_estimation() -> Optional[pd.DataFrame]:
    global FUND_EST_CACHE
    if not USE_EASTMONEY_ESTIMATE:
        return None
    if not hasattr(ak, "fund_value_estimation_em"):
        return None
    for attempt in range(MAX_RETRIES):
        try:
            df = call_with_timeout(ak.fund_value_estimation_em, timeout=REQUEST_TIMEOUT)
            df = df.copy()
            df.columns = [c.strip() for c in df.columns]
            FUND_EST_CACHE = df
            return df
        except Exception:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
            else:
                return None
    return None


def _extract_fund_estimate(df: pd.DataFrame, symbol: str) -> Optional[dict]:
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


def get_stock_industry(code: str) -> Optional[str]:
    if code in INDUSTRY_CACHE:
        return INDUSTRY_CACHE[code]

    try:
        info = call_with_timeout(ak.stock_individual_info_em, kwargs={"symbol": code}, timeout=REQUEST_TIMEOUT)
    except Exception:
        INDUSTRY_CACHE[code] = None
        return None

    industry = None
    if isinstance(info, pd.DataFrame):
        info = info.copy()
        info.columns = [str(c).strip() for c in info.columns]
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

    INDUSTRY_CACHE[code] = industry
    return industry


def estimate_return_with_holdings(
    holdings: pd.DataFrame,
    stock_spot: Optional[pd.DataFrame],
    industry_spot: Optional[pd.Series],
    etf_spot: Optional[pd.Series],
    index_ret: Optional[float],
) -> dict:
    s = None
    if stock_spot is not None:
        s, _, _ = _spot_series(stock_spot)
        s = s / 100.0

    total_weight = float(holdings["weight"].sum()) if not holdings.empty else 0.0
    if total_weight <= 0:
        return {"ret": index_ret or 0.0, "source": "index_only", "coverage": 0.0}

    ret_sum = 0.0
    direct_weight = 0.0
    industry_weight = 0.0
    missing_weight = 0.0

    for _, row in holdings.iterrows():
        code = str(row["code"]).zfill(6)
        weight = float(row["weight"]) / 100.0
        if etf_spot is not None and code in etf_spot.index:
            ret = float(etf_spot.loc[code])
            ret_sum += weight * ret
            direct_weight += weight
            continue
        if s is not None and code in s.index:
            ret = float(s.loc[code])
            ret_sum += weight * ret
            direct_weight += weight
            continue

        ind_ret = None
        if industry_spot is not None:
            industry = get_stock_industry(code)
            if industry and industry in industry_spot.index:
                ind_ret = float(industry_spot.loc[industry])

        if ind_ret is not None:
            ret_sum += weight * ind_ret
            industry_weight += weight
        else:
            missing_weight += weight

    residual_weight = max(0.0, 1.0 - total_weight / 100.0)
    missing_weight += residual_weight

    if missing_weight > 0 and USE_INDEX_FALLBACK and index_ret is not None:
        ret_sum += missing_weight * index_ret
        source = "holdings+industry+index"
    elif missing_weight > 0:
        source = "holdings+industry"
    else:
        source = "holdings+industry"

    coverage = direct_weight / (total_weight / 100.0) if total_weight > 0 else 0.0
    return {
        "ret": ret_sum,
        "source": source,
        "coverage": coverage,
        "direct_weight": direct_weight,
        "industry_weight": industry_weight,
        "missing_weight": missing_weight,
    }


def estimate_return_with_industry_allocation(
    allocation: pd.DataFrame,
    industry_spot: Optional[pd.Series],
    index_ret: Optional[float],
) -> dict:
    if allocation is None or allocation.empty or industry_spot is None:
        return {"ret": index_ret or 0.0, "coverage": 0.0, "source": "index_only"}

    total_weight = float(allocation["weight"].sum())
    if total_weight <= 0:
        return {"ret": index_ret or 0.0, "coverage": 0.0, "source": "index_only"}

    ret_sum = 0.0
    covered = 0.0
    missing_weight = 0.0
    for _, row in allocation.iterrows():
        industry = str(row["industry"])
        weight = float(row["weight"]) / 100.0
        if industry in industry_spot.index:
            ret_sum += weight * float(industry_spot.loc[industry])
            covered += weight
        else:
            missing_weight += weight

    residual_weight = max(0.0, 1.0 - total_weight / 100.0)
    missing_weight += residual_weight

    if missing_weight > 0 and USE_INDEX_FALLBACK and index_ret is not None:
        ret_sum += missing_weight * index_ret
        source = "industry+index"
    else:
        source = "industry"

    coverage = covered / (total_weight / 100.0) if total_weight > 0 else 0.0
    return {"ret": ret_sum, "coverage": coverage, "source": source}


def main():
    print("=== 基金盘中估值实验（持仓+行业映射） ===")
    print("A股交易时段内每 60s 刷新一次")

    cache = {}
    for idx, (fund_code, cfg) in enumerate(FUNDS.items()):
        if idx > 0:
            delay = API_CALL_DELAY * 5
            print(f"等待 {delay:.1f}s 避免API限流...")
            time.sleep(delay)

        try:
            print(f"\n{fund_code} 正在准备数据...")
            fund_df = get_fund_nav_daily(fund_code)
            holdings = get_latest_holdings(fund_code)
            industry_alloc = get_fund_industry_allocation(fund_code)
            cache[fund_code] = {
                "name": cfg.get("name", ""),
                "index_code": cfg.get("index_code"),
                "fund_df": fund_df,
                "holdings": holdings,
                "industry_alloc": industry_alloc,
            }
            if holdings is None or holdings.empty:
                print(f"{fund_code} 持仓为空，将使用指数兜底")
            else:
                print(f"{fund_code} 持仓条目: {len(holdings)}")
        except Exception as e:
            print(f"{fund_code} 准备失败：{e}")

    print(f"\n成功准备 {len(cache)} 个基金，开始实时估值...\n")

    while True:
        try:
            now = pd.Timestamp.now(tz="Asia/Shanghai")
            lines = []

            stock_spot = get_stock_spot()
            if stock_spot is None:
                print("\n获取股票实时行情失败：将跳过股票直连估值，使用ETF/行业/指数兜底")

            etf_spot = get_etf_spot_return_map()

            try:
                index_spot = get_index_spot_pct_change()
            except Exception:
                index_spot = None

            industry_spot = get_industry_spot_pct_change()
            fund_est_df = get_fund_value_estimation()

            for fund_code, info in cache.items():
                try:
                    name = info["name"]
                    fund_df = info["fund_df"]
                    holdings = info["holdings"]
                    industry_alloc = info["industry_alloc"]
                    index_code = info["index_code"]

                    index_ret = None
                    if index_spot is not None and index_code in index_spot.index:
                        index_ret = float(index_spot.loc[index_code])

                    last_nav = float(fund_df["nav"].iloc[-1])

                    est_override = None
                    if fund_est_df is not None:
                        est_override = _extract_fund_estimate(fund_est_df, fund_code)

                    if est_override is not None and est_override["kind"] == "value":
                        est_ret = (float(est_override["value"]) / last_nav) - 1.0
                        coverage = 1.0
                        source = "eastmoney_est_value"
                    elif est_override is not None and est_override["kind"] == "pct":
                        est_ret = float(est_override["value"])
                        coverage = 1.0
                        source = "eastmoney_est_pct"
                    elif holdings is not None and not holdings.empty:
                        out = estimate_return_with_holdings(
                            holdings,
                            stock_spot,
                            industry_spot,
                            etf_spot,
                            index_ret,
                        )
                        est_ret = out["ret"]
                        coverage = out["coverage"]
                        source = out["source"]
                        if coverage < MIN_DIRECT_COVERAGE and index_ret is not None:
                            source = f"{source}(low_coverage)"
                            if industry_alloc is not None:
                                ind_out = estimate_return_with_industry_allocation(
                                    industry_alloc,
                                    industry_spot,
                                    index_ret,
                                )
                                est_ret = est_ret * coverage + ind_out["ret"] * (1.0 - coverage)
                                source = f"{source}+{ind_out['source']}"
                    else:
                        ind_out = estimate_return_with_industry_allocation(
                            industry_alloc,
                            industry_spot,
                            index_ret,
                        )
                        est_ret = ind_out["ret"]
                        coverage = ind_out["coverage"]
                        source = ind_out["source"]

                    est_nav = last_nav * (1.0 + est_ret)
                    pct = est_ret * 100.0
                    pct_str = f"{pct:+.2f}%"
                    if pct > 0:
                        pct_str = f"\033[31m{pct_str}\033[0m"
                    elif pct < 0:
                        pct_str = f"\033[32m{pct_str}\033[0m"

                    lines.append(
                        f"{fund_code}  {name:18s}  {pct_str}  cover={coverage:.2f}  {source}"
                    )
                except Exception as e:
                    lines.append(f"{fund_code}  {name:18s}  估值失败: {e}")

            print("\033[2J\033[H", end="")
            print(now)
            print("代码    名称                当前估值    覆盖率    来源")
            for line in lines:
                print(line)
        except Exception as e:
            print("估值失败：", e)
        time.sleep(SLEEP_SEC)


if __name__ == "__main__":
    main()
