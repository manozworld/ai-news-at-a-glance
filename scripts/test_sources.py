"""
Smoke-test the fetchers without calling the LLM.

Run with:   python scripts/test_sources.py

For each source, prints how many candidate articles were found and a sample.
Use this to debug scrapers when items aren't showing up.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sources import SOURCES  # noqa: E402
from fetch import fetch_source  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")

PASS = "✓"
FAIL = "✗"


def main():
    print(f"\nTesting {len(SOURCES)} sources...\n")
    summary = []
    for source in SOURCES:
        items = fetch_source(source)
        status = PASS if items else FAIL
        line = f"  {status} {source['name']:<20} {len(items):>3} items"
        print(line)
        if items:
            sample = items[0]
            print(f"      e.g. {sample.get('title', '(no title)')[:70]}")
            print(f"           {sample['url']}")
        summary.append((source["name"], len(items)))
        print()

    failed = [n for n, c in summary if c == 0]
    if failed:
        print(f"\n{FAIL} {len(failed)} source(s) returned no items: {', '.join(failed)}")
        print("  → check the URL or link_pattern for those entries in sources.py")
        sys.exit(1)
    else:
        print(f"\n{PASS} All sources returning items.")


if __name__ == "__main__":
    main()
