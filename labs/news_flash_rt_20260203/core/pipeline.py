from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set

from config import SOURCES
from core.dedupe import dedupe_items
from core.detail import fetch_summary
from core.normalize import normalize_items
from core.translate import translate_text
from sources import parse_feed, parse_html_list, parse_json_list, parse_opml


def _log(message: str, enabled: bool) -> None:
    if not enabled:
        return
    print(message)


def _is_recent(item: Dict[str, str], days: int) -> bool:
    ts_epoch = item.get("ts_epoch")
    if ts_epoch is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return datetime.fromtimestamp(ts_epoch, tz=timezone.utc) >= cutoff


def collect_items(seen: Set[str], verbose: bool, days: int, detail: bool) -> List[Dict[str, str]]:
    all_items: List[Dict[str, str]] = []

    for source in SOURCES:
        try:
            if source.kind == "opml":
                feed_urls = parse_opml(source.url)
                _log(f"[opml] {source.name}: {len(feed_urls)} feeds", verbose)
                for feed_url in feed_urls:
                    try:
                        raw = parse_feed(feed_url)
                    except Exception as exc:
                        _log(f"[rss] {feed_url} failed: {exc}", verbose)
                        continue
                    normalized = normalize_items(raw, source.name, source.market, source.lang)
                    all_items.extend(normalized)
            elif source.kind == "html_list":
                raw = parse_html_list(source.url)
                normalized = normalize_items(raw, source.name, source.market, source.lang)
                _log(f"[html] {source.name}: {len(normalized)} items", verbose)
                all_items.extend(normalized)
            elif source.kind == "json":
                raw = parse_json_list(source.url)
                normalized = normalize_items(raw, source.name, source.market, source.lang)
                _log(f"[json] {source.name}: {len(normalized)} items", verbose)
                all_items.extend(normalized)
            else:
                raw = parse_feed(source.url)
                normalized = normalize_items(raw, source.name, source.market, source.lang)
                _log(f"[rss] {source.name}: {len(normalized)} items", verbose)
                all_items.extend(normalized)
        except Exception as exc:
            _log(f"[source] {source.name} failed: {exc}", verbose)
            continue

    # time filter
    all_items = [item for item in all_items if _is_recent(item, days)]

    # translation
    for item in all_items:
        if item.get("lang") and item["lang"] != "zh":
            if item.get("title"):
                item["title"], _ = translate_text(item.get("title", ""), item["lang"], "zh")
            if item.get("summary"):
                item["summary"], _ = translate_text(item.get("summary", ""), item["lang"], "zh")

    # detail enrichment
    if detail:
        for item in all_items:
            if item.get("url") and len(item.get("summary", "")) < 40:
                summary = fetch_summary(item["url"])
                if summary:
                    item["summary"] = summary

    fresh = dedupe_items(all_items, seen)

    # strip internal fields
    for item in fresh:
        item.pop("lang", None)
        item.pop("ts_epoch", None)

    return fresh
