# transfer-safeguards — operating notes

## Doctrine — the long-horizon frame (read before optimizing anything)

Field Assembly is privately funded institution-building, not a startup. The
full thesis is ~/Projects/Field Assembly/field-assembly-standard/STEWARDSHIP.md;
the rules a working session must not violate are these four. Public access is
permanent and free: no gating, no analytics, no accounts, no advertising, at
any depth, ever. The endowment ceilings (~$6k/year, eventually ≤10 hours/week)
mean expansion never comes at the cost of maintaining what exists — a
collection that cannot be faithfully observed for years is a liability, not
progress. A competent stranger must be able to inherit everything: no
undocumented cleverness, no reliance on memory, no single-vendor dependence.
The corpus is designed to outlive Field Assembly LLC: portable, independently
verifiable, separable from its current custodian. Revenue, if it ever comes,
is upside, not oxygen — never redesign toward a buyer. Collection conventions
live in the Field Assembly Record Standard
(~/Projects/Field Assembly/field-assembly-standard).

Working notes for Claude sessions in this repository. Content rules live in
CHARTER.md (page specification, hard boundaries) and PROVENANCE.md (packet
and quotation rules); this file covers only how to run commands against
this folder and how the site will ship. Fourth Field Assembly database,
after Gathered Work, Rules & Record (sped-safeguards), and Board & Border
(~/Projects/Field Assembly/Licensure Mobility). When a convention question
is not answered here, licensure-mobility is the nearest sibling and its
answer usually transfers.

## Spelling: license, not licence — except inside a quotation

Field Assembly house style is American spelling; the cross-project rule and
its rationale live in ~/Projects/Field Assembly/field-assembly-standard/STYLE.md.
*License* as both noun and verb, in this project's own prose everywhere: page
text, change logs, capture notes, recipe notes, queue entries, commit messages.

**Never change the spelling inside a quotation.** If a source writes *licence*,
the quotation reads *licence*. Restyling quoted text to match house style is
falsifying a source, and it is a worse fault than the inconsistency it tidies
away. The same protection covers a source's own title, filename, and any name
or figure quoted from it.

The deploy gate enforces this (check 3b), stripping quoted spans before the
scan. Two things it does not catch, both known: prose inside an HTML attribute,
such as a meta description, because tags are masked out first; and markdown
sources, which the gate does not read. `tools/fix-licence-spelling.py` does a
corpus-wide pass and carries a self-test whose central case is a quoted
*licence* surviving untouched.

Evidence is never touched. Packets and captures hold what the publisher
published, spelling included.

## Run host commands through Desktop Commander

Anything that touches the git repository or Cloudflare should run through
the Desktop Commander MCP (`mcp__Desktop_Commander__start_process` and its
companions), which executes on the Mac itself with the real filesystem, the
real `~/.wrangler` session, and the real git config.

## The sandbox shell cannot do host-credentialed work

The sandboxed Linux shell reaches sibling folders through mounts, but it
does not share the Mac's home directory. `npx wrangler deploy` fails there
demanding `CLOUDFLARE_API_TOKEN`. Do not work around this by hunting for a
token — run the command through Desktop Commander instead. The same applies
to anything else expecting host credentials or host config. This folder is
now a connected folder and is mounted into the Cowork sandbox (corrected
2026-09-01; it was not when this section was written), so ordinary reads and
tool runs work from the sandbox. Git and `wrangler` still go through Desktop
Commander.

## Prefer host-side writes to this folder

In-place rewrites through a mount (`perl -i`, `sed -i`) strand
`.fuse_hidden…` debris and stale `.git/index.lock` files in the siblings.
Write through Desktop Commander or the Read/Write/Edit file tools. Python
tools in `tools/` are safe to *run* from a sandbox mount (they read and
write whole files); avoid sandbox-side in-place edits of tracked files.

## Provisioning status (updated 2026-09-01)

