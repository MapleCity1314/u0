import time
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import akshare as ak
import threading
from typing import Optional, Any

from config import FUNDS, TEMPLATES, DEFAULT_FACTORS

SLEEP_SEC = 60
MAX_RETRIES = 3
RETRY_DELAY = 2.0
API_CALL_DELAY = 1.0  # Delay between consecutive API calls to avoid overwhelming the server
REQUEST_TIMEOUT = 30  # Timeout in seconds for individual API calls

# Global cache for index historical data to avoid redundant fetches
INDEX_HIST_CACHE = {}


class TimeoutError(Exception):
    """Raised when an operation times out."""
    pass


def call_with_timeout(func, args=(), kwargs=None, timeout=REQUEST_TIMEOUT) -> Any:
    """
    Call a function with a timeout. If the function doesn't complete within
    the timeout period, raise TimeoutError.
    """
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
        # Thread is still running - timeout occurred
        raise TimeoutError(f"Operation timed out after {timeout} seconds")

    if exception[0] is not None:
        raise exception[0]

    return result[0]


def is_cn_market_open(ts: pd.Timestamp) -> bool:
    if ts.tzinfo is None:
        ts = ts.tz_localize("Asia/Shanghai")
    else:
        ts = ts.tz_convert("Asia/Shanghai")

    t = ts.time()
    am_open = t >= pd.Timestamp("09:30").time() and t <= pd.Timestamp("11:30").time()
    pm_open = t >= pd.Timestamp("13:00").time() and t <= pd.Timestamp("15:00").time()
    return am_open or pm_open


def get_fund_nav_daily(symbol: str) -> pd.DataFrame:
    """Fetch fund NAV data with retry logic and timeout."""
    for attempt in range(MAX_RETRIES):
        try:
            print(f"  获取基金 {symbol} 净值数据...", end="", flush=True)
            df = call_with_timeout(
                ak.fund_open_fund_info_em,
                kwargs={"symbol": symbol, "indicator": "单位净值走势"},
                timeout=REQUEST_TIMEOUT
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
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f" ✗ 重试中({attempt + 1}/{MAX_RETRIES})...", end="", flush=True)
                time.sleep(wait_time)
            else:
                print(f" ✗ 失败")
                raise

    raise RuntimeError(f"get_fund_nav_daily failed after {MAX_RETRIES} attempts")


def normalize_index_symbol(code: str) -> str:
    if code.startswith(("sh", "sz", "SH", "SZ")):
        return code[2:]
    return code


