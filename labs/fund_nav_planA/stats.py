from pathlib import Path
import json
from datetime import datetime

import pandas as pd

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from services.fund_nav.data.akshare_client import get_fund_nav_daily


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "rt_snapshots"


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


def main():
    rows = []
    for day_dir in sorted(DATA_DIR.glob("[0-9]*")):
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
            })

    if not rows:
        print("no snapshots found")
        return

    df = pd.DataFrame(rows)
    print(f"snapshot rows: {len(df)}")
    print(f"codes: {df['code'].nunique()}")
    print(f"date range: {df['date'].min()} -> {df['date'].max()}")

    # label availability
    label_rows = []
    for code in df["code"].unique():
        nav = get_fund_nav_daily(code)
        if nav is None or nav.empty:
            continue
        nav = nav.copy()
        nav["date"] = nav["date"].dt.strftime("%Y-%m-%d")
        label_rows.append(nav[["date"]].assign(code=code))

    if not label_rows:
        print("no labels available (fund_nav_daily empty)")
        return

    label_df = pd.concat(label_rows, ignore_index=True).drop_duplicates()
    merged = df.merge(label_df, on=["code", "date"], how="inner")

    print(f"labeled rows: {len(merged)}")
    if len(merged) > 0:
        print(f"labeled date range: {merged['date'].min()} -> {merged['date'].max()}")


if __name__ == "__main__":
    # add root to sys.path
    import sys
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
    main()