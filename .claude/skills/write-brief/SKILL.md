---
name: write-brief
description: Write and publish the Daily Brief for today (or a given date) from that day's ingest bundle. Use when asked to write, run, redo or publish the brief.
---

# Write the daily brief

The ingest workflow has already fetched ~1,500 articles, market numbers and
trend signals into a bundle on the `ingest` branch. Your job is to turn it into
`docs/data/briefs/<date>.json`, which https://samsegan.github.io/daily-brief/
renders. You write text and pick reference ids; `brief.build` fills in every
outlet name, lean, URL and number from the bundle and rejects anything that
doesn't check out.

## 1. Set up

1. `date` is today in New York (`TZ=America/New_York date +%F`) unless you were given one.
2. `pip install -e .` if `python -c "import brief"` fails.
3. `scripts/pull-ingest.sh <date>`. If there's no bundle for the date, run the
   `ingest.yml` workflow (GitHub MCP `actions_run_trigger`, method
   `run_workflow`, ref `main`), wait for it to finish, and pull again. Never
   write a brief without a bundle.
4. Write the digests:
   ```
   mkdir -p data/drafts/<date>
   for s in us world business nyc; do
     python -m brief.digest --date <date> --section $s --summaries > data/drafts/<date>/digest-$s.md
   done
   python -m brief.digest --date <date> --front > data/drafts/<date>/digest-front.md
   ```

## 2. Write the four sections in parallel

Spawn one subagent per section (us, world, business, nyc) in a single message.
Give each one: the date, its digest path, the path to
`.claude/skills/write-brief/draft-format.md`, the "Rules for every story"
section below copied in full, its section's line from "Section notes", and its
output path `data/drafts/<date>/<section>.json`. Tell it to finish by running
`python -m brief.build --date <date> --check <section>`, which checks its file
against the bundle, and to fix what it reports until it says the file is valid.

While they work, write `front.json` yourself (step 3).

## Rules for every story

**Choosing.** Rank stories by how widely they're covered across the spectrum
(the digest shows left/center/right/unrated counts per cluster), by consequence
for people's lives, money, safety or rights, and by what's new today. Skip
celebrity, sports and lifestyle news unless it dominates coverage. Clusters are
hints: merge two that are the same event, and split one that mixes events. If
only one side's outlets cover a story, say so in `why_it_matters`.

**Reading.** For each story, read 2-4 open articles in full with WebFetch,
picking from different leans when you can (one left-leaning, one center, one
right-leaning), and mark those coverage notes `read_full: true`. For outlets
marked `$paywall`, work from the headline and summary in the digest only. Don't
try to get around a paywall. If WebFetch can't reach news sites at all (some
environments block them), work from the digest's summaries and WebSearch, set
every `read_full` to false, and leave `left_out` empty. Use WebSearch to fill gaps: official statements and
documents, open reporting that follows up a paywalled scoop, and public reaction
(posts on X, Bluesky, Reddit or forums that search surfaces). Declare every page
you cite from web research in `web_refs`, with an id prefixed by your section
(`us-w1`, `nyc-w3`). Keep it to about a dozen fetches per section.

**Facts.** State only what you can attribute, in plain, neutral words: no
judging adjectives, no "slammed" or "blasted", no speculation. Attribute claims
("the White House said…") instead of stating them as fact. Prefer facts that
two or more independent outlets report. Several outlets reprinting the same AP
or Reuters story count once, so cite the wire. A single-outlet fact is fine
when it is that outlet's own reporting or a public record; the site labels it
"1 source". Never cite an opinion piece as a fact.

**Disputed.** Concrete contradictions: different numbers, causes or accounts of
who did what, each position with its refs. Differences in tone go in framing.

**Framing.** 2-4 ingested articles from different leans whose headlines frame
the story differently. The site shows the real headline, so the note says what
the wording emphasizes or plays down.

**Left out.** Only from outlets you read in full, and only material facts most
others reported. Short items leave things out; don't flag those. `missing_from`
lists source ids.

**Background.** 3-5 sentences for someone who hasn't followed the story at all:
what it is, how it got here, and who the key players are.

**Why it matters.** 1-2 sentences on what it means for an ordinary person (for
nyc, a New Yorker).

**Social.** 1-3 sentences on public reaction if you found any, clearly as
reaction rather than fact. Empty string if none.

**Coverage.** A note for every outlet you relied on, with a one-line takeaway on
how it covered the story.

**Copyright.** The site is public. Write in your own words. Quote at most a
short phrase (under 25 words), with attribution. Never paste article text.

## Section notes

- **us** (5-7 stories): federal government, Congress, courts, elections, national
  policy, major national events. `region` is a short tag like "Congress",
  "Courts", "White House", or "".
- **world** (6-8 stories): cover at least four of Middle East, Europe,
  Asia-Pacific, Africa and Americas when there's real news there. `region` is one
  of those or "Global".
- **business** (3-5 stories): what explains today's market moves and the economy:
  the Fed, jobs, inflation, trade, earnings that moved markets. `region` is a tag
  like "Fed", "Earnings", "Trade", or "".
- **nyc** (4-6 stories): City Hall and the mayor, City Council, Albany as it
  touches the city, the MTA and transit, housing and rent, schools, NYPD and
  public safety, courts, elections and ballot questions, development fights.
  Local outlets often cover a story alone, so single-outlet items in the digest
  are fair game. `region` is a borough or a tag like "City Hall", "Transit", or "".

## 3. Front page: `front.json`

Read `digest-front.md` and the section digests' top clusters.

- `overview`: 3-4 sentences on the day's most important developments across all
  sections.
- `markets.summary`: 3-5 plain-English sentences on what markets did and why,
  grounded in business stories. Explain any jargon in passing.
- `markets.movers`: 2-4 symbols from the front digest's quote table with the
  biggest or most telling moves, each with one sentence on why. If the cause is
  unclear, say so.
- `markets.concept`: one term from today's news explained for a beginner: what
  it is, what moves it, how it reaches your wallet. Don't repeat one from the
  last 14 days (`jq -r .markets.concept.term docs/data/briefs/*.json`).
- `markets.watch`: 2-5 events coming up this week with dates (Fed meetings, CPI,
  jobs report, big earnings, elections). Check the dates with WebSearch.
- `trending`: 4-8 items from the trend signals: what each is and why people are
  looking, in a sentence. `signal` is google, wikipedia, wikipedia_news, bluesky
  or web.

## 4. Build and publish

1. `python -m brief.build --date <date>`. It lists every problem at once (unknown
   refs, opinion pieces cited as facts, bad ids). Fix them in the file each one
   names and rerun until it prints `published`.
2. `python -m pytest -q` passes.
3. Commit `docs/data/` and `data/drafts/<date>/*.json` as `brief <date>` and push
   to main. GitHub Pages redeploys in a minute or two.
4. Report: story counts per section, and any failed feeds from the front digest
   that look permanent (a feed that has moved or died). Fix those in
   `config/sources.toml` on a branch, not in the brief commit.
