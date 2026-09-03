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
