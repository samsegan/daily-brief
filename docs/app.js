// Renders one day's brief from data/briefs/<date>.json. No build step, no framework.
// All text is inserted with textContent: brief content is model-written and
// feed-derived, so it is never parsed as HTML.

import { mountRain } from "./rain.js";
import { mountSettings } from "./settings.js";

const DATA_ROOT = "data";
const DATE_PARAM = "date";
const NEWS_SECTIONS = ["us", "world", "nyc"];
const BUSINESS_SECTION = "business";
const TRENDING_ANCHOR = "trending";
const NAV_ORDER = ["us", "world", "business", "nyc", TRENDING_ANCHOR];
const NAV_LABELS = { us: "U.S.", world: "World", business: "Markets", nyc: "New York City", [TRENDING_ANCHOR]: "Trending" };
const LEAN_LABELS = {
  left: "Left", lean_left: "Lean left", center: "Center", lean_right: "Lean right", right: "Right", unrated: "Web",
};
const GROUP_LABELS = {
  us_stocks: "US stocks", world_stocks: "World stocks", rates: "Interest rates", economy: "Economy",
  commodities: "Commodities", currencies: "Currencies", crypto: "Crypto",
};
const SIGNAL_LABELS = {
  google: "Google searches", wikipedia: "Wikipedia: most read yesterday", wikipedia_news: "Wikipedia: in the news",
  bluesky: "Bluesky trending", web: "Web",
};
const LEAN_CODES = { left: "L", lean_left: "LL", center: "C", lean_right: "LR", right: "R", unrated: "W" };
const BASIS_POINTS = 100;
const CORROBORATED_OUTLETS = 2;

// --- DOM helpers --------------------------------------------------------------

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === false || child === "") continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function link(href, text, attrs = {}) {
  return el("a", { href, target: "_blank", rel: "noopener noreferrer", ...attrs }, text);
}

function dot(lean) {
  return el("span", { class: `dot ${lean}`, title: LEAN_LABELS[lean], "data-code": LEAN_CODES[lean] });
}

// --- data -----------------------------------------------------------------------

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

function chosenDate(index) {
  const requested = new URLSearchParams(location.search).get(DATE_PARAM);
  return index.dates.includes(requested) ? requested : index.latest;
}

function formatDate(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  });
}

function formatTime(isoTimestamp) {
  return new Date(isoTimestamp).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/New_York", timeZoneName: "short",
  });
}

// --- stories --------------------------------------------------------------------

function refChips(refIds, refsById) {
  return el("span", { class: "chips" }, refIds.map((id) => {
    const ref = refsById.get(id);
    return link(ref.url, [dot(ref.lean), ref.outlet], { class: "chip", title: ref.title });
  }));
}

function spectrum(counts) {
  const total = counts.left + counts.center + counts.right + counts.unrated;
  const bar = el("span", { class: "spectrum-bar", "aria-hidden": "true" },
    ["left", "center", "right", "unrated"].filter((key) => counts[key] > 0).map((key) =>
      el("span", { class: key, style: `width:${(100 * counts[key]) / total}%` })));
  const parts = [`${counts.left} left`, `${counts.center} center`, `${counts.right} right`];
  if (counts.unrated) parts.push(`${counts.unrated} other`);
  return el("span", { class: "spectrum", title: "Outlets cited, by lean" }, bar, parts.join(" · "));
}

function factItem(fact, refsById) {
  const badge = fact.outlet_count >= CORROBORATED_OUTLETS
    ? el("span", { class: "badge solid" }, `${fact.outlet_count} outlets`)
    : el("span", { class: "badge thin" }, "1 source");
  return el("li", {}, fact.text, refChips(fact.refs, refsById), badge);
}

function disputesBlock(story, refsById) {
  if (!story.disputed.length) return null;
  return [
    el("div", { class: "label" }, "Where they disagree"),
    story.disputed.map((dispute) => el("div", { class: "dispute" },
      el("div", { class: "dispute-topic" }, dispute.topic),
      dispute.positions.map((position) =>
        el("div", { class: "position" }, position.claim, refChips(position.refs, refsById))))),
  ];
}

function framingBlock(story, refsById) {
  if (!story.framing.length) return null;
  return [
    el("div", { class: "label" }, "How it was framed"),
    story.framing.map((framing) => {
      const ref = refsById.get(framing.ref);
      return el("div", { class: "framing-row" },
        el("div", { class: "framing-outlet" }, dot(ref.lean), ref.outlet),
        link(ref.url, `“${ref.title}”`, { class: "framing-headline" }),
        framing.note ? el("div", { class: "framing-note" }, framing.note) : null);
    }),
  ];
}

