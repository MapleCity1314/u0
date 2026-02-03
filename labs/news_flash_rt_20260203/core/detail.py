from __future__ import annotations

import html
import re
import urllib.request
from typing import Optional


_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"<script[\s\S]*?</script>", re.I)
_STYLE_RE = re.compile(r"<style[\s\S]*?</style>", re.I)
_P_RE = re.compile(r"<p[^>]*>([\s\S]*?)</p>", re.I)


def _fetch_html(url: str, timeout: int = 12) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "news-flash/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    return content.decode("utf-8", errors="ignore")


def _strip_html(text: str) -> str:
    text = html.unescape(text)
    text = _TAG_RE.sub("", text)
    return " ".join(text.split())


def fetch_summary(url: str, max_len: int = 240) -> Optional[str]:
    try:
        html_text = _fetch_html(url)
    except Exception:
        return None

    html_text = _SCRIPT_RE.sub(" ", html_text)
    html_text = _STYLE_RE.sub(" ", html_text)
    paragraphs = [
        _strip_html(match.group(1))
        for match in _P_RE.finditer(html_text)
    ]
    paragraphs = [p for p in paragraphs if p]
    if not paragraphs:
        text = _strip_html(html_text)
    else:
        text = " ".join(paragraphs)

    text = " ".join(text.split())
    if not text:
        return None
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text