- **Live and published.** Worker `quiet-marram-7t2d` exists, serves
  roomandrecourse.com through a custom domain bound in the dashboard outside
  wrangler.toml, and `workers_dev` is false so the pages are not published at
  a second address. Deploy with `bash site/predeploy-check.sh && (cd site &&
  npx wrangler deploy)`, only on a passing check and only when the owner asks.
  Unlike the siblings, this worker's deploys report the trigger
  (`roomandrecourse.com (custom domain)`) rather than "No targets deployed".
- The site shell is built: index.html, about.html, 404.html, federal.html,
  legal/terms.html and legal/privacy.html, plus assets/ and the icon set.
  Corrected 2026-09-01. This section previously said the worker was
  scaffolded but uncreated and the shell not yet built; all three claims were
  stale, and a session acting on them went looking for legal pages that had
  existed since August. A provisioning note that is not updated at the moment
  provisioning changes is worse than no note, because it is believed.
- `tools/` adapted 2026-08-30: check-fidelity.py allowlist carries
  roomandrecourse.com (plus two advisory additions), build-status.py uses
  the "Notice periods and deadlines, as stated in the sources" marker and
  tracks the federal layer, render-state.py renders the Room & Recourse
  shell with federal.md → site/federal.html special-cased. See
  tools/README.md.
- Build/review skills exist: rr-state-page and rr-state-review (account
  skills, saved 2026-08-30).
- Iconography adopted 2026-08-30 from the owner's Room & Recourse lockup,
  following the Gathered Work pattern. site/assets/roomandrecourse-wordmark.svg
  (masthead and colophon) is generated by tools/trace-lockup.py from the source
  art at site/assets/roomandrecourse.png — filled outlines, no font dependency,
  recoloured to the site tokens; do not hand-edit it. site/assets/favicon.svg is
  hand-authored: the icon carves the door down to a solid panel with the knob
  knocked out, because the lockup's linework turns to mush below about 32px, and
  tools/make-icons.py redraws that same carving for the PNG and ICO icons. The
  source .png is committed and excluded from deploy by .assetsignore; keep it —
  an earlier session deleted it before committing and lost the letterforms. SVG
  comments must not contain a double hyphen — the CSS token names do, and an XML
  parser rejects the file.
- Anchoring initialized 2026-08-30 (first chain entry 2026-08-30T144139Z,
  near-contemporaneous with the initial captures). Run
  `python3 tools/anchor.py run` after every capture or review session and
  commit anchors/; `upgrade` a day later; never edit anything under
  anchors/.

## Deploy only when asked, and only on a passing check

Once the worker exists, the gate follows the siblings:
`bash site/predeploy-check.sh && (cd site && npx wrangler deploy)` — deploy
only if the check passes and only if the owner asked in that session.
Verify afterwards by fetching changed pages with `curl -sSL` rather than
trusting the deploy log.

## Fidelity before anything ships

A page that has not passed `python3 tools/check-fidelity.py` against its
packet(s) — markdown and HTML both, zero failures — is not done. There is
no expected miss.

## Capture traps, learned in the build (2026-08-30)

Record here rather than in a page, because these cost an hour each to
rediscover and none of them is about any one state.

An empty-looking page is not an absent document. mass.gov's regulation
pages carry no regulation: only metadata, a table of contents for the
title, and download links. The rule lives in the PDF or DOCX posted there.
Massachusetts spent a build cycle recorded as "capture-blocked" on that
mistake. Before writing an absence into a docket row, fetch the downloads
the page offers.

Slice on the body, not the table of contents. A long document usually
prints its section headings twice, and a naive `find()` for the heading
lands in the contents list, producing a slice that begins at the front
matter and runs for tens of thousands of characters. Anchor on the heading
plus the first words of the text under it, and check the head and tail of
every slice before it goes into a packet.

Two-column PDFs interleave. The Missouri CSR and the Louisiana
Administrative Code print in two columns, and `pdftotext -layout` renders
each printed line as one column's text followed by the other's. A sentence
running down a column is therefore broken across lines carrying unrelated
text. Quotations from such a capture are contiguous spans of the capture as
rendered, not of the printed column; verify every candidate span against
the packet mechanically before writing it, and expect to quote some
passages as two adjacent spans.