function omissionsBlock(story, refsById) {
  if (!story.left_out.length) return null;
  return [
    el("div", { class: "label" }, "What some left out"),
    story.left_out.map((omission) => el("div", { class: "omission" },
      el("div", {}, omission.text, refChips(omission.refs, refsById)),
      el("div", { class: "omission-missing" }, `Not in: ${omission.missing_from.join(", ")}`))),
  ];
}

function sourcesBlock(story) {
  return [
    el("div", { class: "label" }, `Every source (${story.refs.length})`),
    el("ul", { class: "sources" }, story.refs.map((ref) => {
      const flag = ref.paywalled && !ref.read_full ? "paywalled · summary only" : ref.read_full ? "read in full" : "summary only";
      return el("li", {},
        dot(ref.lean),
        el("div", {},
          el("div", { class: "source-outlet" }, ref.outlet, el("span", { class: "source-flag" }, `· ${flag}`)),
          link(ref.url, ref.title, { class: "source-title" })),
        ref.takeaway ? el("div", { class: "source-takeaway" }, ref.takeaway) : null);
    })),
  ];
}

function storyCard(story) {
  const refsById = new Map(story.refs.map((ref) => [ref.id, ref]));
  return el("article", { class: "story module", id: `story-${story.id}` },
    el("div", { class: "story-meta" },
      story.region ? el("span", { class: "tag" }, story.region) : null,
      spectrum(story.lean_counts)),
    el("h3", {}, story.headline),
    el("p", { class: "summary" }, story.summary),
    el("div", { class: "label" }, "What we know"),
    el("ul", { class: "facts" }, story.facts.map((fact) => factItem(fact, refsById))),
    story.why_it_matters ? el("p", { class: "why" }, el("strong", {}, "Why it matters: "), story.why_it_matters) : null,
    el("details", { class: "deeper" },
      el("summary", {}, "Go deeper"),
      story.background ? [el("div", { class: "label" }, "Background"), el("p", {}, story.background)] : null,
      disputesBlock(story, refsById),
      framingBlock(story, refsById),
      omissionsBlock(story, refsById),
      story.social ? [el("div", { class: "label" }, "What people are saying"), el("p", {}, story.social)] : null,
      sourcesBlock(story)));
}

function storyList(stories, emptyText) {
  return stories.length ? stories.map(storyCard) : el("p", { class: "section-empty" }, emptyText);
}

// --- markets --------------------------------------------------------------------

function formatValue(quote) {
  const digits = quote.unit === "fx_rate" ? 4 : 2;
  const number = quote.last.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  if (quote.unit === "percent") return `${number}%`;
  if (quote.unit === "usd") return `$${number}`;
  return number;
}

function change(quote, base, label) {
  const delta = quote.unit === "percent" ? (quote.last - base) * BASIS_POINTS : (quote.last / base - 1) * 100;
  const text = quote.unit === "percent" ? `${delta >= 0 ? "+" : ""}${delta.toFixed(0)} bp` : `${delta >= 0 ? "+" : ""}${delta.toFixed(2)}%`;
  const direction = Math.abs(delta) < 0.005 ? "flat" : delta > 0 ? "up" : "down";
  return el("span", { class: direction }, `${label} ${text}`);
}

function quoteTile(quote) {
  const isMonthly = quote.group === "economy";
  return el("details", { class: "quote" },
    el("summary", {},
      el("div", { class: "quote-name" }, quote.name),
      el("div", { class: "quote-value" }, formatValue(quote)),
      el("div", { class: "quote-changes" },
        change(quote, quote.previous, isMonthly ? "prior" : "day"),
        isMonthly ? null : change(quote, quote.month_ago, "1 mo"))),
    el("p", { class: "quote-blurb" }, quote.blurb),
    el("div", { class: "quote-asof" }, `As of ${quote.as_of}`));
}

function quoteGroups(quotes) {
  const groups = new Map();
  for (const quote of quotes) {
    if (!groups.has(quote.group)) groups.set(quote.group, []);
    groups.get(quote.group).push(quote);
  }
  return [...groups].map(([group, items]) => el("div", { class: "quote-group" },
    el("h4", {}, GROUP_LABELS[group]),
    el("div", { class: "quotes" }, items.map(quoteTile))));
}

function marketsSection(markets, businessStories) {
  return [
    markets.summary ? el("p", { class: "markets-summary" }, markets.summary) : null,
    quoteGroups(markets.quotes),
    markets.movers.length ? [
      el("h3", { class: "subhead" }, "What moved, and why"),
      el("ul", { class: "movers" }, markets.movers.map((mover) =>
        el("li", {}, el("strong", {}, `${mover.name}: `), mover.why))),
    ] : null,
    el("h3", { class: "subhead" }, "Learn one thing"),
    el("div", { class: "concept module" }, el("h4", {}, markets.concept.term), el("p", {}, markets.concept.explanation)),
    markets.watch.length ? [
      el("h3", { class: "subhead" }, "Coming up"),
      el("ul", { class: "watch" }, markets.watch.map((item) => el("li", {}, item))),
    ] : null,
    el("h3", { class: "subhead" }, "Business stories"),
    storyList(businessStories, "No business stories today."),
  ];
}

