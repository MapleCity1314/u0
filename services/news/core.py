from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, Iterable, List, Optional, Tuple


_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = _TAG_RE.sub("", text)
    return " ".join(text.split())


def parse_datetime(value: str | None) -> Tuple[Optional[datetime], str]:
    if not value:
        return None, ""
    try:
        dt = parsedate_to_datetime(value)
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        return dt, dt.isoformat()
    except (TypeError, ValueError):
        return None, ""


def normalize_items(
    raw_items: Iterable[Dict[str, str]],
    source_name: str,
    market: str,
) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for item in raw_items:
        title = strip_html(item.get("title", ""))
        if not title:
            continue
        summary = strip_html(item.get("summary", ""))
        dt, ts = parse_datetime(item.get("published"))
        normalized.append(
            {
                "ts": ts,
                "ts_epoch": dt.timestamp() if dt else None,
                "source": source_name,
                "market": market,
                "title": title,
                "url": item.get("url", ""),
                "summary": summary,
                "tags": item.get("tags", ""),
            }
        )
    return normalized


def is_recent(item: Dict[str, str], days: int) -> bool:
    ts_epoch = item.get("ts_epoch")
    if ts_epoch is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return datetime.fromtimestamp(ts_epoch, tz=timezone.utc) >= cutoff
