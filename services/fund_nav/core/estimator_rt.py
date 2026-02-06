import asyncio
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

import httpx

from . import plan_a_model


REQUEST_TIMEOUT = int(os.getenv("FUND_NAV_RT_TIMEOUT_SEC", "20"))
MAX_CONCURRENCY = int(os.getenv("FUND_NAV_RT_MAX_CONCURRENCY", "8"))


def _normalize_code(code: str) -> str:
    c = code.strip().upper()
    if c.startswith("SH") or c.startswith("SZ"):
        c = c[2:]
    if c.endswith(".SH") or c.endswith(".SZ"):
        c = c[:-3]
    return c.zfill(6)


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.strip())
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    try:
        dt = datetime.strptime(value.strip()[:10], "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


async def _aget(client: httpx.AsyncClient, url: str, params: dict | None = None) -> str | None:
    try:
        resp = await client.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


async def _fetch_fundgz(client: httpx.AsyncClient, code: str) -> dict | None:
    text = await _aget(client, f"https://fundgz.1234567.com.cn/js/{code}.js")
    if not text:
        return None
    m = re.search(r"jsonpgz\((\{.*?\})\)", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except Exception:
        return None
    out = {
        "code": data.get("fundcode") or code,
        "name": data.get("name"),
        "dwjz": data.get("dwjz"),
        "jzrq": data.get("jzrq"),
        "gsz": data.get("gsz"),
        "gszzl": data.get("gszzl"),
        "gztime": data.get("gztime"),
    }
    return out


async def _fetch_tencent_fund(client: httpx.AsyncClient, code: str) -> dict | None:
    text = await _aget(client, f"https://qt.gtimg.cn/q=jj{code}")
    if not text:
        return None
    m = re.search(rf'v_jj{re.escape(code)}="(.*)"', text)
    if not m:
        return None
    parts = m.group(1).split("~")
    if len(parts) < 9:
        return None
    return {
        "dwjz": parts[5] or None,
        "zzl": parts[7] or None,
        "jzrq": _parse_date(parts[8]),
        "name": parts[1] if len(parts) > 1 else None,
    }


def _parse_holdings_html(html_text: str) -> list[tuple[str, float]]:
    rows = re.findall(r"(?s)<tr>.*?</tr>", html_text)
    out: list[tuple[str, float]] = []
    for row in rows:
        code_m = re.search(r">(\d{6})<", row)
        if not code_m:
            continue
        pct_m = re.findall(r">\\s*([0-9.]+)\\s*%\\s*<", row)
        if not pct_m:
            continue
        try:
            weight = float(pct_m[-1])
        except Exception:
            continue
        out.append((code_m.group(1), weight))
    return out


async def _fetch_holdings(client: httpx.AsyncClient, code: str) -> list[tuple[str, float]] | None:
    try:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception:
        now = datetime.now()
    params = {
        "type": "jjcc",
        "code": code,
        "topline": "10",
        "year": str(now.year),
        "month": str(now.month),
    }
    text = await _aget(
        client,
        "https://fundf10.eastmoney.com/FundArchivesDatas.aspx",
        params=params,
    )
    if not text:
        return None
    m = re.search(r'content:"(.*?)"', text, flags=re.S)
    if not m:
        m = re.search(r"content:'(.*?)'", text, flags=re.S)
    if not m:
        return None
    raw = m.group(1)
    try:
        unescaped = bytes(raw, "utf-8").decode("unicode_escape")
    except Exception:
        unescaped = raw
    unescaped = unescaped.replace("\\/", "/")
    holdings = _parse_holdings_html(unescaped)
    return holdings or None


async def _fetch_quotes(client: httpx.AsyncClient, codes: list[str]) -> dict[str, float]:
    if not codes:
        return {}
    symbols = []
    for c in codes:
        base = _normalize_code(c)
        prefix = "sh" if base.startswith("6") else "sz"
        symbols.append(f"{prefix}{base}")
    text = await _aget(client, "https://qt.gtimg.cn/q=" + ",".join(symbols))
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


def _choose_nav(fundgz: dict | None, tencent: dict | None) -> dict:
    dwjz = None
    jzrq = None
    zzl = None
    name = None
    if fundgz:
        dwjz = fundgz.get("dwjz") or dwjz
        jzrq = fundgz.get("jzrq") or jzrq
        name = fundgz.get("name") or name
    if tencent:
        t_date = tencent.get("jzrq")
        f_date = _parse_date(jzrq)
        if t_date and (f_date is None or t_date >= f_date):
            dwjz = tencent.get("dwjz") or dwjz
            jzrq = tencent.get("jzrq") or jzrq
            zzl = tencent.get("zzl") or zzl
        name = tencent.get("name") or name
    return {"dwjz": dwjz, "jzrq": jzrq, "zzl": zzl, "name": name}


async def _estimate_one(client: httpx.AsyncClient, code: str) -> dict[str, Any]:
    code = _normalize_code(code)
    fundgz_task = asyncio.create_task(_fetch_fundgz(client, code))
    tencent_task = asyncio.create_task(_fetch_tencent_fund(client, code))
    holdings_task = asyncio.create_task(_fetch_holdings(client, code))

    fundgz, tencent, holdings = await asyncio.gather(fundgz_task, tencent_task, holdings_task)
    base = _choose_nav(fundgz, tencent)

    dwjz = base.get("dwjz")
    jzrq = base.get("jzrq")
    zzl = base.get("zzl")
    name = base.get("name")

    est_gsz = None
    est_gszzl = None
    est_cov = 0.0
    source = None

    if holdings:
        codes = [c for c, _ in holdings]
        quotes = await _fetch_quotes(client, codes)
        ret_sum = 0.0
        covered = 0.0
        total_weight = 0.0
        for c, w in holdings:
            total_weight += w
            ret = quotes.get(_normalize_code(c))
            if ret is None:
                continue
            weight = w / 100.0
            ret_sum += weight * ret
            covered += weight
        if total_weight > 0:
            est_cov = covered / (total_weight / 100.0)
        if covered > 0 and est_cov >= 0.05:
            est_gszzl = ret_sum * 100.0
            if dwjz is not None:
                try:
                    est_gsz = float(dwjz) * (1.0 + ret_sum)
                except Exception:
                    est_gsz = None
            source = "holdings_tencent"



    try:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception:
        now = datetime.now()
    minutes_since_open = (now.hour * 60 + now.minute) - (9 * 60 + 30)

    # PlanA model adjustment (if available)
    features = {
        "planb_return": ret_sum if holdings else 0.0,
        "coverage": est_cov,
        "fundgz_return": (float(fundgz.get("gszzl")) / 100.0) if fundgz and fundgz.get("gszzl") not in (None, "") else 0.0,
        "is_realtime": 1.0 if est_cov >= 0.05 else 0.0,
        "minutes_since_open": float(minutes_since_open),
        "source_holdings": 1.0 if source == "holdings_tencent" else 0.0,
        "source_fundgz": 1.0 if fundgz else 0.0,
    }
    pred = plan_a_model.predict(features)
    if pred is not None:
        est_gszzl = pred * 100.0
        if dwjz is not None:
            try:
                est_gsz = float(dwjz) * (1.0 + pred)
            except Exception:
                est_gsz = None
        source = "planA_model"

    if est_gsz is None and fundgz:
        est_gsz = fundgz.get("gsz")
        est_gszzl = fundgz.get("gszzl")
        source = source or "fundgz"

    is_realtime = False
    if est_cov >= 0.05:
        is_realtime = True
    elif fundgz and fundgz.get("gztime"):
        today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        if str(fundgz.get("gztime", ""))[:10] == today:
            is_realtime = True

    return {
        "code": code,
        "name": name,
        "dwjz": dwjz,
        "jzrq": jzrq,
        "zzl": zzl,
        "gsz": fundgz.get("gsz") if fundgz else None,
        "gszzl": fundgz.get("gszzl") if fundgz else None,
        "gztime": fundgz.get("gztime") if fundgz else None,
        "est_nav": est_gsz,
        "est_return": (float(est_gszzl) / 100.0) if est_gszzl is not None else None,
        "estPricedCoverage": est_cov,
        "source": source,
        "is_realtime": is_realtime,
    }


async def estimate_many(codes: list[str]) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def run_one(code: str) -> dict[str, Any]:
        async with sem:
            try:
                return await _estimate_one(client, code)
            except Exception as exc:
                return {"code": _normalize_code(code), "error": str(exc), "is_realtime": False}

    async with httpx.AsyncClient() as client:
        tasks = [run_one(c) for c in codes]
        return await asyncio.gather(*tasks)
