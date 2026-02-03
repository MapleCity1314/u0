from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, List


def _fetch_xml(url: str, timeout: int = 12) -> ET.Element:
    request = urllib.request.Request(url, headers={"User-Agent": "news-flash/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    return ET.fromstring(content)


def _get_text(node: ET.Element | None, path: str) -> str:
    if node is None:
        return ""
    found = node.find(path)
    if found is None or found.text is None:
        return ""
    return found.text.strip()


def parse_feed(url: str) -> List[Dict[str, str]]:
    root = _fetch_xml(url)
    tag = root.tag.lower()

    if tag.endswith("rss") or tag.endswith("rdf"):
        return _parse_rss(root)
    if tag.endswith("feed"):
        return _parse_atom(root)

    # Fallback: try RSS first
    items = _parse_rss(root)
    return items if items else _parse_atom(root)


def _parse_rss(root: ET.Element) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    channel = root.find("channel")
    if channel is None:
        channel = root
    for item in channel.findall("item"):
        title = _get_text(item, "title")
        link = _get_text(item, "link")
        pub_date = _get_text(item, "pubDate")
        description = _get_text(item, "description")
        category_nodes = item.findall("category")
        tags = ",".join([node.text.strip() for node in category_nodes if node.text])
        items.append(
            {
                "title": title,
                "url": link,
                "published": pub_date,
                "summary": description,
                "tags": tags,
            }
        )
    return items


def _parse_atom(root: ET.Element) -> List[Dict[str, str]]:
    ns = "{http://www.w3.org/2005/Atom}"
    items: List[Dict[str, str]] = []
    for entry in root.findall(f"{ns}entry"):
        title = _get_text(entry, f"{ns}title")
        updated = _get_text(entry, f"{ns}updated") or _get_text(entry, f"{ns}published")
        summary = _get_text(entry, f"{ns}summary") or _get_text(entry, f"{ns}content")
        link_node = entry.find(f"{ns}link")
        link = ""
        if link_node is not None:
            link = link_node.attrib.get("href", "")
        items.append(
            {
                "title": title,
                "url": link,
                "published": updated,
                "summary": summary,
                "tags": "",
            }
        )
    return items
