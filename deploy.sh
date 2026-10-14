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
#
# One ordering rule, which the gate reports but cannot do for you: the
# sitemap's lastmod for each page is that page's git commit date, so committing
# a page invalidates the sitemap by definition. Regenerate and commit the
# sitemap, robots.txt and _redirects after the content commits they describe,
# as the last commit before this script runs. Check 13 then passes; otherwise
# it fails and keeps failing until you do.
#
# Added 2026-10-14. Until that day the check compared the generated files to
# their own state before the run rather than to the committed copy, so a
# re-run cleared the failure and the ordering never had to be met — two sites
# were found deploying sitemaps a day or more behind their own pages.
set -euo pipefail
cd "$(dirname "$0")"

bash site/predeploy-check.sh

# security.txt must be RFC 9116-valid and not expiring (FA-D-20260911-05).
# Refuses when Expires is past or within 60 days; the fix is
#   python3 ../field-assembly-standard/tools/securitytxt-check.py --renew
# in every site repo, committed with the deploy.
python3 ../field-assembly-standard/tools/securitytxt-check.py

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
