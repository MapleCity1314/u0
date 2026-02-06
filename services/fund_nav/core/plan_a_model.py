import json
import os
from pathlib import Path
from typing import Any

_MODEL = None
_META = None


def _model_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / "data" / "models" / "planA_model.pkl"


def _meta_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / "data" / "models" / "planA_model_meta.json"


def load_model() -> Any | None:
    global _MODEL, _META
    if _MODEL is not None:
        return _MODEL
    model_path = _model_path()
    if not model_path.exists():
        return None
    try:
        import joblib  # type: ignore
    except Exception:
        return None
    try:
        _MODEL = joblib.load(model_path)
    except Exception:
        _MODEL = None
        return None
    meta_path = _meta_path()
    if meta_path.exists():
        try:
            _META = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            _META = None
    return _MODEL


def get_meta() -> dict | None:
    return _META if _META is not None else None


def predict(features: dict) -> float | None:
    model = load_model()
    if model is None:
        return None
    try:
        # expected order
        order = [
            "planb_return",
            "coverage",
            "fundgz_return",
            "is_realtime",
            "minutes_since_open",
            "source_holdings",
            "source_fundgz",
        ]
        vec = [features.get(k, 0.0) for k in order]
        pred = model.predict([vec])[0]
        return float(pred)
    except Exception:
        return None
