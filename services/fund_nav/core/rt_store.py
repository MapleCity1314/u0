import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from zoneinfo import ZoneInfo


def _base_dir() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / "data" / "rt_snapshots"


def store_snapshot(records: Iterable[dict]) -> None:
    try:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception:
        now = datetime.now()
    day = now.strftime("%Y%m%d")
    folder = _base_dir() / day
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "estimates.jsonl"

    with path.open("a", encoding="utf-8") as f:
        for r in records:
            payload = {"ts": now.isoformat(), **r}
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
