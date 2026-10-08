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

## 2026-09-05 — working session (tooling), Florida re-captured

Not a review pass. Two capture.py defects the nightly passes had correctly
declined to patch were fixed in a reviewed session (FA-Q-20260904-08,
FA-Q-20260905-01), and Florida was re-captured to exercise both.

**florida — confirmed, promoted.** Captured unattended for the first time:
source 5 (F.A.C. chapter 65-2, served by flrules.org only as a legacy binary
.doc) now runs through capture.py's own extractor, which sniffs the Composite
Document Format header and converts with textutil. The hand `--supply`
workaround recorded in the 2026-09-05 packet is retired, and the recipe's note
for that source was rewritten to say what the tool now does. Recipe digest
unchanged (63c0a1b05d45); notes are outside the digest.

check-fidelity: 0 failures on both states/florida.md and
site/states/florida.html against the fresh capture. Retained and promoted,
hash 6ff0c4db9f3d5b24.

The retention tool's short-packet guard fired on sources 3 and 4
(3145 -> 2986 and 13708 -> 13576 characters) and the loss is the extract_html
fix, not source movement: myflfamilies.com's template carries developer
comments as markup — "Header injected", "LEFT NAV COLUMN", "MOBILE HAMBURGER
BUTTON", "FIX: type=\"button\" + pass this for aria-expanded updates" — which
the old walk appended as document text because bs4's Comment is a
NavigableString subclass, plus a hidden cookie-classification block. Every
removed line was diffed before promoting. No quotation on the page rested on
any of it.

Worth recording for the next reader: the portfolio-wide grep for the two
residue shapes named in FA-Q-20260904-08 (Westlaw's "anchor(", cdph.ca.gov's
SharePoint labels) found nothing in any standing packet, and Florida was
carrying a third shape none of those markers would have caught. The grep was
not a clean bill of health; a re-capture is.

Reviewer: working session, 2026-09-05.

## 2026-09-08 — recipe backfill: georgia (oldest hand-captured state)

Working session, not a rotation pass; the review cursor was not touched.
Georgia was taken first because it is the oldest hand-captured state
(2026-08-30) and CLAUDE.md's backfill guidance starts with the oldest.

**The blocker in the handoff did not exist.** The task was framed as
"rules.sos.ga.gov returns HTTP 403 to curl, so the drafted recipe's `curl`
transport will not work — change it to `web_fetch`." That reproduces, but
only against a user-agent this project does not send. The host refuses a
Chrome user-agent below roughly version 127 and serves the full page to
everything else. Bisected: Chrome/110 and /120 → 403; Chrome/127 — which
is exactly the string `capture.py` pins for `"user_agent": "browser"` —
/128, /130, /135, /140, curl's own default UA, an unrecognised UA of `"x"`,
and no User-Agent header at all → 200 with all 122,226 bytes. Neither
`--http1.1` nor a full browser header set changes the outcome in either
direction, so this is not the HTTP/2 refusal recorded for apps.azsos.gov.
The 2026-08-30 note "returns HTTP 403 to curl" was true of the request that
was made and false of the host; no transport change was needed and none was
made. Both sources capture unattended by plain curl.

Worth generalising: a "403 to curl" in a 2026-08-30 capture note is a claim
about one header set, and CLAUDE.md's transport list carries several of them.
Bisect the user-agent — including *upward*, against a stale-browser WAF rule —
before reaching for an agent transport, alongside the existing advice to
bisect on `--http1.1`.

**georgia — rebuild, promoted.** Recipe digest 8ce6b626783f, hash
5a522ba5f3d3df33, two sources, both `curl` + `html-text` + `body`, no
filters. Lint clean; two consecutive captures byte-identical (and a third
after the notes were rewritten, confirming notes stay outside the digest and
outside the body hash); `check-fidelity` 0 failures against both
`states/georgia.md` and `site/states/georgia.html`, before and after
promotion. `check-all.py`: 102 pages across 52 states, no unexplained
failures.

**The recipe capture is a substantive superset of the hand capture, which is
the finding.** 11,246 words against 8,857 — the recipe *recovers* rule text
the standing packet never held. The session fetch tool rendered Subject
111-8-50's nested lists as markdown tables and silently dropped the
sub-items nested inside the table cells, so the 2026-08-30 packet is missing
the (a)/(b) and (1)/(2) material under at least sixteen subsections,
including 111-8-50-.11(2)(a) — the physician's determination "that failure
to transfer the resident will result in injury or illness to the resident or
others". The packet's character count nonetheless *falls* (86,962 → 69,616),
because the markdown pipe-and-dash scaffolding removed is bulkier than the
text recovered, which is why a size delta alone would have read this
backfill as a loss. Every differing span was diffed at word level, ignoring
table scaffolding, before promoting. The only material dropped is the fetch
tool's own preamble (title, URL, Content-Type, YAML front matter) and, in
source 2, the georgia.gov "The .gov means it's official" interstitial and
three chrome labels; one stray `xml version="1.0"` line from an inline SVG
declaration is gained. No published quotation or contact fact rested on any
of it.

This is a new argument for the backfill beyond reproducibility: a markdown
table renderer standing between a publisher and a packet can drop list
structure without warning, and the states captured that way on 2026-08-30 —
per their own capture notes — are the ones to re-read first.

