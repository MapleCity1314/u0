from __future__ import annotations

import json
import os
import urllib.request
from typing import Tuple


def _has_cjk(text: str) -> bool:
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False


def translate_text(text: str, source_lang: str = "en", target_lang: str = "zh") -> Tuple[str, bool]:
    if not text or _has_cjk(text) or source_lang == target_lang:
        return text, False

    endpoint = os.getenv("TRANSLATE_ENDPOINT", "https://libretranslate.com/translate")
    api_key = os.getenv("TRANSLATE_API_KEY", "")

    payload = {
        "q": text,
        "source": source_lang,
        "target": target_lang,
        "format": "text",
    }
    if api_key:
        payload["api_key"] = api_key

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "news-flash/0.1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            body = response.read().decode("utf-8")
        parsed = json.loads(body)
        translated = parsed.get("translatedText")
        if translated:
            return translated, True
    except Exception:
        pass

    return text, False
