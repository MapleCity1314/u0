from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Dict, List


def _fetch_json(url: str, timeout: int = 12) -> Dict:
    request = urllib.request.Request(url, headers={"User-Agent": "news-module/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    return json.loads(content.decode("utf-8", errors="ignore"))


def _extract_list(payload: object) -> List[Dict]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("data", "results", "items", "announcements", "datas"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for subkey in ("data", "rows", "list", "items"):
                subval = value.get(subkey)
                if isinstance(subval, list):
                    return subval
    return []


def parse_json_list(url: str) -> List[Dict[str, str]]:
    payload = _fetch_json(url)
    items = _extract_list(payload)
    output: List[Dict[str, str]] = []
    base = "https://www.szse.cn"

    for item in items:
        if not isinstance(item, dict):
            continue
        title = (
            item.get("title")
            or item.get("announcementTitle")
            or item.get("headline")
            or item.get("artTitle")
        )
        if not title:
            continue
        url_value = item.get("url") or item.get("link") or item.get("docUrl") or ""
        if url_value:
            url_value = urllib.parse.urljoin(base, url_value)
        published = (
            item.get("publishTime")
            or item.get("publishTimeStr")
            or item.get("pubDate")
            or item.get("publishDate")
            or item.get("releaseTime")
            or ""
        )
        summary = item.get("summary") or item.get("abstract") or item.get("content") or ""
        output.append(
            {
                "title": str(title),
                "url": str(url_value),
                "published": str(published),
                "summary": str(summary),
                "tags": "",
            }
        )

    return output
