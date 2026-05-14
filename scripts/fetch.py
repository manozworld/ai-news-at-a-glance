"""
Fetchers: pull a list of article candidates from each source.

Each fetcher returns a list of dicts:
  { "url": str, "title": str, "published": str (ISO date or None) }

Article BODY content is fetched separately (see fetch_article_text below)
so that summarize.py can call Claude with the real text, not the listing snippet.
"""

import re
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; AI-News-At-A-Glance/1.0; "
    "+https://github.com/manozworld/ai-news-at-a-glance)"
)
HEADERS = {"User-Agent": USER_AGENT}
TIMEOUT = 20


def _iso(dt):
    """Convert a feedparser time struct to ISO 8601, or None."""
    if not dt:
        return None
    try:
        return datetime(*dt[:6], tzinfo=timezone.utc).isoformat()
    except Exception:
        return None


def fetch_rss(source):
    """Fetch and parse an RSS/Atom feed."""
    logger.info(f"[{source['id']}] fetching RSS: {source['url']}")
    parsed = feedparser.parse(source["url"], request_headers=HEADERS)
    if parsed.bozo and not parsed.entries:
        logger.warning(f"[{source['id']}] RSS parse failed: {parsed.bozo_exception}")
        return []

    items = []
    for entry in parsed.entries:
        url = entry.get("link")
        title = entry.get("title", "").strip()
        if not url or not title:
            continue
        published = _iso(entry.get("published_parsed") or entry.get("updated_parsed"))
        items.append({"url": url, "title": title, "published": published})
    logger.info(f"[{source['id']}] found {len(items)} RSS items")
    return items


def fetch_scrape(source):
    """
    Fetch a listing page and extract article links matching `link_pattern`.

    We do NOT try to grab article body content here — just URLs and titles.
    The article body is fetched on demand in fetch_article_text().
    """
    logger.info(f"[{source['id']}] scraping: {source['url']}")
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"[{source['id']}] fetch failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    pattern = re.compile(source["link_pattern"])
    base = source.get("base_url", "")

    seen = set()
    items = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not pattern.match(href):
            continue
        full_url = urljoin(base, href) if href.startswith("/") else href
        if full_url in seen:
            continue
        seen.add(full_url)
        title = a.get_text(strip=True) or a.get("aria-label", "").strip()
        if not title or len(title) < 8:
            # Skip empty / nav-link matches; we'll try to recover the title
            # later from the article page's <title> or og:title tag.
            title = ""
        items.append({"url": full_url, "title": title, "published": None})
    logger.info(f"[{source['id']}] found {len(items)} scraped items")
    return items


def fetch_source(source):
    """Dispatch to the right fetcher based on source type."""
    try:
        if source["type"] == "rss":
            return fetch_rss(source)
        elif source["type"] == "scrape":
            return fetch_scrape(source)
        else:
            logger.warning(f"[{source['id']}] unknown type {source['type']!r}")
            return []
    except Exception as e:
        logger.exception(f"[{source['id']}] fetcher crashed: {e}")
        return []


def fetch_article_text(url, max_chars=8000):
    """
    Pull the article page and extract a reasonable chunk of body text plus
    metadata (title, published date) from common meta tags.

    Returns: { "title": str|None, "published": str|None, "text": str }
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"article fetch failed for {url}: {e}")
        return {"title": None, "published": None, "text": ""}

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title: prefer og:title, fall back to <title>
    title = None
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Published date: common meta tags
    published = None
    for sel in [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "pubdate"}),
        ("meta", {"name": "date"}),
        ("meta", {"itemprop": "datePublished"}),
    ]:
        tag = soup.find(*sel)
        if tag and tag.get("content"):
            published = tag["content"].strip()
            break

    # Body text: strip scripts/styles, then grab <article> or <main>, else body
    for bad in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
        bad.decompose()
    container = soup.find("article") or soup.find("main") or soup.body or soup
    text = " ".join(container.get_text(separator=" ").split())
    text = text[:max_chars]

    return {"title": title, "published": published, "text": text}
