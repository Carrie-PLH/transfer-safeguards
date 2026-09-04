# Review log — Room & Recourse

Append-only. One entry per review pass. Three results are possible for a page:

- **confirmed** — every source re-fetched and the page still traces to its
  packet; the checked date advances.
- **drift** — a source changed in a way the page's own text depends on. Page
  content is never edited by the pass; the drift is flagged for an owner
  session through `rr-state-page`.
- **unreachable** — the publisher could not be fetched by any transport
  available to the pass. Not a finding about the law, only about the transport.

## 2026-09-03 — rotation initialized

`tools/review-cursor.txt` did not exist and had never existed: no entry for it
in git history, and the working tree was clean, so it was not lost but never
written. Four pages carry retention manifests (iowa and virginia on 2026-09-02,
florida and new-york on 2026-09-03). Those four are not contiguous in the
alphabetical rotation and came two to a night rather than three, so they were
owner-named reviews rather than rotation passes, and a named review does not
advance the cursor. Nothing about the rotation's position was lost, because the
rotation had not started.

Cursor initialized to `alabama`, the alphabetically first published slug, per
the rule in `rr-state-review`. The next pass takes alabama, california and
colorado.

No page content was touched and no checked date was changed by this entry.

## 2026-09-04 — recipe backfill: delaware and washington (Room & Recourse exception)

Scheduled pass (portfolio-nightly-qc-review). tools/recipes/ holds 4 recipes
against 45 published state pages, so the Room & Recourse exception in the
pass's own instructions applies: this repo's slot was spent writing capture
recipes rather than running a review lap, and the review cursor (`alabama`)
is untouched.

**Delaware — recipe written and verified.** Source 1 (16 Del. Admin. Code §
3102) is served as a PDF from a `/api/AdminCode/...` path that looks
JSON-shaped but returns a PDF directly to plain curl (200, no browser
user-agent). pdftotext -layout matches the standing packet's own extraction
(plain/default mode loses the section-number tabular indentation); the
standing packet strips this 5-page document's repeated letterhead more
thoroughly than strip-running-headers manages on a document this short,
which is a cosmetic difference in non-quoted boilerplate, not a fidelity
risk. Sources 2 and 3 (DHCQ contact page, Ombudsman Program page) both use
`.entry-content` as scope, narrower than the standing packet's own capture
(which included site nav and sidebar menus) and confirmed to hold every
contact fact the page quotes. All five verification steps passed: lint
clean, two consecutive captures byte-identical, zero failures against both
states/delaware.md and site/states/delaware.html. Retained as a rebuild
(hash e1fa5277c73f0d37) and promoted.

**Washington — recipe written and verified.** Sources 1 and 2 (RCW 74.42.450,
WAC 388-97-0120) share `#contentWrapper` as scope despite otherwise using
different top-level wrapper classes across the RCW and WAC templates on
app.leg.wa.gov -- narrower than the alternative container on the RCW
template, which pulls in prev/next navigation and a metadata row this page
does not quote. Source 3 (the Ombudsman Program home page) needs `body`:
the phone, fax, TTY number and street address this page quotes all sit in
the site's global footer, outside the page's own `<main>` element, so body
is the narrowest honestly-stated scope that holds everything, matching how
the standing packet itself was captured. All five verification steps
passed: lint clean, two consecutive captures byte-identical, zero failures
against both states/washington.md and site/states/washington.html. Retained
as a rebuild (hash abee18e246f0b712) and promoted.

Neither recipe required a browser transport or any filter beyond
strip-zero-width/trim-lines/collapse-blank-runs (Delaware's PDF source
additionally needs strip-page-numbers and strip-running-headers). Both
states' standing packets were built by hand before either recipe existed;
this pass's recipes reproduce what those packets already said, verified
against the live sources rather than assumed unchanged.

`check-all.py`: 88 pages across 45 states checked against their full
evidence sets, no unexplained failures. `build-status.py`: baseline 44/51,
full 2/51 (delaware and washington now on recipes with a passing check;
florida, iowa, new-york and virginia already had recipes from before this
pass but are not all counted as "full" — that tracker's own criteria, not
touched here).

No queue entries opened.

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-09-04.