def fetch_index_hist(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch index history with retry logic and caching."""
    # Check cache first
    cache_key = f"{code}_{start_date}_{end_date}"
    if cache_key in INDEX_HIST_CACHE:
        print(f"  [缓存] 指数 {code}", flush=True)
        return INDEX_HIST_CACHE[cache_key]

    for attempt in range(MAX_RETRIES):
        hist = None
        err = None

        try:
            if hasattr(ak, "index_zh_a_hist"):
                try:
                    hist = call_with_timeout(
                        ak.index_zh_a_hist,
                        kwargs={
                            "symbol": normalize_index_symbol(code),
                            "period": "daily",
                            "start_date": start_date,
                            "end_date": end_date,
                        },
                        timeout=REQUEST_TIMEOUT
                    )
                except Exception as e:
                    err = e

            if hist is None and hasattr(ak, "stock_zh_index_daily_em"):
                try:
                    time.sleep(API_CALL_DELAY)  # Rate limiting
                    hist = call_with_timeout(
                        ak.stock_zh_index_daily_em,
                        kwargs={"symbol": code},
                        timeout=REQUEST_TIMEOUT
                    )
                except Exception as e:
                    err = e

            if hist is not None:
                # Cache the result before returning
                INDEX_HIST_CACHE[cache_key] = hist
                return hist

        except Exception as e:
            err = e

        # Retry logic
        if attempt < MAX_RETRIES - 1:
            wait_time = RETRY_DELAY * (2 ** attempt)
            print(f" ✗ 重试中({attempt + 1}/{MAX_RETRIES})...", end="", flush=True)
            time.sleep(wait_time)
        else:
            raise RuntimeError(
                f"指数 {code} 获取失败（尝试了 index_zh_a_hist / stock_zh_index_daily_em）。错误: {err}"
            )

    raise RuntimeError(f"fetch_index_hist failed after {MAX_RETRIES} attempts")


def fit_factor_model(fund_df: pd.DataFrame, indices: dict, lookback_days: int) -> tuple[LinearRegression, list[str]]:
    idx_rets = []
    dates = None
    now = pd.Timestamp.now(tz="Asia/Shanghai")
    end_date = now.strftime("%Y%m%d")
    start_date = (now - pd.Timedelta(days=lookback_days + 60)).strftime("%Y%m%d")

    successful_indices = {}
    for idx, (name, code) in enumerate(indices.items()):
        if idx > 0:
            time.sleep(API_CALL_DELAY * 2)  # Rate limiting between index fetches

        print(f"  获取指数 {name}({code}) 历史数据...", end="", flush=True)
        try:
            hist = fetch_index_hist(code, start_date, end_date)
            print(" ✓")
            hist = hist.copy()
            hist.columns = [c.strip() for c in hist.columns]

            date_col = "日期" if "日期" in hist.columns else ("date" if "date" in hist.columns else None)
            close_col = "收盘" if "收盘" in hist.columns else ("close" if "close" in hist.columns else None)
            if date_col is None or close_col is None:
                print(f" ✗ (字段识别失败)")
                continue

            hist[date_col] = pd.to_datetime(hist[date_col])
            hist = hist.sort_values(date_col).rename(columns={date_col: "date", close_col: "close"})
            hist[name] = hist["close"].pct_change()
            hist = hist.dropna(subset=[name])
            hist = hist[["date", name]]

            if dates is None:
                dates = hist["date"]
            idx_rets.append(hist)
            successful_indices[name] = code
        except Exception as e:
            print(f" ✗ (跳过: {str(e)[:50]})")
            continue

    if len(successful_indices) == 0:
        raise RuntimeError("所有指数获取均失败，无法构建模型")

    if len(idx_rets) == 0:
        raise RuntimeError("没有成功获取任何指数数据")

    X = idx_rets[0]
    for t in idx_rets[1:]:
        X = X.merge(t, on="date", how="inner")

    dataset = fund_df[["date", "fund_ret"]].merge(X, on="date", how="inner")
    dataset = dataset.sort_values("date").tail(lookback_days)

    features = list(successful_indices.keys())
    model = LinearRegression()
    model.fit(dataset[features].values, dataset["fund_ret"].values)

    print(f"  成功使用 {len(features)}/{len(indices)} 个指数")
    return model, features


def get_index_spot_pct_change() -> pd.Series:
    """Fetch real-time index data with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            print(f"  获取实时指数数据...", end="", flush=True)
            spot = call_with_timeout(
                ak.stock_zh_index_spot_em,
                kwargs={"symbol": "沪深重要指数"},
                timeout=REQUEST_TIMEOUT
            )
            print(" ✓")
            spot = spot.copy()
            spot.columns = [c.strip() for c in spot.columns]
            code_col = "代码" if "代码" in spot.columns else None
            pct_col = "涨跌幅" if "涨跌幅" in spot.columns else None
            if code_col is None or pct_col is None:
                raise RuntimeError(f"指数实时字段识别失败，当前列：{spot.columns.tolist()}")

            m = spot.set_index(code_col)[pct_col]
            return (m / 100.0)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f" ✗ 重试中({attempt + 1}/{MAX_RETRIES})...", end="", flush=True)
                time.sleep(wait_time)
            else:
                print(f" ✗ 失败")
                raise

    raise RuntimeError(f"get_index_spot_pct_change failed after {MAX_RETRIES} attempts")


def estimate_intraday_nav(
    fund_code: str,
    fund_df: pd.DataFrame,
    model: LinearRegression,
    features: list[str],
    indices: dict,
) -> dict:
    """Original version - fetches spot data internally."""
    last_nav = float(fund_df["nav"].iloc[-1])
    spot_pct = get_index_spot_pct_change()
    return estimate_intraday_nav_cached(fund_code, fund_df, model, features, indices, spot_pct)


