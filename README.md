# AI News at a Glance

A self-hosted, daily-updated digest of releases and announcements from the major
AI labs. A GitHub Action fetches new posts once a day, Claude Haiku turns each
into a structured card (headline + 3 bullets + a "why it matters" line), and a
static page on GitHub Pages renders them with filters and search.

Lives at: **https://manozworld.github.io/ai-news-at-a-glance**

---

## Setup (one time)

1. **Create the repo.** On github.com → New repository → name it
   `ai-news-at-a-glance`, public, with a README. Then drop these files in
   (or clone, copy them across, commit, push).

2. **Add your Anthropic API key.**
   Repo → **Settings** → **Secrets and variables** → **Actions** → **New
   repository secret**. Name: `ANTHROPIC_API_KEY`. Value: your key from
   <https://console.anthropic.com>.

3. **Enable GitHub Pages.**
   Repo → **Settings** → **Pages** → Source: **Deploy from a branch**,
   Branch: **main**, Folder: **/docs**, Save. After ~1 minute, your site is
   live at `https://manozworld.github.io/ai-news-at-a-glance`.

4. **Run the workflow once manually** to populate the first batch of news.
   Repo → **Actions** → **Fetch AI news** → **Run workflow**.
   It'll take 1-3 minutes; when it finishes, `docs/news.json` is committed,
   and the page picks it up on the next reload.

That's it. From then on, it runs daily at 06:00 UTC.

---

## How it works

```
.github/workflows/fetch-news.yml   # daily cron + manual trigger
scripts/
  sources.py                       # which sites to pull from
  fetch.py                         # RSS + HTML scrapers
  summarize.py                     # Claude Haiku → structured JSON
  run.py                           # orchestrator
docs/
  index.html                       # the page itself
  style.css
  app.js                           # filters, search, rendering
  news.json                        # the data the page reads
```

Each run:
1. Loads `docs/news.json` (the existing archive).
2. For each source in `sources.py`, fetches the listing and finds candidate URLs.
3. Skips URLs it's already summarized (matched by a hash of the URL).
4. For new URLs, downloads the article page, extracts the body text, and asks
   Claude Haiku for a structured `{headline, bullets, why_it_matters, tags}`.
5. Appends new items and writes `news.json` back. The action commits the diff.

The frontend just `fetch()`es `news.json` and renders. No backend, no DB.

---

## Cost

Claude Haiku is cheap. A run summarizing ~20 new articles (very generous; most
days will be 0-5) costs well under a cent. Expect a few cents per month total.

## Configuring sources

Open `scripts/sources.py`. Each entry has:

- **`id`** — slug used in JSON and the URL filter
- **`name`** — display name on the card
- **`color`** — hex string used for the accent stripe
- **`type`** — `"rss"` for proper feeds, `"scrape"` for listing-page scraping
- **`url`** — feed URL or listing-page URL
- **`link_pattern`** (scrape only) — regex; only matching links become articles
- **`base_url`** (scrape only) — used to resolve relative URLs

To add a source: copy an existing entry, swap in the new values, commit, push.
To remove one: delete the entry. (Existing items from that provider remain in
`news.json` until they age out.)

## Troubleshooting

**The Action ran but no new items appeared.**
Check the run log (Actions → click the latest run). You'll see one line per
source: `found N items`. If a source consistently shows 0, its URL or
`link_pattern` is stale — open the site in a browser, view source, and update.

**The Action fails with `ANTHROPIC_API_KEY is not set`.**
You forgot step 2. Add the secret in repo settings.

**GitHub Pages 404s.**
Settings → Pages → confirm source is `main` branch, `/docs` folder. Wait a
minute. Hard refresh.

**A scraper started returning 403 or empty results.**
Some sites add Cloudflare-style bot protection. Workarounds: switch the source
to RSS if they offer one, or skip it and substitute another aggregator.

**Cards look wrong / styles broken.**
Make sure `style.css`, `app.js`, and `news.json` are all in `docs/` next to
`index.html`, not at the repo root.

## Scaling later (when you're ready)

Some natural next steps:

- Add a `categories.json` or hand-curated weighting to surface "big" releases.
- Switch from one-file `news.json` to per-month files (`news-2026-05.json`) once
  the archive crosses a few thousand items.
- Add an RSS feed *of your own* — generate `docs/feed.xml` from the same data.
- Subscribe via email — Buttondown or similar can pull from your RSS.
- Add more sources: Cohere, Stability, AI21, Adept, Inflection, Perplexity,
  Together, Cerebras, Groq blogs, etc.
- Move heavy filtering server-side once `news.json` gets large (>1MB).

Nothing here is locked in. The whole thing is ~600 lines of code.
