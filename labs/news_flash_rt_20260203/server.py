from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List
from urllib.parse import parse_qs, urlparse

from core.output import append_jsonl, default_output_path
from core.pipeline import collect_items


class Store:
    def __init__(self, max_items: int = 1000) -> None:
        self._lock = threading.Lock()
        self._items: List[dict] = []
        self._max = max_items

    def add(self, items: List[dict]) -> None:
        if not items:
            return
        with self._lock:
            self._items.extend(items)
            # keep newest by ts when possible
            self._items.sort(key=lambda x: x.get("ts", ""), reverse=True)
            if len(self._items) > self._max:
                self._items = self._items[: self._max]

    def latest(self, limit: int) -> List[dict]:
        with self._lock:
            return list(self._items[:limit])


def start_poller(
    store: Store,
    interval: int,
    days: int,
    output: str,
    detail: bool,
    verbose: bool,
) -> None:
    seen: set[str] = set()
    while True:
        items = collect_items(seen, verbose, days, detail)
        if items:
            store.add(items)
            append_jsonl(items, output)
        time.sleep(interval)


class Handler(BaseHTTPRequestHandler):
    store: Store

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            return self._send_json({"ok": True})
        if parsed.path == "/latest":
            params = parse_qs(parsed.query)
            limit = int(params.get("limit", [50])[0])
            items = self.store.latest(limit)
            return self._send_json({"items": items, "count": len(items)})
        return self._send_json({"error": "not_found"}, status=404)


def main() -> None:
    parser = argparse.ArgumentParser(description="News flash polling API server")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--output", type=str, default=default_output_path())
    parser.add_argument("--no-detail", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    store = Store()
    Handler.store = store

    thread = threading.Thread(
        target=start_poller,
        args=(store, args.interval, args.days, args.output, not args.no_detail, args.verbose),
        daemon=True,
    )
    thread.start()

    server = HTTPServer((args.host, args.port), Handler)
    print(f"server: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
