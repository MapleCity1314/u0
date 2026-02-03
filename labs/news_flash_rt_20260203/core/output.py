from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, Iterable


_ANSI_RESET = "\033[0m"
_ANSI_COLORS = {
    "CN": "\033[38;5;214m",
    "HK": "\033[38;5;81m",
    "US": "\033[38;5;120m",
    "MACRO": "\033[38;5;111m",
    "COMMODITY": "\033[38;5;215m",
}


def _format_line(item: Dict[str, str], color: bool) -> str:
    ts = item.get("ts", "")
    market = item.get("market", "")
    source = item.get("source", "")
    title = item.get("title", "")
    if color and market in _ANSI_COLORS:
        color_code = _ANSI_COLORS[market]
        return f"{color_code}[{ts}] [{market}] {title} ({source}){_ANSI_RESET}"
    return f"[{ts}] [{market}] {title} ({source})"


def print_items(items: Iterable[Dict[str, str]], color: bool = True) -> None:
    for item in items:
        print(_format_line(item, color))


def append_jsonl(items: Iterable[Dict[str, str]], path: str) -> None:
    if not items:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def default_output_path() -> str:
    stamp = datetime.utcnow().strftime("%Y%m%d")
    return os.path.join("data", f"news_flash_{stamp}.jsonl")