One artifact recorded and deliberately not filtered: where this publisher
sets a code citation as a link immediately followed by an italic "et seq."
with no separating character, tag strip joins them ("O.C.G.A. § 50-13-1et
seq.", and two occurrences of "31-8-100et seq."). This is the link-boundary
class CLAUDE.md records for Nebraska, Ohio and North Dakota, inverted — the
publisher's markup has no space there, so the run-together is faithful and a
space would be our invention. Ten other "et seq." citations in the same
document carry the publisher's own space. No page quotes any of the three.

**Sibling check, per the handoff.** Idaho is not a 2026-08-30 state — its
packet is 2026-09-02 — and all three of its curl-captured hosts
(aging.idaho.gov, healthandwelfare.idaho.gov, oah.idaho.gov) answer 200 with
content today; its one agent-fetched source is a legislature.idaho.gov PDF,
not retested here. Kansas and Maryland are 2026-08-30, and neither is ready
to backfill:

- **Kansas — two blockers, one of them movement.** `www.ksrevisor.org`
  (source 1, K.S.A. 39-936) now 301-redirects to `ksrevisor.gov`; the
  redirect target serves the statute, but the publisher's domain has moved
  and that is a source-movement finding for an owner session, not something
  a recipe should paper over by following the redirect silently.
  `www.ombudsman.ks.gov` (source 3) returns 403 to *every* curl variant
  tried — no UA, the pinned browser UA, Chrome/140, curl's default, and
  `--http1.1` — so unlike Georgia this one is a real refusal and needs a
  browser or agent transport. The KAR PDF on sos.ks.gov (10.9 MB) fetches
  fine.
- **Maryland — one blocker, one movement.** `mgaleg.maryland.gov` (source 1)
  still returns only site chrome to curl: fetched and re-checked this pass,
  the 63,847-byte response contains zero occurrences of "19-345" or
  "involuntary", exactly as the 2026-08-30 note said, so the scripted-client
  blocker is unchanged and that source still needs an agent transport.
  Separately, `dsd.maryland.gov` (source 2, COMAR 10.07.09) now
  301-redirects to `regs.maryland.gov`, which serves the regulations —
  again publisher movement to be recorded before a recipe is written.

Both states' redirects were followed and confirmed to serve real content, so
neither is a dead link; both are recorded here as findings rather than
repaired, because a moved publisher is the owner's call through
`rr-state-page`, not a backfill session's.

No page content was touched and no checked date was changed by this entry.
No queue entries opened.

Reviewer: working session, 2026-09-08.

## 2026-09-10 — recipe backfill: michigan (Room & Recourse exception)

Scheduled pass (portfolio-nightly-qc-review). Before this pass, tools/recipes/
held 43 recipes against 51 published state pages (idaho, kansas, maryland,
massachusetts, michigan, minnesota, montana, new-hampshire and south-dakota
had none), so the Room & Recourse exception in the pass's own instructions
applies: this repo's slot was spent writing a capture recipe rather than
running a review lap. This repo has no separate review cursor of its own in
the rotation sense the sibling collections use (see CLAUDE.md); nothing else
here was touched.

**Michigan — recipe written and verified.** Both sources are PDFs published
directly by michigan.gov/lara (a form, LARA-BCHS-ITD-100, and a 2013
guidance memo reproducing the statute); neither touches legislature.mi.gov,
which the repo's CLAUDE.md already documents as unreachable (incomplete
certificate chain to curl, empty body to the session fetch tool) — the
standing packet's own PENDING note says the Legislature's text was never
reached and the department's reproduction in source 2 is what the page
rests on, so this recipe does not change what is or is not captured, only
whether the existing sources can be re-fetched automatically. Both retrieved
by curl with a browser user-agent and extracted with pdftotext -layout,
matching the 2026-08-30 hand capture's own recorded method exactly.
Deliberately no strip-page-numbers filter: source 1's per-page footer
("LARA-BCHS-ITD-100 (07/26/2024)", "Authority: P.A. 368 of 1978 as
amended", "Page N of 7") is the form's own printed text per the standing
packet's capture notes, not a page-number artifact, and stripping it would
silently narrow what the packet holds. No slice on either source; both are
captured whole, as the standing packet already does. All five verification
steps passed: lint clean (digest 2605acca1508), two consecutive captures
byte-identical, zero failures against both states/michigan.md and
site/states/michigan.html. Retained as a rebuild (hash fe4a0985d72a3568) and
promoted. The state's checked date was left untouched — this pass backfilled
the recipe, it did not re-verify or re-date the page, which is the sibling
collections' own distinction between a recipe-backfill pass and a review
pass.

A second recipe was not attempted this pass. Idaho was the next candidate by
the same "oldest hand-captured, most drift-risk" reasoning the sibling
collections use, but its standing packet (2026-09-02) merges six separate
per-section statute pages under one SOURCE number and excerpts a single
853,225-byte PDF chapter as four non-contiguous spans chosen editorially
(cover page, general provisions, one definition subsection, and the Nursing
Facilities sub-area) — materially more complex than a source-per-URL,
whole-or-sliced recipe, and a rushed attempt risks writing a recipe that
enters nightly rotation reading the wrong content. Stopping after one recipe
for cause, per the pass's own instructions. Kansas, Maryland, Minnesota and
Montana are plausible next candidates (single-source-per-URL, no known
browser-only transport, per this repo's own CLAUDE.md transport notes);
Massachusetts and New Hampshire are documented as needing a browser
transport (mass.gov, dhhs.nh.gov) and South Dakota's core sources come from
a JSON API whose extracted "Html" field this repo's capture.py has no
extractor for (only pdftotext-*, html-text, next-data, docx and none are
implemented) — writing one would be a tooling change, which an unattended
pass may not make.

No queue entries opened.

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-09-10.

## 2026-09-17 — rotation pass: alabama, alaska, arizona (all confirmed)

Run to close the gap the portfolio QC backstop reported for this collection: the
2026-09-17 nightly pass covered sped-safeguards, gathered work and licensure
mobility and did not reach transfer-safeguards, whose last entry here was
2026-09-10. Recipe backfill was not attempted; the three states still without
recipes already carry their blockers in the portfolio queue (FA-Q-20260917-04
for massachusetts, FA-Q-20260917-03 for south-dakota, which also records the
new-hampshire transport refusal), and re-reporting them would have duplicated
entries opened the same day. The rotation was taken instead, from the cursor at
alabama.

**The alabama drift that prompted this pass was not drift.** The backstop report
recorded twenty-plus quotation failures against the standing packet and read
them as movement since capture. They reproduce exactly when `check-fidelity.py`
is given the main packet alone — forty-six failures, every one of them a
quotation from the CMS transfer and discharge rule plus the
`admincode.legislature.state.al.us` hostname — and they vanish when
`alabama-packet-rule.txt` and `alabama-packet-complaints.txt` are passed with
it. This page depends on two supplements and is the only page in this
rotation that does; the report also dated the baseline to 2026-08-30 where the
standing packet read `ASSEMBLED: 2026-09-16`. Nothing had moved. This is the
false-drift case the reviewer skill warns about, and it cost a page its checked
date for a week.

Captures were taken with `tools/capture.py` from each state's recipe on the host
carrying the pinned poppler 26.07.0. The sandbox shell available to an
unattended session carries poppler 22.02.0 and `capture.py` correctly refuses
PDF extraction under it, so any pass that touches a PDF-sourced packet has to
run on the pinned host — alabama source 1, alaska source 5 and arizona sources 1
and 2 are all PDFs, so all three states in this rotation are affected.

Results. alabama confirmed, hash 6f01a0d2a3b1603e, 2 sources, recipe
8736087ebf91. alaska confirmed, hash 07e3ac276d05bdec, 8 sources, recipe
bd40de4590dd. arizona confirmed, hash dbff48a8feff9d3c, 4 sources, recipe
ac7e57b789e8. All six surfaces — three `states/<slug>.md` and three
`site/states/<slug>.html` — returned zero failures against the fresh captures,
and returned zero again after the checked dates were advanced and the pages
re-derived through `render-state.py` and `sync-checked-dates.py`.

Source headers moved only in their retrieval dates. No URL redirected, no source
stated a new date, and nothing in this rotation looks like replacement rather
than revision: arizona source 1 still reads Supp. 26-1, March 31, 2026 with its
Historical Note recording the October 1, 2019 amendment, and alaska source 5
still reads Revised 2/1/2025. No `superseded` entry is warranted.

One finding worth recording. `retain-packet.py` flagged alabama source 2 as
carrying less text than the previous capture, 5,416 characters down to 4,848.
The difference is markup residue — `div`, `section` and `button` fragments that
leaked into the 2026-09-04 capture of the Filing Complaints page and are now
dropped before extraction — and not a word of published content. It is the
extractor change made under FA-Q-20260904-08, which is closed. The recipe digest
did not move across it, because the digest covers the recipe file and not the
extractor build; DECISIONS.md already treats that class of change as
digest-inert and settled, so this is recorded here rather than raised again.

Cursor advanced from alabama to arkansas. No queue entries opened or bumped.

Reviewer: session pass recovering the 2026-09-17 portfolio QC gap.

## 2026-09-22 — recipe backfill attempted: massachusetts, new-hampshire (Room & Recourse exception, scheduled)

Scheduled pass (portfolio-nightly-qc-review). 51 published state pages
against 49 recipe files (48 states plus texas-moved), so the Room & Recourse
exception applies: this repo's slot was spent on recipe construction rather
than a review lap. States without a recipe: massachusetts, new-hampshire,
south-dakota. Up to two attempted, per the exception's cap.

**Massachusetts — not written.** All three standing-packet sources are on
mass.gov, which returns HTTP 403 to curl (plain and browser user-agent),
reconfirmed today. This matches the repo's own prior finding
(FA-Q-20260917-04, first opened 2026-09-17): the WebFetch session reader also
fails, and the two PDF-derived supplement sources cannot be reliably
extracted through any transport this pass may use unattended. Bumped
FA-Q-20260917-04 rather than repeating the full investigation. No recipe
file was written or retained; states/massachusetts.md untouched.

**New Hampshire — not written.** Sources 1-3 (gc.nh.gov RSA text, curl) and
the three dhhs.nh.gov sources 4-6 (needing chrome transport, per
FA-Q-20260919-02's still-open extraction-adjacency question) tested as
expected. Sources 7-9 — three excerpts of one PDF at nhmmis.nh.gov — were
recorded capturable via curl as of FA-Q-20260919-02 (2026-09-19); today the
same URL returns an Incapsula bot-mitigation challenge page instead of the
PDF, confirmed with and without a persisted cookie jar. This is a new
regression, not the previously-logged span-adjacency problem, and is
recorded separately as FA-Q-20260922-01. A recipe naming fewer sources than
the standing packet would be a different packet wearing the old one's name,
so nothing was written; states/new-hampshire.md untouched.

South Dakota was not attempted this pass (already covered by
FA-Q-20260917-03 and FA-Q-20260919-01, the JSON-API extractor gap).

No published page changed. Review cursor untouched. Queue: bumped
FA-Q-20260917-04 (occurrence 2); opened FA-Q-20260922-01.

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-09-22.

## 2026-09-24 — rotation pass: arkansas, california, colorado (all confirmed, scheduled)

Room & Recourse recipe exception checked first, per the nightly routine: 51
state pages, 51 recipe files present with no gaps (verified per-slug, not by
count alone) — every page already has a recipe, so the exception is
permanently satisfied and this collection received normal QC review this
pass.

Cursor read at arkansas; batch was arkansas, california, colorado (next two
alphabetically).

- arkansas: CONFIRMED. Retained (promoted), hash 27b3b461cec13246, 4
  sources. Evidence set included both supplements
  (arkansas-packet-dhs.txt, arkansas-packet-medicaid.txt). Zero fidelity
  failures, md + html. Checked date -> 2026-09-24.
- california: CONFIRMED. Retained (promoted), hash d31e53886792b6d4, 9
  sources. Source 2 (dhcs.ca.gov, OAHA Transfer Discharge and Refusal to
  Readmit Unit) returned an Incapsula bot-mitigation challenge page to
  curl+browser-UA (200, 948 bytes, no `<main>` element) rather than the
  document; a documented alternate transport, the built-in browser, reached
  the real page (rendered `<main>`, matching the standing packet's content)
  and was supplied to capture.py with `--supply 2=<path>`. Source 7 (22 CCR
  72519, govt.westlaw.com) timed out on the first attempt and succeeded on
  an immediate retry — recorded as a transient timeout, not a transport
  block. Both fidelity checks (md + html) passed with 0 failures against
  the resulting 9-source capture. Checked date -> 2026-09-24.
- colorado: CONFIRMED. Unchanged since 2026-09-19 capture (byte-identical),
  hash 5df7e0e75286512c. Zero fidelity failures, md + html. Checked date ->
  2026-09-24.

Source headers moved only in retrieval dates on all three pages; nothing
reads as instrument replacement. No `superseded` entry warranted.

Cursor advanced: arkansas -> connecticut. No queue entries opened or
bumped for this collection.

sync-checked-dates.py: 6 derived dates corrected (table + json, 3 states).
build-status.py: baseline 51/51, full 38/51, es 0/51.

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-09-24.

## 2026-09-25 — owner review recorded: idaho, north-dakota, south-dakota

Carrie Schluter reviewed the three pages deepened to full pages on 2026-09-25
and confirmed them for publication. Each page's change-log reviewer line
moved from "Reviewer: Carrie Schluter (review pending for this entry)." to
"Reviewer: Carrie Schluter, reviewed 2026-09-25." in the working markdown,
re-rendered through render-state.py. No page content, quotation, docket row,
source map, packet, or checked date was altered. check-all.py afterward: 102
pages across 52 states, no unexplained failures. build-status.py: baseline
51/51, full 44/51. Sitemap lastmod refreshed by the predeploy gate.

Reviewer: owner, attended session, 2026-09-25.

## 2026-09-25 — dead-link repair: nevada, virginia, utah (attended, owner-named)

Three pages were reported with dead official-source links (404 to a cloud
crawler and to curl on the Mac). Named pages, not a rotation pass; the cursor
was not read or advanced.

Root cause for nevada and virginia was ours, not the publishers':
tools/render-state.py's markdown-link pattern ends a URL at its first ')', so
a source address containing parentheses published truncated
('...Brochure(2', '...(Nursing%20Facilities') and 404'd. The markdown held the
correct addresses throughout. Renderer not changed in this pass (it would
re-render california, whose five westlaw.com links carry the same defect);
flagged for the owner.

- virginia: CONFIRMED. All four sources recaptured through the recipe
  (c974353f8613); retained and promoted, hash 009508ab6c25a644. Source 4 (the
  DMAS Nursing Home Manual chapter behind the dead link) is byte-identical in
  extraction to 2026-09-15 and serves 200 at its unchanged address. Source 1
  lost only the law.lis.virginia.gov site footer (24713 -> 24426 chars), no
  statutory text. Zero failures md + html. Source-map link re-encoded with
  %28/%29; checked date -> 2026-09-25; change-log correction entry added,
  reviewer line pending.
- nevada: source 9 only (the ombudsman discharge brochure). Besides the
  truncation, ADSD moved the file: the old address 301s to
  /siteassets/content/programs/seniors/ltcombudsman/LTC_Discharges_Brochure_2.pdf.
  Captured there through a new supplement recipe
  (tools/recipes/nevada-moved.json, 121c322ec6d0) into
  tools/packets/nevada-packet-moved.txt, following the texas-moved precedent.
  Text unchanged; tripwire run: the page checked against sources 1-8 alone
  fails 12 spans (5 quotes, 3 phones, 4 addresses), and with the supplement
  added passes at zero. Source map relinked; checked date unchanged (the main
  packet was not re-fetched); change-log correction entry added, reviewer
  line pending. The main recipe remains an unpromoted draft.
- utah: NO CHANGE. Not dead. adminrules.utah.gov's rule addresses 404 with
  an empty body only to clients that do not send `Accept: text/html`; with a
  browser's Accept header they return 200 with the application shell, which
  loads the rule from the public API (reachable; not rendered in a browser in
  this pass). The rule-metadata API's own `linkToRule` field gives exactly the
  addresses the page links. The three version witnesses still carry the
  pinned GUIDs, so no rule was amended. Recorded 2026-09-04 in the page's own
  change log as a false dead-link report; this is the same false positive.

California, same session: the renderer fix (tools/render-state.py accepts one
level of parentheses in an address) repairs the five govt.westlaw.com links
that had the same fault; the page was re-rendered and carries its own dated
correction entry. No source was re-captured.

Reviewer: attended session, 2026-09-25; the three correction entries were
reviewed by Carrie Schluter on 2026-09-25.

## 2026-09-26 — rotation pass: connecticut, delaware, district-of-columbia (all confirmed)

Cursor was at connecticut. Took connecticut, delaware, district-of-columbia
(all have recipes, no supplements).

**Connecticut — confirmed.** Recipe capture (digest 5f9a18903066), 4 sources.
Zero failures on both pages. Retained — unchanged since 2026-09-17.txt (hash
71b82a37828a13ea). Promoted. Checked date -> 2026-09-26.

**Delaware — confirmed.** Recipe capture (digest b4683a863dc0), 3 sources.
Zero failures on both pages. Retained — unchanged since 2026-09-04.txt (hash
e1fa5277c73f0d37). Promoted. Checked date -> 2026-09-26.

**District of Columbia — confirmed.** Recipe capture (digest f6b61c9f4ef7),
12 sources. Zero failures on both pages. Retained (hash 1420837cda707789),
no size or header movement flagged. Promoted. Checked date -> 2026-09-26.

Cursor advanced to federal.

No queue entries opened. build-status.py: baseline 51/51, full 44/51 (the
existing backfill gap, unaffected by this pass). check-all.py: 102 pages
across 52 states, no unexplained failures. site/predeploy-check.sh: passed
after a stale-state-picker self-heal (index.html and states/index.html
regenerated). check-live.py: 5 pages sampled, nothing loaded from any other
host.

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-09-26. No human
review is claimed for this entry.

## 2026-09-27 — rotation pass: federal, florida, georgia (all confirmed)

Cursor was at federal. Took federal, florida, georgia, wrapping the "federal"
slot into the alphabetical rotation between district-of-columbia and florida.
None have supplements except federal (federal-packet-scope.txt).

**Federal — confirmed.** No `tools/recipes/federal.json` exists, so both the
main packet (eCFR 42 CFR 483.15, eCFR 42 CFR 431 subpart E, CMS SOM Appendix PP
tags F622-F628) and the scope supplement (eCFR 42 CFR 483.1) were re-fetched by
hand, matching the standing capture notes' transport: eCFR versioner API
(title-42 XML, pinned to 2026-08-13, confirmed via
`/api/versioner/v1/titles.json` as the title's current `latest_issue_date`),
tag-stripped mechanically; CMS PDF re-fetched from the same URL, ModDate
unchanged (2025-07-30 EDT) and Rev. 232 line unchanged, confirmed identical
over tags F622-F628 by pdftotext -layout. Zero failures, both packets, on
federal.md and site/federal.html. Retained (main hash 73fffc9a957fc670, scope
hash 70f941c5432eb1c8) — first retention entries for this slug; no
`tools/packets/history/federal/` existed before this pass. Promoted both.
Checked date -> 2026-09-27.

**Florida — confirmed.** Recipe capture (digest 63c0a1b05d45), 6 sources.
Zero failures on both pages. Retained (hash 32478d63382b6a76). Promoted.
Checked date -> 2026-09-27.

**Georgia — confirmed.** Recipe capture (digest 45c47b529b1d), 4 sources.
Zero failures on both pages. Retained (hash f06919da727cc738). Promoted.
Source 3 (the department's HFRD Laws & Regulations page) lost 54 characters
against the 2026-09-14 capture: one list item, "Drug Abuse Treatment and
Education Programs, Chapter 111-8-19," was removed from the department's own
regulation list. Unrelated to the contact/appeal-routing text this page
quotes from that source; nothing the page states traces to the removed line.
Confirmed rather than drift.

Cursor advanced to hawaii.

No queue entries opened. build-status.py: baseline 51/51, full 47/51.
check-all.py: 102 pages across 52 states, no unexplained failures.
site/predeploy-check.sh: three pre-existing FAILs unrelated to this pass —
montana, vermont and delaware still carry an unresolved review-pending status
(not touched by this pass); the state picker and sitemap generators reported
stale output and were re-run (see below). check-live.py: pending, see report.

The state picker (site/index.html, site/states/index.html) was regenerated by
this pass's own date sync and is included in this pass's commit. The sitemap
(site/sitemap.xml) additionally carried a stale lastmod for montana and
vermont — dated 2026-09-25 where their own last commit is 2026-09-26 — left
over from a prior pass that did not re-run the generator after committing;
that is not this pass's change and is committed separately, after this pass's
own content, so the two are not attributed to the same cause. Reported rather
than silently absorbed.

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-09-27. No human
review is claimed for this entry.

## 2026-09-27 — owner review recorded: alaska, delaware, district-of-columbia, montana, vermont, wyoming

Carrie Schluter reviewed the six pages deepened to full pages on 2026-09-26
(delaware, montana, vermont) and 2026-09-27 (alaska, district-of-columbia,
wyoming) and confirmed them for publication. Each page's change-log reviewer
line moved from "Reviewer: Carrie Schluter (review pending for this entry)."
to "Reviewer: Carrie Schluter, reviewed 2026-09-27." in the working markdown,
re-rendered through render-state.py. No page content, quotation, docket row,
source map, packet, or checked date was altered. Sitemap lastmod refreshed
by generate-sitemap.py.

Reviewer: owner, attended session, 2026-09-27.

## 2026-09-29 — rotation pass: hawaii, idaho, illinois, indiana, iowa (all confirmed)

Cursor was at hawaii. Took hawaii, idaho, illinois, indiana, iowa (all have
recipes, no supplements).

**Hawaii — confirmed.** Recipe capture (digest 637d9ea53696), 5 sources.
Zero failures on both pages. Retained (hash 4871fc306be27ede). Promoted.
Checked date -> 2026-09-29.

**Idaho — confirmed.** Recipe capture (digest e26e6d38077c), 7 sources.
Source 2 (the six Idaho Code sections, fetched as a `urls` list) failed its
first attempt with "curl: (56) Recv failure: Connection reset by peer"; a
second attempt on the same transport succeeded — a transient network
failure, not a source or recipe problem. Zero failures on both pages.
Retained — unchanged since 2026-09-22.txt (hash 5517b2d203cffff0). Promoted.
Checked date -> 2026-09-29.

**Illinois — confirmed.** Recipe capture (digest 28f20d3e7dc5), 3 sources.
Zero failures on both pages. Retained — unchanged since 2026-09-06.txt (hash
4e2390b7ef60d815). Promoted. Checked date -> 2026-09-29.

**Indiana — confirmed.** Recipe capture (digest 00175a9654b0), 5 sources.
Source 4 read 206 chars shorter than the prior capture (whitespace
collapsed; fetch differed too). Zero failures on both pages — recorded as
retained textual movement, not drift. Retained (hash 72d4adf139a271c8).
Promoted. Checked date -> 2026-09-29.

**Iowa — confirmed.** Recipe capture (digest db5675492fce), 3 sources. Zero
failures on both pages. Retained (hash ce5d7559ef7c4671). Promoted. Checked
date -> 2026-09-29.

Cursor advanced to kansas.

No queue entries opened. build-status.py: baseline 51/51, full 50/51 (the
existing Hawaii backfill gap — its operative rule is a scanned PDF with no
text layer, recorded "Not quotable from the sources reviewed" by owner
decision 2026-09-04; unaffected by this pass). check-all.py: 102 pages
across 52 states, no unexplained failures. site/predeploy-check.sh: all
checks passed. check-live.py: 5 pages sampled, nothing loaded from any other
host.

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-09-29. No human
review is claimed for this entry.

## 2026-10-01 — nightly review: kansas, kentucky, louisiana (scheduled)

Cursor at kansas. Selected kansas, kentucky, louisiana (next two
alphabetically).

- kansas: RECIPE BACKFILL REQUIRED, not reviewed. tools/recipes/kansas.json
  is a DRAFT recipe (every source note reads "DRAFT — replace before
  promoting"), never verified or promoted — no packet history exists for
  this state. Captured anyway to check current reachability: 2 of 3 sources
  returned content; SOURCE 3 (ombudsman.ks.gov/helpful-resources/
  issues-of-interest/involuntary-discharge) returned HTTP 403, consistent
  with the 2026-09-08 working session's finding that this host refuses every
  curl variant tried (no UA, pinned browser UA, Chrome/140, curl default,
  --http1.1) and needs a browser or agent transport. Fidelity was not run
  against an unverified DRAFT recipe. No page content touched, no checked
  date changed. This is recipe-backfill work (`lm-recipe-backfill`-style),
  out of scope for this review pass; a working session should finish and
  verify the recipe (including a working transport for source 3) before
  kansas re-enters ordinary rotation review.
- kentucky: CONFIRMED. Recipe capture (digest 7e78656624fa), 3 sources, no
  supplements. Zero failures on both pages. Retained (hash
  501579dcf548fa4b), promoted. Retention tool flagged all three sources as
  shorter than the previous capture (18364->18229, 10383->10168,
  6475->5889 chars, whitespace collapsed); fidelity still passed with zero
  failures on the fresh text, recorded as retained textual movement that did
  not move any published fact, not independently re-analyzed. Checked date
  -> 2026-10-01 (md canonical, re-rendered, synced to table and JSON).
- louisiana: UNREACHABLE. Recipe capture, 2 of 3 sources. SOURCE 3
  (adminlaw.la.gov/areas-of-law/health.html) returned HTTP 403 to the
  documented transport (curl with browser user-agent); no alternate
  transport is documented for this source. No capture retained (incomplete
  evidence), checked date untouched. First pass through this skill for
  louisiana (prior packet history is from working-session rebuilds on
  2026-09-04 and 2026-09-15, not an automated review pass). Not queued (one
  unreachable pass).

Cursor advanced: kansas -> maine (past louisiana, the third selected unit).

sync-checked-dates.py: 2 derived dates corrected (table + json, kentucky).
build-status.py: baseline 51/51, full 50/51 (pre-existing Hawaii backfill
gap, unaffected). build-state-picker.py: 51/51 regenerated. check-all.py:
102 pages across 52 states, no unexplained failures. site/predeploy-check.sh:
ALL CHECKS PASSED. check-live.py: 5 pages sampled, nothing loaded from any
other host.

Not actioned this pass: the Field Assembly portfolio footer-credit line
("Built by Reassembly") is not present on this site's pages, and
roomandrecourse.com is not yet on the portfolio CLAUDE.md's "Done" list.
Same gap found this pass in sped-safeguards and licensure mobility; see the
portfolio-level report for the consolidated finding.

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-10-01. No human
review is claimed for this entry.

## 2026-10-03 — rotation: maine, maryland, massachusetts

Cursor read as `maine`. Took maine, maryland and massachusetts (the next two,
alphabetically, wrapping not needed).

- maine: NOT REVIEWED — tooling defect, not a source finding. `tools/.venv/bin/python
  tools/capture.py maine` failed both docx sources (`SOURCE 1 failed: No module
  named 'docx'`, `SOURCE 2 failed: No module named 'docx'`). The recipe's "docx"
  extractor for sources 1-2 is correct (confirmed by the 2026-09-01 capture notes
  and the 2026-09-24 recipe fix); python-docx is simply not installed in this
  repo's tools/.venv. Confirmed the same gap in licensure mobility's venv and
  confirmed python-docx IS present in sped-safeguards's and gathered work's. No
  capture attempted beyond the failed run, no page content touched, no checked
  date changed. Per FA-D-20260831-09 this pass does not install the missing
  dependency; tooling entry FA-Q-20261003-01 opened in field-assembly-standard
  (slug capture-py, kind tooling) naming the fix for a working session.
- maryland: CONFIRMED. Recipe capture (digest 094cd75387b1), 6 sources, no
  supplements. Zero failures on both pages. Retained (hash 9dc8dd474e6f7a55),
  promoted — the retained hash differs from the 2026-09-13 rebuild because the
  fresh #StatuteText scope still carries the Previous/Next pager text the
  2026-09-13 capture's notes already describe as a superset of the quoted text;
  no quoted fact moved. Header fields (statute and regulation administrative
  history dates) unchanged — only the retrieval date differs — so this is
  revision-class, not a replacement signal. Checked date -> 2026-10-03 (md
  canonical, re-rendered, synced to table and JSON).
- massachusetts: CONFIRMED. Recipe capture (digest f2c8a6194960), 3 sources,
  checked with supplements tools/packets/massachusetts-packet-bedhold.txt and
  tools/packets/massachusetts-packet-regs.txt. Captured 35 seconds after the
  maryland capture, respecting mass.gov's documented burst-403 window. Zero
  failures on both pages. Retained (hash 196acf359f155271), promoted. Source
  dates (LTC-013 Rev. 01/01; no stated date on sources 2-3) unchanged — only the
  retrieval date differs, revision-class, not replacement. Checked date ->
  2026-10-03 (md canonical, re-rendered, synced to table and JSON).

Cursor advanced: maine -> michigan (past massachusetts, the third selected
unit).

sync-checked-dates.py: 4 derived dates corrected (table + json, maryland and
massachusetts). build-status.py: baseline 51/51, full 50/51 (pre-existing
Hawaii backfill gap, unaffected). site/predeploy-check.sh: first run FAILed on
a stale state picker (regenerated by the gate itself, the designed
one-failure-then-pass shape for check 11); second run ALL CHECKS PASSED.
check-live.py: 5 pages sampled, nothing loaded from any other host.

Correction to this entry (same pass, caught before closing the portfolio
report): the line below was carried forward from the 2026-10-01 entry without
re-checking it, and it is wrong. The predeploy gate (`ok footer credit on all
59 pages`) and a direct grep of site/states/maryland.html and site/federal.html
both confirm the "Built by Reassembly" line is present, and roomandrecourse.com
is in fact on the portfolio CLAUDE.md's "Done" list (dated 2026-10-01). Struck
through rather than deleted, so the mistake is visible rather than silently
corrected: ~~Not actioned this pass: the portfolio footer-credit line ("Built
by Reassembly") is still absent from this site and roomandrecourse.com is
still not on the portfolio CLAUDE.md's "Done" list — same gap recorded
2026-10-01; see the portfolio-level report.~~

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-10-03. No human
review is claimed for this entry.

2026-10-04 — nightly review (portfolio-nightly-qc-review). Cursor was
`michigan`; batch michigan, minnesota, mississippi. Recipe-exception check run
first: 55 recipes against 52 state pages, so every page already has one;
reviewed normally.

- michigan: CONFIRMED. Recipe 508f3660fd67, 4 sources, 0 failures md + html.
  Retained unchanged since 2026-09-13 (hash bb9c7d582cde5789), promoted.
  Checked date -> 2026-10-04.
- minnesota: CONFIRMED. Recipe 58989314ea0a, 6 sources, 0 failures md + html.
  Source 3 (mn.gov/ooltc/, behind Radware/ShieldSquare bot management per the
  recipe's own notes) returned capture.py exit 3 on plain curl; fetched
  through the Claude Browser pane as the recipe notes prescribe (no
  interstitial), saved, and supplied with `--supply 3=`. Retained a changed
  body (hash f44aadc6e1181510), promoted; no source-header movement. Checked
  date -> 2026-10-04.
- mississippi: CONFIRMED. Recipe ca85686f9a9a, 7 sources, 0 failures md +
  html. Retained unchanged since 2026-09-21-b (hash 67519e8b2595adc4),
  promoted. Checked date -> 2026-10-04.

Cursor advanced michigan -> missouri (past mississippi, the third selected
unit).

sync-checked-dates.py: 6 derived dates corrected (table + json, michigan,
minnesota, mississippi). build-status.py: baseline 51/51, full 50/51
(pre-existing Hawaii backfill gap, unaffected). check-all.py: 102 pages / 52
states, no unexplained failures. retain-packet.py --verify: 0 failures across
102 entries. generate-sitemap.py: 57 URLs (texas excluded, pre-existing
recorded drift, unaffected by this pass). check-live.py: 5 pages sampled,
nothing loaded from any other host. No deploy.

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-10-04. No human
review is claimed for this entry.

2026-10-06 — nightly review (portfolio-nightly-qc-review). Cursor was
`missouri`; batch missouri, montana, nebraska, nevada, new-hampshire.
Recipe-exception check run first: 55 recipes against 52 state pages, so
every page already has one; reviewed normally.

- missouri: CONFIRMED. Recipe 9d0acc95d4b4, 3 sources, 0 failures md + html.
  Retained (hash 2b6f8901aad9ddaa; source 2 somewhat shorter, whitespace-
  collapsed), promoted. Checked date -> 2026-10-06.
- montana: CONFIRMED. Recipe a5a560fac077, 6 sources, 0 failures md + html.
  Sources 2-4 and 6 (rules.mt.gov, chrome transport per the recipe) fetched
  through the Claude Browser pane with get_page_text, trimmed of the site's
  global footer per the recipe notes, and supplied with `--supply`. Source 6
  (37.40.338, Bed Hold Payments) is newly added to the recipe since the
  standing packet was last retained (the baseline page had recorded this
  provision as pending); retain-packet.py reported it as a new source header
  rather than a replaced one. Retained (hash e0d210dc7d0234ad), promoted.
  Checked date -> 2026-10-06.
- nebraska: CONFIRMED. Recipe 27b925a0693b, 10 sources, 0 failures md + html.
  retain-packet.py reported five "new" source headers relative to the prior
  retained capture (NAC and NAC chapters already covered under different
  packet slots) — net additions, not replacements; nothing removed or
  retitled. Retained (hash ec919800fe41653b), promoted. Checked date ->
  2026-10-06.
- nevada: DRIFT. 2 failures, identical on md and html: `QUOTE not in packet:
  'patients welfare'` and `QUOTE not in packet: 'The facility can no longer
  provide for the needs of the patient and the transfer'`. Source: NAC
  449.74429(1)(a), leg.state.nv.us/nac/NAC-449.html, recipe 1a04d9e0d0e9. The
  page's 2026-09-01 change-log finding (3)
  specifically preserved the regulation's own missing apostrophe in
  "patients welfare" as a deliberate verbatim transcription; the fresh
  capture now reads "patient's welfare" WITH an apostrophe, and the rest of
  the subsection is byte-identical — the Legislative Counsel Bureau appears
  to have corrected its own typo. Main capture retained without promotion
  (hash 6ebc1ab6b6c8abcf); the `moved` supplement (the LTC discharges
  brochure, tools/packets/nevada-packet-moved.txt) was unaffected and
  re-confirmed separately (hash 9588b06441731293), promoted. Checked date
  NOT advanced. Queue FA-Q-20261006-02 opened (drift) for the owner to
  decide whether to update the two quoted spans and retract the 2026-09-01
  finding.
- new-hampshire: CONFIRMED. Recipe 55e50782350a, 9 sources, 0 failures md +
  html. Sources 4-6 (www.dhhs.nh.gov, chrome transport, 403s curl per
  CLAUDE.md) fetched through the Claude Browser pane with
  `document.querySelector('main').innerText` exactly as the recipe notes
  specify (menu labels and the trailing "Escape Site" link left in,
  unedited), and supplied with `--supply`. Retained unchanged since
  2026-09-22 (hash 82bcd4a036e9c300), promoted. Checked date -> 2026-10-06.

Cursor advanced missouri -> new-jersey (past new-hampshire, the fifth
selected unit; nevada's drift does not hold the cursor back).

sync-checked-dates.py: 8 derived dates corrected (table + json; missouri,
montana, nebraska, new-hampshire — nevada correctly excluded). build-
state-picker.py: 51/51 published. build-status.py: baseline 51/51, full
50/51 (nevada's new drift). check-all.py: 102 pages / 52 states, no
unexplained failures. retain-packet.py --verify: 0 failures across 108
manifest entries. generate-sitemap.py: 56 URLs (nevada and texas excluded,
both recorded drift). check-live.py: 5 pages sampled, nothing loaded from
any other host. No deploy.

Reviewer: scheduled pass (portfolio-nightly-qc-review), 2026-10-06. No human
review is claimed for this entry.

## 2026-10-06 — nevada corrected from drift handoff FA-Q-20261006-02 (attended)

The "apostrophe appeared in NAC 449.74429" drift was a capture error, not a
change by the Legislative Counsel Bureau: leg.state.nv.us serves NAC/NRS as
Windows-1252 with no charset (possessive apostrophe = byte 0x92). The
2026-09-01 hand capture dropped it, so the page's finding (3) recorded a typo
that was never in the rule; the recipe's UTF-8 decode turned it into U+FFFD.
Fixes: tools/capture.py gained an opt-in `encoding: "cp1252"` source key
(digest-stable unset, lint rules, self-test); nevada.json sources 1-4 set to
it, and all nine sources sliced to the sections the page quotes (the recipe
was an unsliced auto-draft; source 8 ends before the rotating State
Animal/Bird sidebar widget that made consecutive captures differ). Two
consecutive recipe captures byte-identical (recipe dc167f8f2e6b). Page:
section-01 and docket quotations now "patient's welfare" as the source
prints it; finding (3) retracted in a new 2026-10-06 change-log entry (the
Medicaid manual's own omission stands). 0 failures md + html against the new
capture plus the moved supplement. Retained --result rebuild (hash
f1ddda5550295eca) and promoted; checked date 2026-10-06; check-all 102 pages
clean; capture.py --self-test clean. Reviewer line on the new entry is the
placeholder, so the predeploy gate holds nevada until Carrie reviews. No
deploy.

## 2026-10-06 — kansas recipe backfill (attended, from the 2026-10-01 handoff item 3)

tools/recipes/kansas.json was a draft (every note "DRAFT — replace before
promoting"; no packet history; skipped by every nightly since 2026-09-08).
Finished and verified: source 1 repointed to ksrevisor.gov after the owner
chose to follow the move and record it (www.ksrevisor.org answers 301 to the
same path, observed 2026-10-06), sliced from the statute's own heading;
source 2 (KAR 2022 Book 2, 10.9 MB, pdftotext -layout) sliced on regulation
headings 28-39-145 through the 28-39-150 heading, where the hand capture's
anchors were mid-sentence line cuts; source 3 (ombudsman.ks.gov, HTTP 403 to
every curl variant, still) set to transport chrome / extractor none, supplied
from the built-in browser pane's document.body.innerText, unedited. Lint clean
(digest 405261adf039); two consecutive captures byte-identical (source 3
supplied identically); 0 failures md + html against the new capture plus the
KanCare supplement. Source 3's body wording matches the 2026-08-30 capture
line for line (only the old page-title line differs: the session fetch tool
added it, innerText does not). Retained --result rebuild (hash
7906ea4dc3be37f7), promoted; checked date 2026-10-06; page edits limited to
the source-movement link and retrieval dates plus a dated change-log entry
(reviewer placeholder, so the gate holds kansas until review). check-all: 102
pages clean. Kansas re-enters ordinary rotation review, with the standing note
that source 3 needs the browser pane each time. No deploy.

## 2026-10-08 — Nightly review: New Jersey confirmed; New Mexico and New York tooling-blocked

Cursor stood at new-jersey; selected new-jersey, new-mexico, new-york (next two
alphabetically). Cursor advanced to north-carolina regardless of result.

**New Jersey — confirmed.** Fresh capture of both sources; zero fidelity
failures, markdown and HTML. Retained changed body (source 2: 9570 -> 9500
chars, whitespace collapsed; header title/URL/date unchanged, no replacement
signal). Hash 9df67e0896a52397, promoted. Checked date advanced to Oct 8,
2026 (markdown, re-rendered, synced).

**New Mexico — not reviewed, tooling-blocked.** Fresh capture of both sources
(8.370.16 and 8.312.2 NMAC, www.srca.nm.gov) decoded clean on fetch but
fidelity reported 6 QUOTE-not-in-packet failures, markdown and HTML, each
landing where the document's Word-exported tab-alignment spans sit beside
quoted text. Traced to capture.py's fetch_curl decoding every curl response
as UTF-8 with errors='replace' unless the source sets the opt-in "encoding"
field (added for FA-Q-20261006-02, the Nevada 0x92 case) — these sources
serve undeclared Windows-1252 bytes (0xA0 inside mso-tab-count spans), so
every run of them became U+FFFD. Confirmed deterministic (two consecutive
captures byte-identical) and confirmed against the raw bytes directly (curl +
hexdump: 0xA0 x10 before "Voluntary removal:" in 08.370.0016.html). This is a
capture-side artifact, not source drift: not retained, standing packet and
checked date untouched. Tooling entry opened: FA-Q-20261008-02 (recipe needs
"encoding": "cp1252" on both sources; also notes gathered-work and
licensure-mobility lack the opt-in mechanism entirely).

**New York — not reviewed, tooling-blocked.** Capture failed outright:
"SOURCE 6 failed: No module named 'docx'" — tools/.venv has no python-docx
installed, a known open gap (FA-Q-20260924-04, opened 2026-09-24, already
naming new-york.json among the affected recipes). Bumped that entry
(occurrence 2) rather than opening a duplicate; not retained, standing packet
and checked date untouched.

sync-checked-dates.py corrected 2 derived dates (table + JSON, new-jersey
only). build-status.py re-run. No drift queue entries — the two blocked
pages are tooling findings, not source movement.
