#!/bin/bash
#
# deploy.sh — the one supported deploy command for this repo.
#
# Gate, publish, IndexNow ping, ledger commit, in that order. Written
# 2026-09-11 so the IndexNow step (FA-D-20260911-01) cannot be forgotten:
# asking for a deploy means running this file, not the commands it wraps.
# Deploy only when the owner asked in that session; the gate still decides
# whether anything ships. Runs on the Mac (bash 3.2 — no case-in-$( ), see
# CLAUDE.md), through Desktop Commander from a Cowork session.
set -euo pipefail
cd "$(dirname "$0")"

bash site/predeploy-check.sh

(cd site && npx wrangler deploy)

# IndexNow: submit what this deploy changed (FA-D-20260911-01). set -e means
# a ping failure after a successful publish stops here and is seen, not
# hidden; rerun the tool by hand after fixing.
python3 ../field-assembly-standard/tools/indexnow-ping.py

# Keep the ledger on the record with the pass that deployed. Commits only
# the ledger path, never the working tree.
if ! git diff --quiet -- tools/indexnow-ledger.json 2>/dev/null; then
  git commit -m "IndexNow ledger: record post-deploy submission" -- tools/indexnow-ledger.json
  echo "Ledger committed - push it with the session's other commits."
fi

echo ""
echo "Done. Site deployed and IndexNow notified."