Transports that need something other than plain curl: mass.gov (403 to
curl on regulation pages and document downloads — use the session fetch
tool); cdph.ca.gov (incomplete certificate chain to curl and to
python/certifi); dhcs.ca.gov (returns a script shell); aging.ny.gov,
rules.sos.ga.gov and dch.georgia.gov PDFs (403); mgaleg.maryland.gov and
mn.gov (render to a scripted client only); legislature.mi.gov (incomplete
chain to curl, and an empty body to the fetch tool — Michigan's statute is
therefore carried through the department's own reproduction of it);
admincode.legislature.state.al.us (JavaScript app over a curl-able GraphQL
endpoint — see the API paragraph in PROVENANCE.md). Curl with a browser
user-agent has been enough for ilga.gov, leg.state.fl.us, revisor.mn.gov,
apps.legislature.ky.gov, legis.iowa.gov, publications.tnsosfiles.com,
law.lis.virginia.gov, dsd.maryland.gov, health.ny.gov and ldh.la.gov.

A revoked rule is a finding, not a missing capture. Kansas's transfer and
discharge regulations, K.A.R. 28-39-147 and 28-39-148, appear in the
Secretary of State's own regulation volume as a bare citation with a
revocation date of May 22, 2009 and no text beneath. Before recording a
rule as uncaptured, check whether the state's code prints it as revoked;
the two look identical from a search engine and mean opposite things.

More transports learned building Rhode Island, Nevada and New Hampshire
(2026-09-01). rules.sos.ri.gov (Rhode Island's official regulation code,
RICR) serves an empty JavaScript shell to curl; render it in a browser, and
where the page offers a "Download Regulation" link, cross-verify against
that PDF (hosted on risos-apa-production-public.s3.amazonaws.com) fetched
by curl and `pdftotext -layout` — both should match. nevadamedicaid.nv.gov
lists its Medicaid Services Manual chapters and forms only via client-side
script, empty to curl; the document link itself must be read with a
browser tool. dhcfp.nv.gov, Nevada's former Medicaid domain, now
301-redirects everything to www.nevadamedicaid.nv.gov — re-resolve any URL
found via search or printed on an older document rather than trusting it.
dhhs.nh.gov (New Hampshire) 403s to both curl and the session fetch tool;
use the browser. He-P 803 and He-E 802, the New Hampshire nursing-home
rules that would sharpen the statute's procedure, stayed capture-blocked
on that same host even from the browser, which offered the PDF only as a
download rather than a page; New Hampshire's page is built on RSA 151:21,
151:25 and 151:26 alone, which happen to state the notice's contents, the
30-day period and its exceptions, and the appeal-rights sentence in full.

A browser text-extraction tool can silently concatenate adjacent page
elements with no delimiter, turning a five-line mailing address into one
run-together string — seen on dhhs.nh.gov contact pages, rendering as
"Brown Building129 Pleasant StreetConcordNH03301". Verify against the
page's own accessibility tree or DOM structure before treating the
concatenation as the source's own formatting, and join the genuinely
separate elements with normal punctuation in the packet rather than
reproducing the run-together artifact.

A JavaScript-only rules portal can carry a public JSON API underneath it,
found building South Dakota (2026-09-02). sdlegislature.gov (the South
Dakota Legislature's own rule and statute site) serves nothing but a
client-side application shell to curl on every page and endpoint that looks
like a document — the rule pages themselves, and even the "download in
Word" and "printer friendly" links reached from them — up to 3 MB of
JavaScript bundle with zero occurrences of any rule number, browser
user-agent or not. The application itself calls a same-origin JSON
endpoint, `https://sdlegislature.gov/api/Rules/<article-number>` (colons
URL-encoded, e.g. `44%3A73`), which returns the whole article as JSON with
the rule text sitting in an "Html" field — a Microsoft Word HTML export,
complete with the document's own per-section revision-tracking tokens and
repeated running heads — and is directly curl-able with no query hash or
session token in the URL, so it is a stable public endpoint rather than an
application-level identifier that could drift. Slice on the chapter, not
the article, exactly as with any other long capture: the field for one
article can hold a dozen chapters and run past 200,000 characters after
stripping the embedded `<style>` blocks the export leaves inline throughout
the body (strip those before stripping tags generally, or the CSS class
declarations swamp the text).

Some states have no reachable publisher at all. Arkansas defeated every
transport available on 2026-08-30 and is deliberately unbuilt:
codeofarrules.arkansas.gov, the only publisher of 20 CAR 410-805, fails TLS
to curl from both the sandbox and the Mac, returns an empty body to the
session fetch tool, and is denied to both the built-in browser and Chrome;
humanservices.arkansas.gov 403s to curl and truncates long PDFs through the
fetch tool at roughly 137k characters, which lands short of the section
that matters; arkleg's code search returns 500. The reachable Arkansas
sources — the 2024 Rules for Nursing Homes, section 317.7, and the DHS
ombudsman site — carry a ten-day notice and no contacts, which would state
Arkansas's law more thinly than it is. Retry from a different publisher
rather than publishing that.

Arizona is unbuilt for the same reason, by a different mechanism.
apps.azsos.gov 403s to curl from both the sandbox and the Mac even with a
full browser header set, and the session fetch tool truncates the 10.3 MB
Title 9 Chapter 10 PDF at about 117k characters — page i of a 343-page
file, far short of R9-10-408 on page 94. The built-in browser can fetch the
bytes (fetch from that origin returns 200) but there is no way to get text
out of them; inflating the content streams in-page fails. The only
reachable Article 4 text is the department's 2013 rulemaking copy, which
titles the rule "Discharge" where the current code titles it "Transfer;
Discharge" and whose own first line says the official version is published
in the Administrative Register. Retry when a per-article publisher exists.

A scanned PDF can hide behind a format parameter. West Virginia's Secretary
of State serves 64 CSR 13 from readfile.aspx, and Format=HTML, Format=PDF
and Format=TEXT all return the same 60-page scanned PDF with no text layer;
only Format=WORD returns the real document. Convert such a file with
`libreoffice --headless --convert-to txt` rather than scraping printable
runs out of the bytes — a naive extraction silently drops short lines and
breaks apostrophes, which corrupts quotations in ways the checker cannot
see, because it compares the page against the same corrupted packet.

Scanned PDFs with no text layer are not a dead end by themselves. Alabama's
department publishes its nursing facility chapter as an image, but the
Legislature publishes the same rule as text. Look for the other publisher
before concluding the text is unreachable, and never reach for OCR — see
PROVENANCE.md.

## One authority for the checked date, and two surfaces nothing generates

A state's "sources last checked" date is published in three places and only one
of them is authoritative: `<dd class="docket-checked">` on
`site/states/<slug>.html`. The STATES JSON island in `site/index.html` (which
feeds the pill tooltip through `build-state-picker.py`) and the last cell of
each row in `site/states/index.html` are both derived from it.

Neither derived surface has a generator behind it, and on 2026-09-01 that
showed: `site/states/index.html` held two table rows — Ohio and Texas, the
exemplars written when the index was created — against thirty-six published
pages, and the STATES JSON held the same two records, so thirty-four states
were live with no row, no record and a pill tooltip carrying no date. Nothing
was broken. The `rr-state-page` skill's closing checklist named STATUS.md and
the picker and never named the table, so thirty-four nightly builds each did
exactly what they were told. The rows were written and the skill's checklist
corrected in the same pass; fixing the rows alone would have lasted one night.

`python3 tools/sync-checked-dates.py` copies the authority into both derived
surfaces; `--check` reports without writing and is check 10 of the deploy gate.
Check 11 covers the layer above it: the tooltip is rendered *from* the JSON, so
a correct JSON whose picker has not been regenerated leaves a stale tooltip
live while check 10 passes. Check 11 runs the generator and fails if it changed
anything.

Two properties of check 10 matter, and the second is the one the sibling's
version does not have. The page is the authority and the script rewrites dates
only, never the status prose — the table sentence and the JSON blurb are
independently written, answer different questions in different places, and
regenerating one from the other would silently rewrite published descriptions.
And a *missing* row fails, not only a stale one: a check that verified the rows
present would have passed on this page every night for thirty-four nights. A
missing row is reported and never repaired, because the sentence is written
from that state's own page and nothing can generate it.

Tripwired both ways on 2026-09-01 before being trusted, the way check 3 was:
row deleted -> FAIL; JSON record deleted -> FAIL; table date wrong -> FAIL;
JSON date wrong -> FAIL; restored -> pass.

One trap found doing it, and it is the mount trap this file already warns
about, met from the other side: `sed -i.tmp` on a file under `site/` leaves an
`index.html.tmp` beside it that the sandbox cannot unlink — the fuse mount
permits the create and refuses the unlink. Remove it through Desktop Commander,
and prefer whole-file writes.

**The deploy gate does not catch that file, and `.assetsignore` does not
exclude it.** Checked on 2026-09-01 with the stray present: all seventeen
checks pass, because every page check globs `*.html` and `index.html.tmp` is
not one. It would have been uploaded and served at
roomandrecourse.com/index.html.tmp — a copy of a page, at an address nothing
links and nothing would ever notice. An earlier note here claimed the colophon
and skip-link checks failed on it; that claim was wrong and is corrected here
rather than edited away. (One gate run during the tripwire did fail with no
cause I could reproduce afterwards, most likely because it read the tree
mid-rename; that is unexplained rather than explained by the stray file.)

The standing exposure was the shape `.assetsignore` has: a denylist, complete
only to the extent someone remembered the last thing worth excluding. Gathered
Work hit the same shape on 2026-09-01 from the other direction and moved its
deploy root to `site/`. This repo already serves `site/`, so what remained was
junk landing *inside* it.

**Closed the same day by check 12**, an allowlist of the kinds of file the site
publishes rather than a list of the ones it does not: `.tmp`, `.bak`, `.orig`,
`.rej`, `.swp` and `.fuse_hidden*` all fail by not being on the list, without
anyone having had to anticipate them. Written here and ported to all three
siblings in the same pass, identical apart from the deploy root. `anchors/` is
exempt everywhere, because where it is published it ships whole by decision and
its extensions are open-ended; only Gathered Work publishes one. Widen the list
in the same commit that adds a legitimate new file type; do not delete the check
to get a deploy out. Tripwired on the Mac in every repo: `.tmp`,
`.fuse_hidden0000`, `.orig` and a nested `.html.bak` each FAIL, clean passes.

## The gate runs on bash 3.2, and the sandbox does not

`/bin/bash` on this Mac is 3.2.57. The Cowork sandbox runs bash 5. Check 12 was
written with a `case` statement inside a command substitution, which bash 5
runs happily and bash 3.2 mis-parses, dying on the `;;` — so the check passed
every test in the sandbox and killed the gate on the host, mid-run, after
several checks had already reported ok.

The gate runs on the host. A shell check tested only in the sandbox has not
been tested. Run `bash site/predeploy-check.sh` through Desktop Commander
before believing any change to it, and prefer `if`/`else` to `case` inside
`$( )` in these scripts.

## Checker and renderer traps

The fidelity checker's contact layers match on patterns, and two false
positives have surfaced. Digits inside an http(s) URL were being read as a
telephone number — Michigan's form filename `.../ITD-100-07262024.pdf`
matched as 100-072-6202 — fixed 2026-08-30 by stripping URLs before the
phone scan, with a self-test case; `tel:` links are still checked. The
address layer has the same shape of bug and is not fixed: where a packet
prints a street address with a street-type abbreviation opening the next
line, as in "540 Cedar Street\nSt. Paul", the packet-side match swallows
the "St." and no longer equals the page-side match. Quote such an address
as a single contiguous span rather than as two.

`render-state.py` runs its markdown inline pass over quoted text, so a
literal asterisk inside a quotation is read as emphasis and disappears from
the HTML. Tennessee's notice footnotes its grounds with asterisks and hit
this; the HTML fidelity check catches it, which is how it was found. Quote
around the asterisk, or fix the renderer if a state's text ever needs one.