def estimate_intraday_nav_cached(
    fund_code: str,
    fund_df: pd.DataFrame,
    model: LinearRegression,
    features: list[str],
    indices: dict,
    spot_pct: pd.Series,
) -> dict:
    """Version that uses pre-fetched spot data to avoid repeated API calls."""
    last_nav = float(fund_df["nav"].iloc[-1])

    x = []
    missing = []
    for name, code in indices.items():
        if code in spot_pct.index:
            x.append(float(spot_pct.loc[code]))
        else:
            x.append(0.0)
            missing.append(code)

    x = np.array(x).reshape(1, -1)
    missing_all = len(missing) == len(indices)
    if missing_all:
        est_ret = float(model.intercept_)
        return_source = "alpha_only"
    else:
        est_ret = float(model.predict(x)[0])
        return_source = "factor_intraday"

    est_nav = last_nav * (1.0 + est_ret)

    sorted_betas = dict(
        sorted(
            zip(features, model.coef_.tolist()),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )
    )
    dominant_factor = next(iter(sorted_betas), None)

    now = pd.Timestamp.now(tz="Asia/Shanghai")
    market_status = "closed" if (missing_all or not is_cn_market_open(now)) else "open"

    return {
        "fund": fund_code,
        "last_official_nav": last_nav,
        "estimated_return": est_ret,
        "return_source": return_source,
        "estimated_nav": est_nav,
        "market_status": market_status,
        "missing_index_codes": missing,
        "betas": sorted_betas,
        "dominant_factor": dominant_factor,
        "alpha": float(model.intercept_),
    }




def build_model_for_fund(fund_code: str, fund_cfg: dict):
    template_name = fund_cfg.get("template", "multi_factor")
    template = TEMPLATES.get(template_name)
    if template is None:
        raise RuntimeError(f"未知模板: {template_name}")

    if template_name == "external":
        return None, None, None, None

    indices = template.get("indices")
    if template_name == "single_index":
        index_code = fund_cfg.get("index_code")
        if index_code:
            indices = {"BASE": index_code}
        else:
            indices = DEFAULT_FACTORS
    if not indices:
        raise RuntimeError(f"模板 {template_name} 没有可用指数")

    lookback_days = int(template.get("lookback_days", 90))
    fund_df = get_fund_nav_daily(fund_code)
    model, features = fit_factor_model(fund_df, indices, lookback_days)
    return fund_df, model, features, indices


def main():
    print("=== 多基金盘中估值实验 ===")
    print("A股交易时段内每 60s 刷新一次")

    cache = {}
    for idx, (fund_code, cfg) in enumerate(FUNDS.items()):
        if cfg.get("template") == "external":
            print(f"{fund_code} 跳过：external 模板未实现")
            continue

        # Add delay between fund model builds to avoid overwhelming API
        if idx > 0:
            delay = API_CALL_DELAY * 5
            print(f"等待 {delay:.1f}s 避免API限流...")
            time.sleep(delay)

        try:
            print(f"\n{fund_code} 正在构建模型...")
            fund_df, model, features, indices = build_model_for_fund(fund_code, cfg)
            cache[fund_code] = (cfg.get("name", ""), fund_df, model, features, indices)
            print(f"{fund_code} 模型已拟合: features={features}")
        except Exception as e:
            print(f"{fund_code} 模型构建失败：{e}")

    print(f"\n成功构建 {len(cache)} 个基金模型，开始实时估值...\n")

    while True:
        try:
            now = pd.Timestamp.now(tz="Asia/Shanghai")
            lines = []

            # Fetch real-time index data once for all funds
            try:
                spot_pct = get_index_spot_pct_change()
            except Exception as e:
                print(f"\n获取实时指数数据失败: {str(e)[:100]}")
                print(f"等待 {SLEEP_SEC}s 后重试...\n")
                time.sleep(SLEEP_SEC)
                continue

            for fund_code, (name, fund_df, model, features, indices) in cache.items():
                try:
                    # Pass pre-fetched spot_pct to avoid repeated API calls
                    out = estimate_intraday_nav_cached(fund_code, fund_df, model, features, indices, spot_pct)
                    pct = out["estimated_return"] * 100.0
                    pct_str = f"{pct:+.2f}%"
                    if pct > 0:
                        pct_str = f"\033[31m{pct_str}\033[0m"  # red up
                    elif pct < 0:
                        pct_str = f"\033[32m{pct_str}\033[0m"  # green down
                    lines.append(
                        f"{fund_code}  {name:20s}  {pct_str}  {out['market_status']:6s}  {out['return_source']}"
                    )
                except Exception as e:
                    lines.append(f"{fund_code}  {name:20s}  估值失败: {e}")

            # 简易终端刷新
            print("\033[2J\033[H", end="")
            print(now)
            print("代码    名称                    当前估值    市场状态    来源")
            for line in lines:
                print(line)
        except Exception as e:
            print("估值失败：", e)
        time.sleep(SLEEP_SEC)


if __name__ == "__main__":
    main()
