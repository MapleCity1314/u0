import time
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import akshare as ak

FUND_CODE = "022485"

# 你可以按需增减（MVP先用这些“风格因子”）
FACTOR_INDEX = {
    "HS300": "sh000300",
    "ZZ500": "sh000905",
    "CYB":   "sz399006",
    "ZZ1000":"sh000852",
}

LOOKBACK_DAYS = 90  # 回归窗口
SLEEP_SEC = 60      # 盘中每分钟刷新一次

def get_fund_nav_daily(symbol: str) -> pd.DataFrame:
    """
    取基金日频单位净值走势，并生成日收益率
    """
    df = ak.fund_open_fund_info_em(symbol=symbol, indicator="单位净值走势")  # :contentReference[oaicite:2]{index=2}
    # 常见字段：净值日期、单位净值（不同版本 akshare 字段名可能略有差异，这里做兼容）
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # 兼容列名
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

def get_index_spot_pct_change() -> pd.Series:
    """
    拉取指数实时涨跌幅（单位：%），并转为小数（0.0123）
    """
    spot = ak.stock_zh_index_spot_em(symbol="沪深重要指数")  # :contentReference[oaicite:3]{index=3}
    spot = spot.copy()
    spot.columns = [c.strip() for c in spot.columns]
    # 常见列：代码、名称、最新价、涨跌幅
    code_col = "代码" if "代码" in spot.columns else None
    pct_col = "涨跌幅" if "涨跌幅" in spot.columns else None
    if code_col is None or pct_col is None:
        raise RuntimeError(f"指数实时字段识别失败，当前列：{spot.columns.tolist()}")

    m = spot.set_index(code_col)[pct_col]
    # 转成小数
    return (m / 100.0)

def fit_factor_model(fund_df: pd.DataFrame) -> tuple[LinearRegression, list[str]]:
    """
    用基金历史日收益，对指数日收益做回归，得到 beta
    这里为了 MVP 简化：用指数的“日收益”需要日频指数历史数据。
    但 AkShare 的指数日频接口较多版本差异，MVP先用更稳的替代：
    - 用基金自身历史收益对“指数日收益代理”不太现实
    因此这里给你两个选项：
    A) 如果你能稳定拿到指数日频（推荐，你改一个函数即可）
    B) MVP极简：用基金历史收益对“指数同日涨跌幅”（从历史接口拉）回归

    为了让你现在就跑起来，我先用 B：走一个常见的东财指数历史日频接口（若你版本不支持，下面会抛出提示，你再告诉我我帮你换接口名）
    """
    # === 尝试拉取指数日频（接口名可能随版本变化；失败会提示） ===
    idx_rets = []
    dates = None

    for name, code in FACTOR_INDEX.items():
        # 常见可用接口之一（不同 akshare 版本名字可能略变）
        # 这里采用 “index_zh_a_hist” / “stock_zh_index_daily_em” 等都可能存在
        hist = None
        err = None
        for fn in ["stock_zh_index_daily_em", "index_zh_a_hist"]:
            if hasattr(ak, fn):
                try:
                    hist = getattr(ak, fn)(symbol=code)
                    break
                except Exception as e:
                    err = e
        if hist is None:
            raise RuntimeError(
                f"你当前 akshare 版本找不到可用的指数日频接口（尝试了 stock_zh_index_daily_em / index_zh_a_hist）。"
                f"报错示例：{err}\n"
                f"解决：你把 `dir(ak)` 里包含 'index' 的函数名贴我，我给你换成你版本可用的。"
            )

        hist = hist.copy()
        hist.columns = [c.strip() for c in hist.columns]
        # 兼容字段
        date_col = "日期" if "日期" in hist.columns else ("date" if "date" in hist.columns else None)
        close_col = "收盘" if "收盘" in hist.columns else ("close" if "close" in hist.columns else None)
        if date_col is None or close_col is None:
            raise RuntimeError(f"{code} 指数历史字段识别失败：{hist.columns.tolist()}")

        hist[date_col] = pd.to_datetime(hist[date_col])
        hist = hist.sort_values(date_col).rename(columns={date_col: "date", close_col: "close"})
        hist[name] = hist["close"].pct_change()
        hist = hist.dropna(subset=[name])
        hist = hist[["date", name]]

        if dates is None:
            dates = hist["date"]
        idx_rets.append(hist)

    X = idx_rets[0]
    for t in idx_rets[1:]:
        X = X.merge(t, on="date", how="inner")

    # 只保留需要的列，避免重复 merge 导致 fund_ret_x / fund_ret_y
    dataset = fund_df[["date", "fund_ret"]].merge(X, on="date", how="inner")
    dataset = dataset.sort_values("date").tail(LOOKBACK_DAYS)

    features = list(FACTOR_INDEX.keys())
    model = LinearRegression()
    model.fit(dataset[features].values, dataset["fund_ret"].values)


    return model, features

def estimate_intraday_nav(fund_df: pd.DataFrame, model: LinearRegression, features: list[str]) -> dict:
    """
    用实时指数涨跌幅估算今日基金 NAV
    """
    last_nav = float(fund_df["nav"].iloc[-1])   # 最近公布的净值（通常是昨日）
    spot_pct = get_index_spot_pct_change()

    x = []
    missing = []
    for name, code in FACTOR_INDEX.items():
        if code in spot_pct.index:
            x.append(float(spot_pct.loc[code]))
        else:
            x.append(0.0)
            missing.append(code)

    x = np.array(x).reshape(1, -1)
    est_ret = float(model.predict(x)[0])  # 估算今日相对“昨日净值”的涨跌
    est_nav = last_nav * (1.0 + est_ret)

    return {
        "fund": FUND_CODE,
        "last_official_nav": last_nav,
        "estimated_return": est_ret,
        "estimated_nav": est_nav,
        "missing_index_codes": missing,
        "betas": dict(zip(features, model.coef_.tolist())),
        "alpha": float(model.intercept_),
    }

def main():
    fund_df = get_fund_nav_daily(FUND_CODE)
    model, features = fit_factor_model(fund_df)

    print("=== 模型已拟合 ===")
    print("alpha:", model.intercept_)
    print("betas:", dict(zip(features, model.coef_)))
    print("开始盘中估值（每 60s 刷新）...")

    while True:
        try:
            out = estimate_intraday_nav(fund_df, model, features)
            print(pd.Timestamp.now(), out)
        except Exception as e:
            print("估值失败：", e)
        time.sleep(SLEEP_SEC)

if __name__ == "__main__":
    main()
