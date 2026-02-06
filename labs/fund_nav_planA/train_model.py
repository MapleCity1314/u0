from pathlib import Path

import joblib
import pandas as pd
from pandas.errors import EmptyDataError
import json
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "features" / "rt_train.csv"
MODEL_DIR = ROOT / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "planb_return",
    "coverage",
    "fundgz_return",
    "is_realtime",
    "minutes_since_open",
    "source_holdings",
    "source_fundgz",
]

if __name__ == "__main__":

    if not DATA.exists():
        print(f"missing dataset: {DATA}")
        raise SystemExit(1)
    if DATA.stat().st_size == 0:
        print(f"empty dataset: {DATA}")
        raise SystemExit(1)
    try:
        df = pd.read_csv(DATA)
    except EmptyDataError:
        print(f"empty dataset: {DATA}")
        raise SystemExit(1)
    df = df.dropna(subset=["fund_ret"])
    if df.empty:
        print("no labeled rows (fund_ret missing) — collect more snapshots")
        raise SystemExit(1)
    X = df[FEATURES].fillna(0.0)
    y = df["fund_ret"].astype(float)

    model = HistGradientBoostingRegressor(
        max_depth=6,
        learning_rate=0.05,
        max_iter=200,
        l2_regularization=0.1,
        random_state=42,
    )
    model.fit(X, y)

    out = MODEL_DIR / "planA_model.pkl"
    joblib.dump(model, out)
    meta = {
        "features": FEATURES,
        "rows": len(df),
        "model": "HistGradientBoostingRegressor",
    }
    (MODEL_DIR / "planA_model_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved model to {out}")
