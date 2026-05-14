"""
Summarize an article into structured card data using Claude Haiku.

Returns a dict matching the frontend card schema:
  {
    "headline":       "concise rewritten title (6-12 words)",
    "bullets":        ["fact 1", "fact 2", "fact 3"],
    "why_it_matters": "one sentence on practical impact",
    "tags":           ["model-release", "agents", ...]
  }
"""

import json
import logging

import anthropic

logger = logging.getLogger(__name__)

# Latest Haiku alias — Anthropic auto-routes to the most recent Haiku version.
MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT = """You summarize AI-industry announcements into compact news cards.

You will be given the source provider, the article title, and the article body.

Return ONLY a JSON object with these exact keys:
  - "headline":       6-12 word rewrite of the title in your own words. Punchy, factual, no marketing fluff.
  - "bullets":        Array of 2-3 short factual statements. Each <= 14 words. Specific (numbers, model names, features). No filler.
  - "why_it_matters": ONE sentence (<= 20 words) describing the practical implication for developers, users, or the industry.
  - "tags":           Array of 1-3 short lowercase tags from this allowed set ONLY:
                      ["model-release","reasoning","multimodal","agents","voice","image","video",
                       "coding","safety","research","api","open-weights","pricing","product","tooling"]

Rules:
  - Output valid JSON only. No markdown fences, no commentary, no preamble.
  - Never quote more than 6 consecutive words from the source. Always rewrite.
  - If the article is not actually a news/announcement (e.g. a hiring page, policy doc, generic landing page), return: {"skip": true, "reason": "<short reason>"}
"""


def summarize(provider_name, title, url, body_text, client=None):
    """
    Return the parsed structured summary dict, or None on failure / skip.
    """
    if client is None:
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    user_content = (
        f"Provider: {provider_name}\n"
        f"URL: {url}\n"
        f"Article title: {title or '(unknown)'}\n\n"
        f"Article body:\n{body_text[:7000]}"
    )

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=600,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
    except Exception as e:
        logger.warning(f"Claude API error for {url}: {e}")
        return None

    raw = "".join(block.text for block in resp.content if block.type == "text").strip()

    # Defensive: strip markdown fences if the model slips
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed for {url}: {e}\nRaw: {raw[:300]}")
        return None

    if data.get("skip"):
        logger.info(f"Skipping {url}: {data.get('reason')}")
        return None

    # Light validation
    required = ("headline", "bullets", "why_it_matters")
    if not all(k in data for k in required):
        logger.warning(f"Missing keys in summary for {url}: {data}")
        return None
    if not isinstance(data["bullets"], list) or len(data["bullets"]) == 0:
        logger.warning(f"Invalid bullets for {url}")
        return None

    # Normalize
    data["bullets"] = [b.strip() for b in data["bullets"] if b and b.strip()][:3]
    data["tags"] = [t.strip().lower() for t in data.get("tags", [])][:3]

    return data
