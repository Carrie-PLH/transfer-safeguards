# Writing the monthly change-record issue — Room & Recourse

The attended half of the change record. `MONTHLY-RECORD-PASS.md` is the
unattended half: on the 1st it triages last month's retention series into
`change-record/drafts/<YYYY-MM>.md` and stops (scheduled task
`rr-monthly-change-record`). This file is what a session with Carrie in it
does next, to turn that draft into the issue published at
https://roomandrecourse.com/changes/ (`site/changes.html`).

Written 2026-11-17 from how the September and October 2026 issues were
actually produced (commits `25a935b` for September, `b0e0ee3` for October,
`98d66c4` for the October draft's close-out), and modeled on Gathered Work's
`CHANGE-RECORD-ISSUE.md`. It replaces
`HANDOFF-change-record-2026-10-01.md`, which is completed and was specific to
the first issue.

This is never an unattended job. Writing an entry is a judgment about what a
change means to a reader (FA-D-20260831-09), and no scheduled pass may run
this file.

## What the issue is written from

Three sources, and the draft is the smallest of them here.

1. **The triage draft**, `change-record/drafts/<YYYY-MM>.md`. Each candidate
   carries the tool's evidence lines and a `TRIAGE:` reading. Below the
   candidates are four sections the pass leaves for a session (Corrections,
   Published and deepened, Still not published by the state, Where two of a
   state's documents disagree) and a Tooling notes section the tool fills
   itself.
2. **The pages' own change logs.** This is where almost everything in both
   published issues came from. The retention series here began on Aug 27, so
   most sources have had only a first or second capture and a change leaves
   nothing earlier to diff against. September's draft held one candidate
   (Texas, "no superseded capture recorded", triaged as a question about the
   series) and the September issue carries four state changes, fifteen
   corrections and the month's growth, all from change logs. October's draft
   held two (Nevada, again no earlier capture, and Indiana, already
   resolved); New York's rewritten page, Idaho's reissued chapter, Kansas's
   moved host and the three corrections were written from change logs. The
   issue says so itself: "Every other entry above was found by people
   re-capturing and checking pages."
   `QUEUE.md` (2026-10-01) records the same limit: `record-digest.py` cannot
   see corrections that predate the retention series.
3. **The retained captures**, `tools/packets/history/<slug>/`, and for a
   change the series cannot show, the standing packet and the supplement the
   change log names. Every quotation in the issue is read in the capture, in
   this session, before it is written.

## 1. Before writing

```bash
python3 ../field-assembly-standard/tools/portfolio-status.py
git status --short
ls change-record/drafts/
```

- Confirm the draft for the month exists and is committed. If the pass did
  not run or stopped on a failed self-test, run `MONTHLY-RECORD-PASS.md`'s
  sections 2 to 5 first; do not write an issue without a triaged draft.
- If the draft says the series is incomplete (a manifest named a capture not
  on disk), say so to Carrie before writing anything.
- Note anything already modified in the working tree and leave it alone.
- Texas's evidence includes a letter its host will not serve to the review's
  tools, and several supplements (Arkansas, Kansas) need a browser session.
  A change at one of them reaches the record only after an attended capture,
  so ask Carrie whether one was done this month.

## 2. Gather the month's change-log entries

Every page is rendered from its Markdown source (`states/<slug>.md`), and the
source is canonical (FA-D-20260905-02). Change-log entries open with
`YYYY-MM-DD — Title.` at the start of a line, in the source and on the page.

List what the pages recorded in the month, with the routine automated
entries filtered out:

```bash
M=2026-10   # the issue's month
grep -H -o -E "^$M-[0-9]{2} — [^.]{0,90}" states/*.md \
  | grep -v -E "Internet Archive captures|Baseline page built|Deepened from|Deepened to a full page|Page created|Languages row"
```

The title is cut at its first period, so a title with an abbreviation shows
short; read the entry itself. Read each remaining entry on its page. Entries
dated in the first days of the following month can belong to this issue when
they resolve a change the state made inside the month:

```bash
N=2026-11
grep -H -o -E "^$N-0[1-3] — [^.]{0,70}" states/*.md | grep -v "Internet Archive"
```

The date an entry is filed under in the issue is the date the source or the
capture carries, not the date the page was fixed. October's Indiana entry is
dated Oct 25 on the page and in the issue because that is the run that found
the fax line gone.

Also read the month's queue items, open and closed, since most real findings
have one. This collection's tag is `-rr-`:

```bash
Q=202610   # the issue's month as YYYYMM
ls ../field-assembly-standard/queue/open ../field-assembly-standard/queue/closed | grep -E "FA-Q-$Q.*-rr-"
```

## 3. Sort every item into one of the page's kinds

The page's opening promises that three kinds of fact are kept apart: a
state's own change, an error of ours, and a difference that came from this
project's tools with the state's document unchanged. Each item from the draft
and from step 2 goes to exactly one section. The headings below are the ones
the issues carry, in their order on the page.

| Section | What belongs there |
| --- | --- |
| What the states changed | A state reworded, moved or reissued a document a page quotes or links; a moved host (Kansas's statutes); a rewritten program page. TRIAGE `real revision`. Dated paragraphs, with a docket where wording moved. |
| Corrections to these pages | An error of this project's own, in a table (Page, What was wrong, What it says now), each row linking `/states/<slug>/#s-04` with its date. September's fifteen were grouped by cause where several pages shared one (five spacing corrections, one paragraph under the table). |
| Published and deepened | Pages added or deepened, and capture methods finished. September: 33 pages (2 full) to 51 (50 full). October: no pages added, three recipes finished, Texas's evidence rebuilt. |
| Still not published by the state | A document the state does not publish in quotable form, set out as its own entry (Hawaii's scanned rule, New Hampshire's unretrievable He-P 803 and He-E 802, Idaho's repealed grounds). October restated that the three stand and named what was added. Keep it: unlike the other collections, this one publishes the section. |
| Where a state's documents disagree | One paragraph per disagreement, both versions quoted, in a docket. September had eight. October left the section out; Gathered Work keeps an empty section with "None this month." Either is defensible, so say which you are doing to Carrie. |
| How closely this record watches | This collection's version of "what looked like a change and was not": what the comparison of each capture with the last flagged, how many of those were real, and any difference that came from this project's own tools reading an unchanged document. October's names the two flagged pages and closes the two capture defects September reported as open. |

A "no superseded capture recorded" candidate is not a finding on the draft's
evidence, and it is not cleared by it either. Read that slug's change log
for the month before dropping it: if the page recorded a state change, it is
written from the change log and the capture. If the page recorded nothing,
it is left out. Nevada's October candidate was a retention question; what the
page recorded was a correction, and that is what the issue carries.

A revision to text no page quotes or depends on is left out unless Carrie
wants it in. That is her call; put it to her with a recommendation rather
than deciding it. October's Idaho paragraph is the shape of one that stayed
in with its limits stated ("the parts the page quotes read word for word as
before").

An item still open at writing time is published only if Carrie says so. The
recommended order is to resolve it on the page first (re-capture, requote in
the Markdown, re-render, change-log entry, close the queue item) and then
write it as settled, which is what both issues so far have done. September's
two open capture defects, reported as open and closed in October, are the
precedent for stating one as open.

## 4. Verify before writing a word of quotation

For every "Was" and "Now":

- Open both captures the draft or the change log names and read the passage.
  Quote from the capture, not from the draft's TRIAGE line or the change
  log's paraphrase.
- Confirm the page already carries the current wording and a change-log
  entry for it. The issue links to that change log; it must not be the
  first place a change is recorded.
- Quotation rules are the site's: wording, spelling and sense-bearing
  punctuation exact; a state's own spaces and stray punctuation stay (the
  collection's five spacing corrections show what happens when a capture
  adds them); never restyle a source's spelling, including "licence".
- Date a docket row where the date is the point: `Was &middot; Sep 4`,
  `Now &middot; Oct 8`, or the revision label (`Rev. 23-1`).

## 5. Write the issue into site/changes.html

There is no generator, and `render-state.py` does not touch this page. Copy
the newest issue's `<section>` and rewrite it.

- **Placement:** the new `<section class="section section--raise"
  id="<YYYY-MM>">` goes directly above the previous month's, newest first.
- **Jump nav:** add `<a href="#<YYYY-MM>">Month YYYY</a>` as the first link
  in `<nav class="jump" aria-label="Issues">`.
- **Section label:** `<div class="section-no">YYYY-MM<small>Mon 1 to Mon 31,
  YYYY</small></div>`, then `<h2>Month YYYY</h2>`.
- **Opening paragraph:** two to five sentences that state what happened in
  the month in outline, name the states that changed documents, say how
  many pages were corrected for errors of this project's own, and say
  whether any page was added.
- **A changed quotation:** a `<p class="mw">` beginning
  `<strong>State &middot; Mon D.</strong>`, then `<dl class="docket">` with
  `Was` and `Now` rows, then a line ending with the link
  `<a href="/states/<slug>/#s-04">X's change log</a>.`
- **A move or a small change with nothing requoted:** one paragraph, no
  docket, same closing link.
- **Corrections:** one `<tr>` in the section's `claim-table`; where one cause
  covers several pages, one row may list them, each linked with its own date.
- **Empty sections stay**, reading "None this month." or "None recorded this
  month." (see the table for the one this collection has left out).
- **Closing line of the issue:** `<p class="mw muted small"
  style="margin-top:2.25rem;">Written from the pages' own change logs, each
  already reviewed on the date shown there. Reviewer: [pending review before
  publication]. Corrections on the record: <a
  href="mailto:hello@fieldassembly.net">hello@fieldassembly.net</a>.</p>`

What never goes on the page: the pass's report, a diff, a manifest line, a
similarity figure, a queue or decision ID, a recipe hash. The captures and
manifests stay outside `site/` under the tier boundary.

House rules that apply here as everywhere: American spelling outside
quotations, no advice or deadline calculations, no external requests, and
the footer (Reassembly credit, More from Field Assembly column, Accessibility
link) is left exactly as it is. `changes.html` has no "Reviewed" footer line
to update.

### The "Published and deepened" numbers

Count pages at the month's boundaries from git, so the figures match the
window the issue states:

```bash
count() { git ls-tree -r --name-only "$(git rev-list -1 --before="$1" main)" \
  | grep -E '^site/states/[^/]+\.html$' | grep -vc 'index.html'; }
count "2026-10-01 00:00"   # start of the month
count "2026-11-01 00:00"   # end of the month
for d in 2026-10-01 2026-11-01; do
  git show "$(git rev-list -1 --before="$d 00:00" main):STATUS.md" | grep -m1 'Full pages'
done
```

The first two give pages published and the third gives "Baseline N of 51 ·
Full pages N of 51" as `STATUS.md` stood at each boundary. Do not run
`tools/build-status.py` to refresh the file for this: it rewrites it.

### Checked against git, 2026-11-17

Both published issues were counted at the calendar boundaries, and the
figures match. There is no open point on counts for this repo.

- **September.** "Began with 33 state pages, two of them full, and ended
  with all 51, fifty of them full" matches the tree and `STATUS.md` at the
  Sep 1 commit (33 pages, 2 full) and the Oct 1 commit (51 pages, 50 full).
  "Eighteen states were published for the first time" is 51 minus 33, and
  "forty-eight pages were deepened" is 50 minus 2.
- **October.** "No pages added", "all 51 pages, fifty of them full" match the
  Oct 1 and Nov 1 commits (51 and 50 at both).

Other lines used so far, each optional and each from a named source: the
archive backlog (`python3 tools/spn.py status`; a growing backlog is
expected and is reported, not chased).

## 6. Carrie's review

Show Carrie the written issue. Nothing ships with the placeholder in place:
gate check 1 refuses any HTML file carrying it, and check 1b refuses any
variant of "review pending", so do not paraphrase the placeholder when
drafting. If the same session changed a state page, its reviewer line
follows the same rule.

When she says "I've reviewed" (portfolio rule, 2026-10-02), that is the
review. Then, and only then, replace the placeholder with
`Reviewer: Carrie Schluter (review confirmed YYYY-MM-DD).`, using the date
of her confirmation, as October's issue did. September's issue reads
"Reviewer: Carrie Schluter, reviewed 2026-10-01", a form from before the
dated standard was settled; leave it, and use the dated form for new issues.

Do not ask her to confirm again, and do not clear the placeholder on
anything short of that statement.

## 7. Commit

Stage paths, never the tree. `changes.html` is not a state page, so
`render-state.py`, `sync-checked-dates.py`, `build-state-picker.py` and
`anchor.py` are not part of this: the anchor covers the packets and tools,
not `site/` (`cat tools/anchor-paths.txt`). There is no feed here.

```bash
git status --short
git commit -m "Change record: <Month YYYY> issue (owner review YYYY-MM-DD)" -- site/changes.html
python3 tools/generate-sitemap.py
git commit -m "sitemap: regenerate after <Month> change record" -- site/sitemap.xml site/robots.txt site/_redirects
git push origin main
```

October's issue went in as one commit touching `site/changes.html` alone
(`b0e0ee3`). The sitemap commit comes after the content commit because
`lastmod` is the page's commit date. Commit only the files the generator
changed; `robots.txt` and `_redirects` often do not move.

If state pages were also changed in this session (a finding resolved in
step 3), they follow their own rules first: the dated entry in
`states/<slug>.md`, `python3 tools/render-state.py <slug>` (never edit the
page by hand), `python3 tools/sync-checked-dates.py` when the checked date
moved, the retention tool for any capture, and the fidelity check against
the page's computed evidence set. Then `python3 tools/build-status.py`
rewrites `STATUS.md`.

## 8. Deploy, only if Carrie asks in this session

```bash
grep -n -i "hold" QUEUE.md        # put any deploy hold to her first
bash deploy.sh
```

`deploy.sh` runs `site/predeploy-check.sh`, the security.txt check,
`npx wrangler deploy` from `site/`, the IndexNow ping and the ledger commit;
push that commit. This worker's deploy reports its trigger
(`roomandrecourse.com (custom domain)`) rather than "No targets deployed", as
`CLAUDE.md` records; either way, verify on the live site. Other pages
waiting on review block the whole deploy, so report them rather than working
around them.

```bash
curl -sSL https://roomandrecourse.com/changes/ | grep -c 'id="<YYYY-MM>"'
python3 tools/check-live.py --url https://roomandrecourse.com/changes/
```

## 9. Close out

- Report: what the issue says in one or two lines, the commits, whether it
  deployed, and anything left open.
- The pass leaves no other draft behind: the triage draft is its only output
  here. The draft's four lower sections are filled by a session after the
  issue is written, and committed by path (`git commit -m "change record:
  close out the <YYYY-MM> draft" -- change-record/drafts/<YYYY-MM>.md`), as
  `98d66c4` did for October.
- If writing the issue showed the triage tool misreading something, that is
  a queue item for a tooling session, not an edit to `record-digest.py`
  here.
