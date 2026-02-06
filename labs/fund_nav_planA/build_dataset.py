import json
from datetime import datetime
from pathlib import Path

import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from services.fund_nav.data.akshare_client import get_fund_nav_daily

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "rt_snapshots"
OUT_DIR = ROOT / "data" / "features"


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def build_dataset(start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
    rows = []
    for day_dir in sorted(DATA_DIR.glob("[0-9]*")):
        day = day_dir.name
        if start_date and day < start_date.replace("-", ""):
            continue
        if end_date and day > end_date.replace("-", ""):
            continue
        path = day_dir / "estimates.jsonl"
        if not path.exists():
            continue
        for rec in _iter_jsonl(path):
            ts = rec.get("ts")
            code = rec.get("code")
            if not ts or not code:
                continue
            try:
                dt = datetime.fromisoformat(ts)
            except Exception:
                continue
            rows.append({
                "code": code,
                "date": dt.strftime("%Y-%m-%d"),
                "time": dt.strftime("%H:%M:%S"),
                "planb_return": rec.get("est_return"),
                "coverage": rec.get("estPricedCoverage", 0.0),
                "fundgz_return": (float(rec.get("gszzl")) / 100.0) if rec.get("gszzl") not in (None, "") else 0.0,
                "is_realtime": 1.0 if rec.get("is_realtime") else 0.0,
                "source": rec.get("source") or "",
            })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # label: final fund return (fund_ret) for that date
    labels = []
    for code in df["code"].unique():
        nav = get_fund_nav_daily(code)
        if nav is None or nav.empty:
            continue
        nav = nav.copy()
        nav["date"] = nav["date"].dt.strftime("%Y-%m-%d")
        labels.append(nav[["date", "fund_ret"]].assign(code=code))
    if labels:
        label_df = pd.concat(labels, ignore_index=True)
        df = df.merge(label_df, on=["code", "date"], how="left")

    # time feature
    def _minutes_since_open(t: str) -> int:
        try:
            hh, mm, _ = t.split(":")
            return int(hh) * 60 + int(mm) - (9 * 60 + 30)
        except Exception:
            return 0

    df["minutes_since_open"] = df["time"].apply(_minutes_since_open)
    df["source_holdings"] = (df["source"] == "holdings_tencent").astype(int)
    df["source_fundgz"] = (df["source"] == "fundgz").astype(int)

    return df


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = build_dataset()
    out = OUT_DIR / "rt_train.csv"
    df.to_csv(out, index=False)
    print(f"wrote {out}")
