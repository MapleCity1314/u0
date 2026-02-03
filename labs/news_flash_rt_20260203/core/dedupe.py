from __future__ import annotations

import hashlib
from typing import Dict, Iterable, List, Set


def _fingerprint(item: Dict[str, str]) -> str:
    payload = f"{item.get('title','')}|{item.get('url','')}".encode("utf-8")
    return hashlib.sha1(payload).hexdigest()


def dedupe_items(items: Iterable[Dict[str, str]], seen: Set[str]) -> List[Dict[str, str]]:
    fresh: List[Dict[str, str]] = []
    for item in items:
        fp = _fingerprint(item)
        if fp in seen:
            continue
        seen.add(fp)
        fresh.append(item)
    return fresh
