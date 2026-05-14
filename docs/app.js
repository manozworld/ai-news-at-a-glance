/* ============================================================
   AI News at a Glance — frontend logic
   ============================================================ */

const DATA_URL = "./news.json";

const state = {
  items: [],
  filtered: [],
  search: "",
  provider: "all",
  range: "all",        // "1" | "7" | "30" | "all"
};

const els = {
  feed: document.getElementById("feed"),
  empty: document.getElementById("emptyState"),
  loading: document.getElementById("loadingState"),
  search: document.getElementById("search"),
  clearSearch: document.getElementById("clearSearch"),
  dateChips: document.getElementById("dateChips"),
  providerChips: document.getElementById("providerChips"),
  lastUpdated: document.getElementById("lastUpdated"),
};

// ------------------------------------------------------------------
// Boot
// ------------------------------------------------------------------

init();

async function init() {
  try {
    const res = await fetch(DATA_URL, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.items = await res.json();
  } catch (err) {
    console.error("Failed to load news data:", err);
    els.loading.textContent =
      "Couldn't load news.json yet — once the GitHub Action runs, this page will fill in.";
    return;
  }

  if (!state.items.length) {
    els.loading.textContent =
      "No stories yet — the daily action will populate this shortly.";
    return;
  }

  els.loading.hidden = true;
  buildProviderChips();
  updateLastUpdated();
  wireEvents();
  render();
}

// ------------------------------------------------------------------
// UI assembly
// ------------------------------------------------------------------

function buildProviderChips() {
  // Unique provider list from data, preserving first-seen order
  const seen = new Map();
  for (const item of state.items) {
    if (!seen.has(item.provider_id)) {
      seen.set(item.provider_id, {
        id: item.provider_id,
        name: item.provider_name,
        color: item.provider_color,
      });
    }
  }
  for (const p of seen.values()) {
    const btn = document.createElement("button");
    btn.className = "chip";
    btn.dataset.provider = p.id;
    btn.textContent = p.name;
    btn.setAttribute("role", "tab");
    els.providerChips.appendChild(btn);
  }
}

function updateLastUpdated() {
  const newest = state.items
    .map((i) => i.published || i.fetched_at)
    .filter(Boolean)
    .sort()
    .pop();
  if (!newest) {
    els.lastUpdated.textContent = "";
    return;
  }
  const d = new Date(newest);
  if (isNaN(d)) {
    els.lastUpdated.textContent = "";
    return;
  }
  els.lastUpdated.textContent =
    "Last update · " +
    d.toLocaleDateString(undefined, {
      year: "numeric", month: "short", day: "numeric",
    });
}

function wireEvents() {
  // Search (debounced)
  let debounceId;
  els.search.addEventListener("input", (e) => {
    clearTimeout(debounceId);
    debounceId = setTimeout(() => {
      state.search = e.target.value.trim().toLowerCase();
      els.clearSearch.hidden = !state.search;
      render();
    }, 120);
  });
  els.clearSearch.addEventListener("click", () => {
    els.search.value = "";
    state.search = "";
    els.clearSearch.hidden = true;
    els.search.focus();
    render();
  });

  // Chip groups (event delegation)
  els.dateChips.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    setActive(els.dateChips, btn);
    state.range = btn.dataset.range;
    render();
  });
  els.providerChips.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    setActive(els.providerChips, btn);
    state.provider = btn.dataset.provider;
    render();
  });
}

function setActive(group, btn) {
  group.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
  btn.classList.add("active");
}

// ------------------------------------------------------------------
// Filtering
// ------------------------------------------------------------------

function applyFilters() {
  const now = Date.now();
  const cutoffMs =
    state.range === "all"
      ? 0
      : now - parseInt(state.range, 10) * 24 * 60 * 60 * 1000;

  const q = state.search;

  state.filtered = state.items.filter((item) => {
    // Provider filter
    if (state.provider !== "all" && item.provider_id !== state.provider) {
      return false;
    }

    // Date filter — fall back to fetched_at if published is missing
    if (cutoffMs > 0) {
      const dateStr = item.published || item.fetched_at;
      const t = dateStr ? Date.parse(dateStr) : NaN;
      if (isNaN(t) || t < cutoffMs) return false;
    }

    // Search filter — match across headline, bullets, why_it_matters, tags, provider
    if (q) {
      const haystack = [
        item.headline,
        item.why_it_matters,
        item.provider_name,
        (item.bullets || []).join(" "),
        (item.tags || []).join(" "),
      ]
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }

    return true;
  });
}

// ------------------------------------------------------------------
// Rendering
// ------------------------------------------------------------------

function render() {
  applyFilters();

  // Clear existing cards (preserve empty/loading nodes)
  const cards = els.feed.querySelectorAll(".card");
  cards.forEach((c) => c.remove());

  if (state.filtered.length === 0) {
    els.empty.hidden = false;
    return;
  }
  els.empty.hidden = true;

  const frag = document.createDocumentFragment();
  for (const item of state.filtered) {
    frag.appendChild(buildCard(item));
  }
  els.feed.appendChild(frag);
}

function buildCard(item) {
  const card = document.createElement("article");
  card.className = "card";
  card.style.setProperty("--provider-color", item.provider_color || "#888");

  const dateStr = formatDate(item.published || item.fetched_at);
  const q = state.search;

  card.innerHTML = `
    <div class="card-meta">
      <span class="card-provider">${escapeHtml(item.provider_name)}</span>
      <span class="card-date">${dateStr}</span>
    </div>
    <h2 class="card-headline">
      <a href="${escapeAttr(item.url)}" target="_blank" rel="noopener noreferrer">
        ${highlight(item.headline, q)}
      </a>
    </h2>
    <ul class="card-bullets">
      ${(item.bullets || [])
        .map((b) => `<li>${highlight(b, q)}</li>`)
        .join("")}
    </ul>
    <div class="card-why">
      <strong>Why it matters</strong>
      ${highlight(item.why_it_matters || "", q)}
    </div>
    ${
      item.tags && item.tags.length
        ? `<div class="card-tags">${item.tags
            .map((t) => `<span class="tag">${escapeHtml(t)}</span>`)
            .join("")}</div>`
        : ""
    }
  `;
  return card;
}

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function formatDate(s) {
  if (!s) return "";
  const d = new Date(s);
  if (isNaN(d)) return "";
  const now = new Date();
  const days = Math.round((now - d) / (1000 * 60 * 60 * 24));
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function escapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
function escapeAttr(s) {
  return escapeHtml(s);
}

function highlight(text, query) {
  const safe = escapeHtml(text);
  if (!query) return safe;
  // Escape regex special chars in the query
  const re = new RegExp(
    `(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
    "ig"
  );
  return safe.replace(re, "<mark>$1</mark>");
}
