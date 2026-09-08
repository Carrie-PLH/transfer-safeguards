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
