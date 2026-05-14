# Notes for Claude Code

This file is auto-loaded when you open this folder in Claude Code. It exists
so that you (Claude) have full context on what this project is, how it was
built, and what's likely to come up — without the user having to re-explain.

---

## What this is

A static, GitHub-hosted aggregator of AI announcements from the major labs
(OpenAI, Anthropic, Google DeepMind, Meta AI, xAI, Hugging Face, Mistral).
Lives at `https://manozworld.github.io/ai-news-at-a-glance`.

A daily GitHub Action fetches each source, asks **Claude Haiku** to turn each
new article into a structured `{headline, bullets, why_it_matters, tags}` card,
and commits the updated `docs/news.json` back to the repo. The static page in
`docs/` renders the cards with filters (date, provider) and full-text search.

---

## Origin

Scaffolded in a Claude.ai conversation with the user (`manozworld`). The user
is not a heavy developer — they want this to work, want to add features
incrementally, and care about costs being near-zero. Be direct, skip ceremony,
explain trade-offs briefly when relevant.

The project has **not been run end-to-end yet**. The very first GitHub Action
run is where reality meets the scaffolding — expect 1-3 sources to need URL
or selector tweaks. See "Likely first-run issues" below.

---

## File map

```
.github/workflows/fetch-news.yml   GitHub Action: daily cron + manual trigger
scripts/sources.py                 Source definitions (URLs, types, selectors)
scripts/fetch.py                   RSS parser + HTML scraper
scripts/summarize.py               Claude Haiku call, JSON-structured output
scripts/run.py                     Orchestrator (called by the Action)
scripts/test_sources.py            Smoke test for fetchers — NO API calls
docs/index.html                    The page
docs/style.css                     Editorial/magazine styling
docs/app.js                        Filters, search, rendering (vanilla JS)
docs/news.json                     Data file written by the Action
requirements.txt                   Python deps
README.md                          User-facing setup
CLAUDE.md                          This file
```

---

## Key design decisions and why

- **Static site + JSON file, no database.** Free GitHub Pages hosting, free
  Actions minutes (public repo), no DB to manage. Scales fine to thousands of
  items. When it stops scaling, switch `news.json` → monthly shards or move to
  Supabase.
- **GitHub Action commits data back to the repo.** This is unconventional but
  works perfectly for this volume. The commit also acts as an audit log.
- **Claude Haiku, not Sonnet/Opus.** Summarization is a simple structured-
  extraction task; Haiku is 10x cheaper and plenty good. Model alias used:
  `claude-haiku-4-5`. The `summarize.py` system prompt locks output to a JSON
  schema, temperature 0.
- **Vanilla JS frontend.** No build step, no package.json, no node_modules.
  The whole frontend is 3 files Claude Code can edit directly.
- **URL-hash dedup.** First 12 hex chars of `sha1(url)` is the item ID. Idempotent
  re-runs.
- **Per-source resilience.** A failing source logs and is skipped — never kills
  the whole run.
- **Conservative skipping in the summarizer.** The prompt returns
  `{"skip": true}` for non-announcement pages (careers, policy, generic
  landing pages). If the user complains about missing stories, that's the first
  place to look.

---

## Owner preferences (carry these forward)

- **GitHub:** `manozworld` — repo `ai-news-at-a-glance`, public
- **Site:** `https://manozworld.github.io/ai-news-at-a-glance`
- **Cadence:** daily at 06:00 UTC
- **Model:** Claude Haiku (cost matters)
- **Style:** editorial, calm, scannable — don't add visual noise without reason

---

## Likely first-run issues (debug in this order)

1. **Empty results from a scraped source.** Almost certain for at least one of
   Anthropic, Meta AI, xAI, Mistral. Run `python scripts/test_sources.py` to
   see counts per source. For any source returning 0, open the listing URL in
   a browser, view source, find the article-link pattern, update
   `link_pattern` in `sources.py`.

2. **RSS feed 404.** OpenAI, Google DeepMind, and Hugging Face are configured
   as RSS. If a URL is stale, search the provider's site for "rss" or "feed",
   or switch the source to `type: scrape`.

3. **Workflow fails on first push because `secrets.ANTHROPIC_API_KEY` is
   missing.** The user has been instructed to add it. If they ask why it's
   failing, point them at repo Settings → Secrets and variables → Actions.

4. **Pages doesn't show up.** Settings → Pages → confirm `main` branch, `/docs`
   folder. Hard refresh.

5. **Article body too short.** Some sources put the body behind JS. `run.py`
   skips items with <200 chars of body. If a real announcement is being
   skipped, that source needs a different content selector or a JS-rendering
   approach (Playwright, but that's overkill for v1).

---

## Open follow-ups (roadmap, not required)

- Add an RSS feed *of the digest itself* → `docs/feed.xml` generated by `run.py`
- Add more sources: Cohere, Stability, Perplexity, Together, Groq, Cerebras, AI21
- Per-tag filter chips (currently only date and provider)
- "Star" or save-for-later (would need a tiny bit of state — `localStorage` only,
  no backend)
- Monthly shards once `news.json` > 1 MB
- Email digest via Buttondown (pulls from RSS once that exists)

---

## How to test things without burning API credits

```bash
# Just check which sources are reachable and what they return
python scripts/test_sources.py

# Dry-run the whole pipeline (no Anthropic key needed, won't call API)
ANTHROPIC_API_KEY=fake python scripts/run.py
# (will fail at the summarize step but you'll see fetch behavior first)

# Real run, locally (requires real ANTHROPIC_API_KEY env var)
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/run.py
```

The user should NOT commit their key to the repo. If you find yourself about
to write a key into a file, stop and use environment variables instead.

---

## Frontend notes for future edits

- Fonts: Fraunces (display serif, variable) + IBM Plex Sans (body) + IBM Plex
  Mono (metadata). Loaded from Google Fonts in `index.html`.
- Colors live in CSS variables at the top of `style.css`; full dark-mode
  support via `prefers-color-scheme`.
- Provider color stripes are set per-card via inline `--provider-color`
  custom property from `app.js`.
- Search uses simple `String.includes()` across headline + bullets +
  why_it_matters + tags + provider name. Debounced 120ms.
- Date chips compare against `item.published || item.fetched_at`.

If the user asks for a redesign, ask which direction (more editorial?
more dense/dashboard? newspaper-like?) before changing colors and fonts —
the current choice was deliberate.
