from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from typing import Dict, List


_DATE_ANCHOR_RE = re.compile(
    r"(20\d{2}-\d{2}-\d{2}).{0,200}?<a[^>]+href=\"([^\"]+)\"[^>]*>([^<]+)</a>",
    re.S,
)


def _fetch_html(url: str, timeout: int = 12) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "news-module/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    return content.decode("utf-8", errors="ignore")


def parse_html_list(url: str) -> List[Dict[str, str]]:
    html_text = _fetch_html(url)
    items: List[Dict[str, str]] = []

    for match in _DATE_ANCHOR_RE.finditer(html_text):
        date_str, href, title = match.groups()
        title = html.unescape(title.strip())
        if not title:
            continue
        full_url = urllib.parse.urljoin(url, href.strip())
        items.append(
            {
                "title": title,
                "url": full_url,
                "published": date_str,
                "summary": "",
                "tags": "",
            }
        )

    return items
