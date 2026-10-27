#!/usr/bin/env bash
# Copies a day's ingest bundle from the `ingest` branch to data/ingest/<date>.json.
# Usage: scripts/pull-ingest.sh [YYYY-MM-DD]   (defaults to today in New York)
set -euo pipefail

date="${1:-$(TZ=America/New_York date +%F)}"
root="$(git rev-parse --show-toplevel)"

git -C "$root" fetch -q origin ingest
mkdir -p "$root/data/ingest"
if ! git -C "$root" show "origin/ingest:${date}.json" > "$root/data/ingest/${date}.json"; then
  rm -f "$root/data/ingest/${date}.json"
  echo "No ingest bundle for ${date} on the ingest branch. Has today's ingest workflow run?" >&2
  echo "Bundles there: $(git -C "$root" ls-tree --name-only origin/ingest | tr '\n' ' ')" >&2
  exit 1
fi
echo "data/ingest/${date}.json"
