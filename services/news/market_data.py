from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Iterable

import os
import akshare as ak
from concurrent.futures import ThreadPoolExecutor, TimeoutError

try:
    from tqdm.auto import tqdm

    tqdm.disable = True
except Exception:
    pass

if os.getenv("AKSHARE_DISABLE_PROXY", "true").lower() in ("1", "true", "yes"):
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        if key in os.environ:
            os.environ.pop(key, None)


@dataclass(frozen=True)
class MarketIndexQuote:
    name: str
    value: str
    change: float
    amount: str


def _pick_by_names(df, names: Iterable[str], name_col: str = "名称"):
    rows = []
    col = df[name_col].astype(str)
    for target in names:
        match = df[col.str.contains(target, na=False)]
        if not match.empty:
            rows.append(match.iloc[0])
    return rows


def _format_amount(value, unit: str = "元") -> str:
    try:
        num = float(value)
    except Exception:
        return "-"
    if math.isnan(num) or math.isinf(num) or num == 0:
        return "-"
    if num >= 1e12:
        return f"{num / 1e12:.2f}万亿{unit}"
    if num >= 1e8:
        return f"{num / 1e8:.2f}亿{unit}"
    if num >= 1e4:
        return f"{num / 1e4:.2f}万{unit}"
    return f"{num:.2f}{unit}"


def _safe_float(value) -> float:
    try:
        num = float(value)
    except Exception:
        return 0.0
    if math.isnan(num) or math.isinf(num):
        return 0.0
    return num


def fetch_cn_indices() -> list[MarketIndexQuote]:
    df = ak.stock_zh_index_spot_em(symbol="沪深重要指数")
    targets = ["上证指数", "深证成指", "创业板指", "科创50"]
    rows = _pick_by_names(df, targets)
    quotes: list[MarketIndexQuote] = []
    for row in rows:
        quotes.append(
            MarketIndexQuote(
                name=str(row.get("名称", "")),
                value=str(row.get("最新价", "")),
                change=_safe_float(row.get("涨跌幅", 0)),
                amount=_format_amount(row.get("成交额", 0)),
            )
        )
    return quotes


def fetch_hk_indices() -> list[MarketIndexQuote]:
    df = ak.stock_hk_index_spot_em()
    targets = ["恒生指数", "恒生科技指数", "国企指数", "恒生中国企业"]
    rows = _pick_by_names(df, targets)
    quotes: list[MarketIndexQuote] = []
    for row in rows:
        amount_value = row.get("成交额", row.get("成交量", 0))
        amount_label = "元" if "成交额" in row.index else "手"
        quotes.append(
            MarketIndexQuote(
                name=str(row.get("名称", "")),
                value=str(row.get("最新价", "")),
                change=_safe_float(row.get("涨跌幅", 0)),
                amount=_format_amount(amount_value, amount_label),
            )
        )
    return quotes


def fetch_us_indices() -> list[MarketIndexQuote]:
    index_df = ak.index_global_spot_em()
    targets = ["道琼斯", "纳斯达克", "标普500", "罗素2000"]
    rows = _pick_by_names(index_df, targets, name_col="名称")

    etf_df = ak.stock_us_spot_em()
    etf_map = {}
    for _, row in etf_df.iterrows():
        code = str(row.get("代码", "")).upper()
        name = str(row.get("名称", "")).upper()
        etf_map[code] = row
        if name:
            etf_map[name] = row

    etf_symbols = {
        "道琼斯": "DIA",
        "纳斯达克": "QQQ",
        "标普500": "SPY",
        "罗素2000": "IWM",
    }

    quotes: list[MarketIndexQuote] = []
    for row in rows:
        name = str(row.get("名称", ""))
        amount = "-"
        for key, symbol in etf_symbols.items():
            if key in name:
                etf_row = etf_map.get(symbol) or etf_map.get(f"{symbol}")
                if etf_row is not None:
                    amount = _format_amount(etf_row.get("成交额", 0))
                break
        quotes.append(
            MarketIndexQuote(
                name=name,
                value=str(row.get("最新价", "")),
                change=_safe_float(row.get("涨跌幅", 0)),
                amount=amount,
            )
        )
    return quotes


def fetch_gold_indices() -> list[MarketIndexQuote]:
    df = ak.futures_global_spot_em()
    targets = ["COMEX黄金", "伦敦金", "COMEX白银", "伦敦银"]
    rows = _pick_by_names(df, targets)
    quotes: list[MarketIndexQuote] = []
    for row in rows:
        volume = row.get("成交量", 0)
        value = row.get("最新价", row.get("现价", ""))
        change = row.get("涨跌幅", row.get("涨跌", 0))
        name = str(row.get("名称", ""))
        val = str(value)
        if "nan" in val.lower():
            val = "-"
        quotes.append(
            MarketIndexQuote(
                name=name,
                value=val,
                change=_safe_float(change),
                amount=_format_amount(volume, "手"),
            )
        )
    return quotes


def fetch_market_indices(market: str) -> list[MarketIndexQuote]:
    market = market.upper()
    return _fetch_market_indices_cached(market)


CACHE_TTL_SEC = 60
FETCH_TIMEOUT_SEC = 6
_QUOTE_CACHE: dict[str, tuple[float, list[MarketIndexQuote]]] = {}


def _fetch_market_indices_cached(market: str) -> list[MarketIndexQuote]:
    now = time.time()
    cached = _QUOTE_CACHE.get(market)
    if cached and now - cached[0] < CACHE_TTL_SEC:
        return cached[1]

    try:
        if market == "CN":
            quotes = _run_with_timeout(fetch_cn_indices)
        elif market == "HK":
            quotes = _run_with_timeout(fetch_hk_indices)
        elif market == "US":
            quotes = _run_with_timeout(fetch_us_indices)
        elif market in ("GL", "GOLD"):
            quotes = _run_with_timeout(fetch_gold_indices)
        else:
            quotes = []
    except Exception:
        quotes = []

    if quotes:
        _QUOTE_CACHE[market] = (now, quotes)
        return quotes

    if cached:
        return cached[1]
    return []


def _run_with_timeout(fn):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=FETCH_TIMEOUT_SEC)
        except TimeoutError:
            return []
