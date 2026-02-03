from __future__ import annotations

import hashlib
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Set

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from services.core.database import SessionLocal
from services.logs.utils import log_event
from services.news.config import SOURCES
from services.news.core import is_recent, normalize_items
from services.news.detail import fetch_summary
from services.news.models.news import NewsItem
from services.news.sources.html_list import parse_html_list
from services.news.sources.json_api import parse_json_list
from services.news.sources.opml import parse_opml
from services.news.sources.rss import parse_feed
from services.news.translate import translate_text


def _fingerprint(item: Dict[str, str]) -> str:
    payload = f"{item.get('title','')}|{item.get('url','')}|{item.get('ts','')}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def _to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _store_items(db: Session, items: List[Dict[str, str]]) -> int:
    inserted = 0
    for item in items:
        fingerprint = item.get("fingerprint") or _fingerprint(item)
        exists = db.query(NewsItem).filter(NewsItem.fingerprint == fingerprint).first()
        if exists:
            continue
        try:
            entry = NewsItem(
                source=item.get("source"),
                market=item.get("market"),
                title=item.get("title"),
                url=item.get("url"),
                summary=item.get("summary"),
                tags=item.get("tags"),
                fingerprint=fingerprint,
                published_at=_to_datetime(item.get("ts")),
                search_vector=func.to_tsvector(
                    "simple",
                    f"{item.get('title','')} {item.get('summary','')}",
                ),
            )
            db.add(entry)
            inserted += 1
        except Exception as exc:
            log_event("error", "news.collect", "insert_failed", error=str(exc))
    if inserted:
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            log_event("error", "news.collect", "commit_failed", error=str(exc))
            return 0
    return inserted


def collect_once(days: int, detail: bool, verbose: bool = False) -> int:
    seen: Set[str] = set()
    all_items: List[Dict[str, str]] = []

    for source in SOURCES:
        try:
            if source.kind == "opml":
                feed_urls = parse_opml(source.url)
                for feed_url in feed_urls:
                    raw = parse_feed(feed_url)
                    batch = normalize_items(raw, source.name, source.market)
                    for item in batch:
                        item["lang"] = source.lang
                    all_items.extend(batch)
            elif source.kind == "html_list":
                raw = parse_html_list(source.url)
                batch = normalize_items(raw, source.name, source.market)
                for item in batch:
                    item["lang"] = source.lang
                all_items.extend(batch)
            elif source.kind == "json":
                raw = parse_json_list(source.url)
                batch = normalize_items(raw, source.name, source.market)
                for item in batch:
                    item["lang"] = source.lang
                all_items.extend(batch)
            else:
                raw = parse_feed(source.url)
                batch = normalize_items(raw, source.name, source.market)
                for item in batch:
                    item["lang"] = source.lang
                all_items.extend(batch)
        except Exception as exc:
            log_event("error", "news.collect", f"source_failed:{source.name}", error=str(exc))
            continue

    # recent filter + dedupe
    filtered: List[Dict[str, str]] = []
    for item in all_items:
        if not is_recent(item, days):
            continue
        fp = _fingerprint(item)
        if fp in seen:
            continue
        seen.add(fp)
        item["fingerprint"] = fp
        filtered.append(item)

    translate_enabled = os.getenv("NEWS_TRANSLATE_ENABLED", "true").lower() in ("1", "true", "yes")
    if translate_enabled:
        for item in filtered:
            if item.get("lang") and item["lang"] != "zh":
                try:
                    if item.get("title"):
                        item["title"], _ = translate_text(item.get("title", ""), item["lang"], "zh")
                    if item.get("summary"):
                        item["summary"], _ = translate_text(item.get("summary", ""), item["lang"], "zh")
                except Exception as exc:
                    log_event("error", "news.collect", "translate_failed", error=str(exc))

    if detail:
        for item in filtered:
            if item.get("url") and len(item.get("summary", "")) < 40:
                try:
                    summary = fetch_summary(item["url"])
                    if summary:
                        item["summary"] = summary
                except Exception as exc:
                    log_event("error", "news.collect", "summary_failed", error=str(exc))

    try:
        db = SessionLocal()
    except Exception as exc:
        log_event("error", "news.collect", "db_session_failed", error=str(exc))
        return 0
    try:
        return _store_items(db, filtered)
    except Exception as exc:
        log_event("error", "news.collect", "store_failed", error=str(exc))
        return 0
    finally:
        db.close()


def start_background_collector(interval: int = 60, days: int = 7, detail: bool = True) -> None:
    def loop():
        while True:
            try:
                inserted = collect_once(days=days, detail=detail)
                if inserted:
                    log_event("info", "news.collect", f"inserted:{inserted}")
            except Exception as exc:
                log_event("error", "news.collect", "collect_failed", error=str(exc))
            time.sleep(interval)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
