# Daily Brief

A personal morning news brief: for each of the day's main stories, what several
outlets agree on, where they disagree, how each side framed it, and what some
left out. It covers US, world, markets and New York City news. Every fact
links to the outlets that reported it.

**Site:** https://samsegan.github.io/daily-brief/

## How it works

```
GitHub Actions, 10:10 UTC daily (free)      Claude Code session (your Claude plan)
┌──────────────────────────────────┐         ┌─────────────────────────────────────┐
│ python -m brief.ingest           │         │ .claude/skills/write-brief          │
│  ~45 outlets' RSS feeds          │ ingest  │  digest → 4 section writers +       │
│  Yahoo Finance + FRED numbers    │ ──────► │  front page → python -m brief.build │
│  Google Trends, Wikipedia,       │ branch  │  (validates every ref) → push main  │
│  Bluesky trend signals           │         └──────────────────┬──────────────────┘
│  TF-IDF clustering into stories  │                            │
└──────────────────────────────────┘                  docs/ on GitHub Pages
```

1. **Ingest** (`brief/ingest.py`, `.github/workflows/ingest.yml`) fetches the
   outlets in `config/sources.toml` and the numbers in `config/markets.toml`,
   groups articles into candidate stories, and force-pushes one JSON bundle to
   the `ingest` branch. It stores headlines, short feed summaries and links,
   never full article text.
2. **Write**: a Claude Code session follows `.claude/skills/write-brief/SKILL.md`.
   It reads open articles in full and paywalled ones from their summary only,
   uses web search for gaps and public reaction, and writes drafts in
   `data/drafts/<date>/`.
3. **Build** (`brief/build.py`) checks every reference against the bundle,
   fills in outlet names, leans, URLs and market numbers from it, and writes
   `docs/data/briefs/<date>.json`. The static site in `docs/` renders it.

## Running it

```
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m brief.ingest                  # needs open internet; writes data/ingest/<date>.json
scripts/pull-ingest.sh                            # or fetch the Actions-made bundle instead
.venv/bin/python -m brief.digest --date 2026-10-27 --section us --summaries
.venv/bin/python -m brief.build --date 2026-10-27
python3 -m http.server -d docs 8000               # preview the site
```

## Skins

The gear menu switches between **Matrix** (default: a plain green-on-black
terminal with code rain behind the masthead), **Cold Steel** (the plug-ins' own
blue-black skin, with their textures) and **Paper**, and turns each skin's
effects on or off (code rain; scratches and wear). The choice is saved in the
browser. `docs/skin.js` applies it before paint; `docs/terminal.css` and
`docs/steel.css` draw the two dark skins.

## Editing sources

`config/sources.toml` lists each outlet with a rough lean and whether it's
paywalled. Feeds that fail or go stale show up in the bundle's `errors`
(and in `brief.digest --front`).