// --- trending -------------------------------------------------------------------

function trendingSection(brief) {
  const signalsByKind = new Map();
  for (const item of brief.signals) {
    if (!signalsByKind.has(item.signal)) signalsByKind.set(item.signal, []);
    signalsByKind.get(item.signal).push(item);
  }
  return [
    el("p", { class: "section-empty" }, "What people are searching for and reading. Attention, not facts."),
    el("ul", { class: "trend-notes" }, brief.trending.map((note) => el("li", {},
      el("span", { class: "signal" }, SIGNAL_LABELS[note.signal]),
      el("span", { class: "trend-title" }, note.title),
      el("div", {}, note.context)))),
    [...signalsByKind].map(([signal, items]) => [
      el("div", { class: "label" }, SIGNAL_LABELS[signal]),
      el("ul", { class: "signal-list" }, items.map((item) => el("li", {},
        item.url ? link(item.url, item.title) : item.title, " ",
        el("span", { class: "signal-detail" }, item.detail)))),
    ]),
  ];
}

// --- page -----------------------------------------------------------------------

function section(id, title, ...content) {
  return el("section", { class: "section", id }, el("h2", { class: "section-title" }, el("span", { class: "plate" }, title)), content);
}

function renderNav() {
  document.getElementById("section-nav").replaceChildren(
    ...NAV_ORDER.map((id) => el("a", { href: `#${id}` }, NAV_LABELS[id])));
}

function renderEditionPicker(index, date) {
  const select = document.getElementById("edition");
  select.replaceChildren(...index.dates.map((value) => {
    const option = el("option", { value }, value);
    option.selected = value === date;
    return option;
  }));
  select.onchange = () => {
    const url = new URL(location.href);
    url.searchParams.set(DATE_PARAM, select.value);
    location.assign(url);
  };
}

function renderFooter(brief) {
  const { stats } = brief;
  document.getElementById("footer").replaceChildren(
    el("h2", {}, "How this works"),
    el("p", {},
      `Each morning the brief reads ${stats.articles.toLocaleString()} articles from ${stats.outlets} outlets, `,
      `groups them into stories, and an AI writer lists what several outlets agree on, where they differ, and what some left out. `,
      "Every fact links to the outlets that reported it. Paywalled outlets are read from their headline and summary only. ",
      "Summaries are machine-written: check the linked sources before relying on anything."),
    el("div", { class: "legend" }, ["left", "lean_left", "center", "lean_right", "right", "unrated"].map((lean) =>
      el("span", {}, dot(lean), LEAN_LABELS[lean]))),
    el("p", {}, "Leans are rough labels for each outlet's news coverage, based on public media-bias charts."),
    el("p", {}, `Articles fetched ${formatTime(brief.ingested_at)} · brief written ${formatTime(brief.generated_at)}`,
      stats.failed_fetches ? ` · ${stats.failed_fetches} feeds failed` : ""));
}

function renderBrief(brief) {
  const sections = new Map(brief.sections.map((block) => [block.id, block]));
  document.getElementById("dateline").textContent = formatDate(brief.date);
  const newsSection = (id) => section(id, sections.get(id).title,
    storyList(sections.get(id).stories, "Nothing major today."));
  document.getElementById("app").replaceChildren(
    el("div", { class: "overview" }, el("p", {}, el("span", { class: "prompt", "aria-hidden": "true" }, ">"), brief.overview)),
    newsSection(NEWS_SECTIONS[0]),
    newsSection(NEWS_SECTIONS[1]),
    section(BUSINESS_SECTION, "Markets", marketsSection(brief.markets, sections.get(BUSINESS_SECTION).stories)),
    newsSection(NEWS_SECTIONS[2]),
    section(TRENDING_ANCHOR, "Trending", trendingSection(brief)));
  renderFooter(brief);
}

async function main() {
  renderNav();
  mountSettings();
  mountRain();
  const app = document.getElementById("app");
  try {
    const index = await fetchJson(`${DATA_ROOT}/index.json`);
    const date = chosenDate(index);
    renderEditionPicker(index, date);
    renderBrief(await fetchJson(`${DATA_ROOT}/briefs/${date}.json`));
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  } catch (error) {
    app.replaceChildren(el("p", { class: "status" }, `No brief to show yet (${error.message}).`));
  }
}

main();
