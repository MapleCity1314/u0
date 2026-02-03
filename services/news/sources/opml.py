from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from typing import List


def _fetch_xml(url: str, timeout: int = 12) -> ET.Element:
    request = urllib.request.Request(url, headers={"User-Agent": "news-module/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    return ET.fromstring(content)


def parse_opml(url: str) -> List[str]:
    root = _fetch_xml(url)
    feeds: List[str] = []
    for outline in root.findall(".//outline"):
        xml_url = outline.attrib.get("xmlUrl") or outline.attrib.get("xmlurl")
        if xml_url:
            feeds.append(xml_url.strip())
    return feeds
