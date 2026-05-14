"""
Entry point: fetch → dedupe → summarize → save.

Run locally:    python scripts/run.py
Run in CI:      same, but ANTHROPIC_API_KEY comes from GitHub Secrets.

Reads/writes:   docs/news.json
Max items kept: NEWS_KEEP (most recent, by published date)
"""

import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

import anthropic

# Make `from sources import ...` work regardless of where the script is run from
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sources import SOURCES, MAX_ITEMS_PER_SOURCE  # noqa: E402
from fetch import fetch_source, fetch_article_text  # noqa: E402
from summarize import summarize  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run")

REPO_ROOT = Path(__file__).resolve().parent.parent
NEWS_FILE = REPO_ROOT / "docs" / "news.json"
NEWS_KEEP = 300        # cap total stored items; tune as you like
SLEEP_BETWEEN_CALLS = 1.0   # be polite to source sites and to the API


def url_hash(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def load_existing():
    if NEWS_FILE.exists():
        try:
            return json.loads(NEWS_FILE.read_text())
        except Exception as e:
            logger.warning(f"news.json unreadable, starting fresh: {e}")
    return []


def save(items):
    # Sort newest first by published date (fallback: fetched_at)
    items.sort(
        key=lambda x: x.get("published") or x.get("fetched_at") or "",
        reverse=True,
    )
    items = items[:NEWS_KEEP]
    NEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    NEWS_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False))
    logger.info(f"Wrote {len(items)} items to {NEWS_FILE}")


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY is not set. Aborting.")
        sys.exit(1)

    client = anthropic.Anthropic()
    existing = load_existing()
    known_ids = {item["id"] for item in existing}
    new_count = 0
    fail_count = 0

    for source in SOURCES:
        candidates = fetch_source(source)[:MAX_ITEMS_PER_SOURCE]
        for candidate in candidates:
            item_id = url_hash(candidate["url"])
            if item_id in known_ids:
                continue

            logger.info(f"[{source['id']}] new: {candidate['url']}")
            article = fetch_article_text(candidate["url"])
            title = candidate["title"] or article["title"] or "(untitled)"
            published = candidate["published"] or article["published"]

            if not article["text"] or len(article["text"]) < 200:
                logger.info("  skipping (too little body text)")
                fail_count += 1
                continue

            summary = summarize(
                provider_name=source["name"],
                title=title,
                url=candidate["url"],
                body_text=article["text"],
                client=client,
            )
            if summary is None:
                fail_count += 1
                time.sleep(SLEEP_BETWEEN_CALLS)
                continue

            existing.append({
                "id": item_id,
                "provider_id": source["id"],
                "provider_name": source["name"],
                "provider_color": source["color"],
                "url": candidate["url"],
                "original_title": title,
                "headline": summary["headline"],
                "bullets": summary["bullets"],
                "why_it_matters": summary["why_it_matters"],
                "tags": summary.get("tags", []),
                "published": published,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            known_ids.add(item_id)
            new_count += 1
            time.sleep(SLEEP_BETWEEN_CALLS)

    save(existing)
    logger.info(f"Done. {new_count} new items, {fail_count} skipped/failed.")


if __name__ == "__main__":
    main()
