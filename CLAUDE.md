# daily-brief

Personal daily news brief. See README.md for the pipeline.

- **Code changes** go on a branch cut from `origin/main`, in their own worktree,
  with `python -m pytest -q` passing before you push. Open a PR, then merge it
  yourself once tests pass.
- **The daily brief** is data, not code: the write-brief skill commits
  `docs/data/` and `data/drafts/<date>/` straight to main.
- The site is public. Never commit full article text; the ingest bundle holds
  only headlines, short feed summaries and links, and lives on the `ingest`
  branch.
- Keep `brief/` modules under 600 lines and functions under 150. Constants and
  enums live in `brief/config.py`; outlets and market instruments in `config/`.
