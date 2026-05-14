"""
AI news sources configuration.

Each source has:
  - id:    short slug used in JSON and in the frontend filter
  - name:  display name shown on the cards
  - color: hex color for the card accent stripe
  - type:  'rss' or 'scrape'
  - url:   feed URL (for rss) or listing-page URL (for scrape)
  - link_pattern: (scrape only) regex; only links matching this become articles

NOTES:
  - RSS URLs change. If a feed 404s, search the provider's site for "rss" or
    "feed" and update the URL here.
  - Scraped sources are fragile; if a redesign breaks one, update link_pattern.
"""

SOURCES = [
    {
        "id": "openai",
        "name": "OpenAI",
        "color": "#10A37F",
        "type": "rss",
        "url": "https://openai.com/news/rss.xml",
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "color": "#C96442",
        "type": "scrape",
        "url": "https://www.anthropic.com/news",
        "link_pattern": r"^/news/[a-z0-9\-]+$",
        "base_url": "https://www.anthropic.com",
    },
    {
        "id": "deepmind",
        "name": "Google DeepMind",
        "color": "#4285F4",
        "type": "rss",
        "url": "https://deepmind.google/blog/rss.xml",
    },
    {
        "id": "meta",
        "name": "Meta AI",
        "color": "#0866FF",
        "type": "scrape",
        "url": "https://ai.meta.com/blog/",
        "link_pattern": r"^https://ai\.meta\.com/blog/[a-z0-9\-]+/?$",
        "base_url": "https://ai.meta.com",
    },
    {
        "id": "xai",
        "name": "xAI",
        "color": "#1A1A1A",
        "type": "scrape",
        "url": "https://x.ai/news",
        "link_pattern": r"^/news/[a-z0-9\-]+$",
        "base_url": "https://x.ai",
    },
    {
        "id": "huggingface",
        "name": "Hugging Face",
        "color": "#FFB000",
        "type": "rss",
        "url": "https://huggingface.co/blog/feed.xml",
    },
    {
        "id": "mistral",
        "name": "Mistral",
        "color": "#FA520F",
        "type": "scrape",
        "url": "https://mistral.ai/news",
        "link_pattern": r"^/news/[a-z0-9\-]+$",
        "base_url": "https://mistral.ai",
    },
]

# How many of the newest items to consider per source on each run.
# Anything we've already summarized (matched by URL hash) is skipped, so this
# is just an upper bound on "how far back to look".
MAX_ITEMS_PER_SOURCE = 10
