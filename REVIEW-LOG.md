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
