from __future__ import annotations

import argparse
import time
from typing import Set

from core.output import append_jsonl, default_output_path, print_items
from core.pipeline import collect_items


def main() -> None:
    parser = argparse.ArgumentParser(description="Real-time news flash aggregator")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval (seconds)")
    parser.add_argument("--once", action="store_true", help="Run a single fetch then exit")
    parser.add_argument("--output", type=str, default=default_output_path(), help="JSONL output path")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    parser.add_argument("--verbose", action="store_true", help="Print source errors and counts")
    parser.add_argument("--days", type=int, default=7, help="Keep items from the last N days")
    parser.add_argument("--no-detail", action="store_true", help="Skip detail page fetching")
    args = parser.parse_args()

    seen: Set[str] = set()

    while True:
        items = collect_items(seen, args.verbose, args.days, not args.no_detail)
        if items:
            print_items(items, color=not args.no_color)
            append_jsonl(items, args.output)
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
