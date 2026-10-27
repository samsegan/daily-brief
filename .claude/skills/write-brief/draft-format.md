# Draft format

A day's draft lives in `data/drafts/<date>/`: `us.json`, `world.json`,
`business.json`, `nyc.json` and `front.json`. `brief.build` decodes them
strictly: every key below is required (use `""` or `[]` when there's nothing),
and unknown keys are errors.

The examples below show the shape only; their contents are made up.

Refs are article ids from the digest (the backticked 10-character ids) or ids
of `web_refs` declared in the same file.

## Section file (`us.json`, `world.json`, `business.json`, `nyc.json`)

```json
{
  "stories": [
    {
      "id": "senate-shutdown-vote",
      "headline": "Senate passes stopgap bill to end the shutdown",
      "region": "Congress",
      "importance": 5,
      "summary": "Two or three sentences: what happened, who did it, and what happens next.",
      "why_it_matters": "One or two sentences on what it means for an ordinary person.",
      "background": "Three to five sentences for someone who hasn't followed this at all.",
      "facts": [
        { "text": "The Senate passed the bill 52-48 on Monday night.", "refs": ["3f9a1c0b2d", "a81e4f6c90"] },
        { "text": "The White House said the president would sign it Tuesday.", "refs": ["us-w1"] }
      ],
      "disputed": [
        {
          "topic": "How many federal workers missed a paycheck",
          "positions": [
            { "claim": "About 800,000, per the Office of Personnel Management.", "refs": ["3f9a1c0b2d"] },
            { "claim": "Closer to 1.3 million counting contractors, per a union estimate.", "refs": ["c0d2e4f6a8"] }
          ]
        }
      ],
      "framing": [
        { "ref": "a81e4f6c90", "note": "Leads with the GOP holdouts who flipped." },
        { "ref": "c0d2e4f6a8", "note": "Leads with the cost to federal workers." }
      ],
      "left_out": [
        {
          "text": "The bill only funds the government through Dec. 19.",
          "refs": ["3f9a1c0b2d", "a81e4f6c90"],
          "missing_from": ["fox"]
        }
      ],
      "coverage": [
        { "ref": "3f9a1c0b2d", "takeaway": "Straight vote story with the tally and next steps.", "read_full": true },
        { "ref": "a81e4f6c90", "takeaway": "Headline and summary only (paywalled): focuses on the deal.", "read_full": false }
      ],
      "social": "On X and Bluesky, federal workers mostly asked when back pay will land."
    }
  ],
  "web_refs": [
    { "id": "us-w1", "url": "https://www.whitehouse.gov/...", "title": "Statement on the continuing resolution", "outlet": "White House" }
  ]
}
```

- `importance`: 1 (minor) to 5 (top story). Stories are shown highest first.
- `left_out[].missing_from`: source ids from `config/sources.toml` (`fox`, `nyt`, ...).
- `framing[].ref` must be an ingested article, not a web ref.

## Front file (`front.json`)

```json
{
  "overview": "Three or four sentences on the day's most important news.",
  "markets": {
    "summary": "Three to five plain-English sentences on what markets did and why.",
    "movers": [
      { "symbol": "^GSPC", "why": "Rose after the shutdown deal eased worries about missing economic data." }
    ],
    "concept": {
      "term": "Treasury yield",
      "explanation": "What it is, what moves it, and how it reaches your wallet, for a beginner."
    },
    "watch": ["Wed Oct 29: Federal Reserve rate decision", "Fri Oct 31: September jobs report"]
  },
  "trending": [
    { "title": "World Series Game 3", "context": "Why people are searching for it, in one sentence.", "signal": "google" }
  ]
}
```

- `movers[].symbol` must be a symbol in the front digest's quote table.
- `trending[].signal`: google, wikipedia, wikipedia_news, bluesky or web.
