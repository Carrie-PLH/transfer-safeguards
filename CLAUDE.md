# transfer-safeguards — operating notes

## Reading a packet: use capture-core, never a fresh regex

`tools/capture-core.py` holds the canonical reader. Call it:

    _core.packet_sources(text)            # {n: body}, headers and notes excluded
    _core.packet_sources(text, with_headers=True)   # {n: (header_line, body)}
    _core.packet_header(text)             # canary, capture notes, pending list
    _core.normalize_retrieval_dates(text) # flatten dates before comparing captures

Do not write a parser for this. Every ad-hoc one written on 2026-09-03 was
wrong, and each was wrong differently: one matched `RETRIEVED:` where packets
write `retrieved:` and reported twenty-five unchanged jurisdictions as content
drift; one ended a source at the next header without checking for an END SOURCE
marker and mis-attributed a quotation to the wrong document; one ended a source
at END SOURCE with no fallback and, in a packet having none, swallowed nine
following sources into a supplement meant to hold one.

The format varies, and not per repository, which is the trap:

- **Source headers** take three shapes — `SOURCE 1` alone on its line,
  `SOURCE 1:`, and `SOURCE 1 |`. All four collections' `check-fidelity.py`
  already share one pattern accepting all three; capture-core adopts it verbatim.
- **END SOURCE markers** are optional and mixed *within* a repository. Counted
  2026-09-03: sped-safeguards 117 packets with sources, 31 with END SOURCE;
  licensure mobility 58 and 9; gathered work 73 and none; transfer-safeguards
  47 and 43. A block ends at its own marker when it has one and at the next
  header when it does not.
- **`END OF PACKET`** closes the file and is structure, not evidence.
- **The header block** above `SOURCE 1` describes the capture. It is never
  evidence: a capture note *mentioning* an obfuscation placeholder is not a
  packet carrying one, and counting it as one produced a wrong portfolio-wide
  tally on 2026-09-03.

capture-core's reader was diffed against every one of the 299 packets in the
portfolio, against each repository's own `check-fidelity.py`, and agrees on 298.
The one difference is a template file where this reader correctly excludes
capture notes that the older path included. Re-run that diff after any change to
the reader.

## Cloudflare email obfuscation is not a capture limit (2026-09-03)

A page that renders every email address as the placeholder `[email protected]`
has not withheld them. Cloudflare's obfuscation is a one-byte XOR carried in the
page's own markup, so the plaintext is already in the bytes curl receives, and
decoding it is extraction in the same category as reading a `__NEXT_DATA__`
island. `capture-core.py` decodes it, and `extract_html` calls that decoder
before anything else reads the document.

This is worth stating as a rule because the failure was written down as a fact
twice, in two repositories, by sessions that were being careful: Alabama's
capture notes recorded the placeholder as "left as the page renders it", and
Gathered Work's Walden page asserted that a plain fetch "cannot recover the real
addresses" and that a browser executing the de-cloaking JavaScript was required.
Both were reasoning from what the text looked like rather than from what the
bytes contained.

The failure mode it creates is silent and specific. `check-fidelity.py` requires
every address a page publishes to appear in its packet, not the reverse -- so a
packet full of placeholders passes every check while being unable to support any
contact at all. The damage is to what a page *can* say, never to what it says,
and nothing reports it. Alabama is the case that shows the cost: the department's
nursing-home complaint address sat unpublishable for four days on the layer whose
readers are families trying to complain about a facility.

If a packet holds `[email protected]`, the capture is stale, not the source.

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

## A commit stages paths, never the working tree

Stage the paths the pass wrote. Never `git add -A`, `git add .`, `git add -u`,
`git commit -a`, or `git commit -am`. Before committing, run
`git status --short`: if it shows anything outside the paths this pass
produced, commit only its own paths, leave the rest untouched, and name the
other changes in the report rather than absorbing them. A pass with nothing to
do makes no commit, and a pass that finds modifications it did not make
reports them rather than reverting, stashing or cleaning them.

An unattended pass that stages the tree signs its name to whatever an
interactive session had in flight, and its message then describes a fraction
of its own diff. That is how transfer-safeguards `2a7a3c0` came to carry
fifty-one files under a message naming two of them, on 2026-09-04. The full
statement of the rule, and that case, are in the standard's CLAUDE.md
(~/Projects/Field Assembly/field-assembly-standard/CLAUDE.md).

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

**What `curl -sSL` does not tell you.** It confirms that a deploy published the
bytes that were built, and it reads a page's own text. It is not evidence about
third-party requests. Cloudflare's Web Analytics injection depends on request
headers, and curl's defaults do not trigger it — on 2026-09-04 a RUM beacon was
being appended to every page on two of the four sites, and curl reported them
clean throughout, before and after the fix. The deploy gate could not see it
either: the gate reads the HTML on disk, and the injection happens after the
files leave the repository.

So where the question is what a reader's browser actually loads, fetch with a
browser's header set (a real User-Agent and an `Accept: text/html,...` line) and
look for loaded resources — `script`, `link`, `img`, `iframe`, `source`,
`video`, `audio`, `embed`, `object`, CSS `@import`/`url()` — pointing anywhere
but this site's own hosts. Links in prose to source documents are the product
and are never a finding. The full rule and the case are in the standard's
CLAUDE.md.

`tools/check-live.py` is the check that can see this, added 2026-09-04. It
fetches a sample of published pages with a browser's User-Agent and Accept
header and fails on anything *loaded* from a host this site does not own —
script, link, img, iframe, source, video, audio, embed, object, and CSS
`@import`/`url()`. Anchors to source documents are the product and are never a
finding. `--all` reads every published page, `--url` takes specific ones, and
`--self-test` exercises the parser offline. Run it after a deploy; the nightly
QC routine also runs it in every repo it touches. A finding is not necessarily
a mistake in the pages: the 2026-09-04 case was fixed by disabling a setting in
the Cloudflare dashboard, with nothing to change in the repository at all.

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

## The archive layer (added 2026-09-04, pending review)

`tools/spn.py` requests Internet Archive Save Page Now captures for sources a
state page links but has no `web.archive.org` link for. It reads the state
pages themselves to decide what needs capturing, so it cannot drift from what
is published. Read its docstring before touching it; it governs. It is a
port of gathered work's `tools/spn.py` (2026-09-04) — an independent copy per
this portfolio's rule against a shared library across repos, not a wrapper
around it, so a real fix to the shared logic has to be made in every repo's
copy by hand. `gathered work/tools/spn.py` itself is not touched by this port
and does not change.

**In service since 2026-09-04**, on Carrie's decision. The nightly routine
(`portfolio-archive-captures-and-pass-health-sped-lm-rr`) already reads all
four collections against one shared budget of 30 confirmed captures a night,
so this repo now competes for that budget rather than watching gathered work
spend all of it. The backlog here is deep — 121 candidates at the moment of
the decision — and it draws down slowly by design. A growing backlog is
expected and is not a problem to solve.

**What counts as a capture.** Save Page Now returned success, the captured
response was HTTP 200, and the capture played back. A stored 403 or a WAF
interstitial is a refusal page, not evidence, and the script rejects those.
Never record a capture the script did not confirm — a change log listing a
capture that holds a challenge page is worse than one listing nothing.

**The three states a failed source can be in**, which must be named correctly
because they call for different things: *resting*, the ordinary outcome,
which means seven days before it is eligible again; *blocked*, after three
consecutive hard failures, which means held back until a person looks; and
*not reached*, which means the pass ran out of budget before getting to it.
Never write that a failed source is "carried to the next pass" — it is not,
it rests a week first, and saying otherwise misstates the record.

A failed source returns behind sources never attempted, so forward progress
onto uncaptured pages is never displaced by retrying a stubborn host.

**The budget is a number of captures, not attempts.** `--budget 30` works
down the candidate list until twenty are confirmed stored, bounded by an
attempt ceiling of three times the budget. Save Page Now caps concurrent
sessions per account — the same Internet Archive account gathered work's
script uses, credentials shared at `~/.config/ia/spn.env` — so a run against
this repo competes with the other three collections for the same nightly
session budget rather than having one of its own. Let a run finish. Do not
run it twice in a pass, do not raise the budget, and do not request captures
by any other means.

A capture pass records captures. It does not re-verify quotations, re-fetch
sources, change any date, touch the docket, or touch the footer's "Reviewed"
line. If a capture reveals that a source changed, that is a note for the
review pass, not a repair to make here.

**Scope: state pages plus the federal layer** (widened 2026-09-04, same
decision). `scan_all` reads every page under `site/states/` and also
`site/federal.html`, under the slug `federal` — the same name the review
rotation uses for it. The federal page publishes first-party eCFR and CMS
sources exactly as a state page publishes its board's, and scoping the tool
to `site/states/` alone had left those four sources with no archive coverage
at all. The pattern follows sped-safeguards' two-collection version of this
same script.

Board & Border's copy has the identical gap and has not been widened:
`compact.html` is its federal-layer analogue and its `spn.py` does not
mention it. Fix that there, in that repo, when someone is next in it — this
note is the reminder, not the authority.

## The change log is a record, not a claim (adopted 2026-09-04)

`check-fidelity.py` now splits section 04 out of the quotation scan.
`split_change_log` and `CHANGELOG_MARKERS` are ported from Gathered Work, which
has had them since 2026-09-02.

The reason is a contradiction between two rules this project already held. A
category (c) correction entry is *required* to quote the agency's superseded
wording beside the new, so a reader can see what moved. The checker forbids
quoting anything absent from the current packet, and a packet holds only what
the source says today. So the second time a source moves, the required entry
becomes unwritable. That is not a preference clash; the rules disagreed, and
the checker won by default. The 2026-09-04 Nebraska correction was the first
bite: an honest sentence quoting the heading the notice runs into had its
quotation marks stripped to pass. The tool edited the record. Those marks have
since been restored, which is the point.

**Quotations only.** The phone, email and address scans still read the whole
page here. Gathered Work extended the split to contact facts as well, because a
change log there records rejected leads by name; that convention does not exist
in this repo, and exempting contacts would create unverified surface to buy
nothing. If a false-lead convention ever starts here, revisit it then.

**This is not the durable answer.** `retain-packet.py` keeps superseded
captures, so a change-log quotation could be verified against the retained
capture it came from rather than excused. That is strictly stronger: the old
wording stays checked, against the evidence that it was ever said. It is left
for later because the retained history begins 2026-08-27 and is not yet deep
enough to check against, and because it is real work rather than a flag. When
the history is deep enough, prefer it and narrow this exemption.

A marker that fails to match weakens nothing — the split returns the whole page
as live — but it also does nothing, so the self-test pins every heading dialect
these pages actually use, in markdown and HTML.

## Recipe slicing: heading anchors, not line ranges (added 2026-09-04)

Several states publish the provision a page quotes inside a much longer
document — Illinois serves the whole Nursing Home Care Act, and Missouri,
Tennessee and Oklahoma each print one rule inside a chapter PDF. Those captures
used to be taken by hand: extract the whole file, then cut a line range by eye.
A line range is exactly what a nightly pass cannot reproduce, because the
document repaginates and the range silently moves, so those states sat outside
the recipe backfill.

`capture.py` recipes now take a per-source `slice`:

```
"slice": {"from": "<anchor>", "to": "<anchor>", "from_occurrence": 2}
```

`to` is exclusive and optional (omit it to run to the end of the document);
both occurrence keys default to 1. Rules that matter:

- **Anchors match across line breaks.** Every run of whitespace in an anchor
  matches any run of whitespace in the document, so a heading plus the first
  words beneath it works as one anchor even where `-layout` breaks it over two
  lines with alignment spaces.
- **Anchors are case-sensitive, and that is load-bearing.** Tennessee's chapter
  prints its headings twice — title case in the table of contents on page 1,
  capitals over the text — so the capitalised anchor matches the body and
  nothing else, and no occurrence key was needed. Check the case before
  reaching for `from_occurrence`.
- **At least 12 characters** (`MIN_ANCHOR`), enforced by `--lint`. A short
  anchor is how a slice lands in the table of contents and captures the front
  matter instead of the rule.
- **A miss is an error, never a fallback.** Falling back to the whole document
  would still pass fidelity — a superset always does — while the packet quietly
  stopped being the slice its own capture notes describe. If an anchor stops
  matching, read the extraction: a document that has been reissued, repaginated
  or re-headed is a finding about the source, not a recipe to widen until it
  matches again.
- The slice runs **after extraction and before the filters**, which is the order
  the hand captures used. `strip-page-numbers` and `unwrap-hard-wraps` both
  rewrite lines an anchor may sit across, so filtering first would move the
  anchors.
- A source with no slice hashes exactly as it did before the option existed, so
  no capture already taken was invalidated; a recipe that changes its anchors
  captures a different span and shows a different digest. Verified against all
  twelve recipes at the time of the change.

Tennessee was the first state built on it; Missouri, Illinois and Oklahoma
followed the same day. Ported to all three sibling repos 2026-09-04.
**What Missouri taught the option (2026-09-04).** In a two-column render the
reading order is the whole left column, then the whole right, so a rule's own
text need not lie between its own headings. In 19 CSR 30-82, rule .050's
section (2) — the enumerated grounds the page quotes — renders in the
right-hand column of the page whose left column is still printing .020 and
.030, *above* the line carrying the .050 heading, while .050's paragraphs (10)
through (14) render *below* the line carrying the heading of .060. Anchoring on
.050's own heading lost all six grounds. The checker caught it before anything
was promoted, which is the whole argument for capturing to
tools/packets/review/ and checking there.

The fix is not a cleverer anchor. It is to anchor on the headings of the rules
on either side of the spread and accept a superset — Missouri slices .020
through .070 and holds four rules entire. A superset can only add evidence and
never narrows what verifies. Where a two-column document is involved, expect
this, and never tighten a slice to look neat: a slice that reads tidily and
drops a column is the failure mode this whole apparatus exists to prevent.

## Two helpers for the recipe backfill (added 2026-09-04)

`tools/draft-recipe.py <slug>` writes the mechanical half of a recipe from the
standing packet's own SOURCE headers — the source list, URLs, recorded dates,
and an extractor guessed from the URL. Every note says DRAFT. It parses headers
by pattern and will silently skip one it cannot parse: check that the draft has
as many sources as the packet before working on it. South Dakota's packet
defeated it (two headers in a shape the pattern misses), which is why that
state is still hand-written.

`tools/propose-slice.py <slug>` proposes slice anchors by fetching each source
unsliced and locating the standing packet's own span inside it. The first line
of the span becomes `from`, the first line after it becomes `to`, each grown
until unique and at least 45 characters — well above the linter's floor of 12,
because a 13-character anchor that is unique today is one revision away from
matching somewhere else.

Both are drafting aids, not authorities. The anchors they propose still have to
be read, and two habits earned their keep on the first six states:

- **Never accept a mid-sentence anchor.** Colorado's section 15.1 and Nebraska's
  175 NAC span both began mid-sentence in the standing packet, because a hand
  capture had cut a line range. Widen to the enclosing heading instead: a
  superset can only add evidence, and a heading survives a revision that
  renumbers the paragraph beneath it.
- **Prefer an anchor that carries its own date.** Oregon's division 88 prints
  each rule's heading with its effective or amended date, so a rule amended
  after the capture changes its own heading and the slice fails loudly rather
  than quietly capturing the neighbouring rule.

Where the tail after a span holds nothing long enough to anchor on, omit `to`
and run to the end of the document rather than writing a short anchor. Nebraska
source 5 does this deliberately.

## Link-boundary spaces: an artifact class the pages inherited (2026-09-04)

Three pages published a space the publisher does not print, each inside a
quotation or a contact string, and each traceable to the same cause: the
2026-08-30 captures reduced HTML to text by stripping tags, and where a
publisher sets a section number or a phone number as a link, the strip left a
space at the link boundary.

- **Nebraska**: `the text of section 71-445 .` The Legislature's markup is
  `section <a>71-445</a>.`
- **Ohio**: `section 3721.08 , sections 5165.60 to 5165.89 , or section
  5155.31`. codes.ohio.gov sets each number as a link, `section <a>3721.08</a>,`.
- **North Dakota**: `Phone : (701) 328-2311` and `Toll Free : (800) 472-2622`
  in the ombudsman row.

All three are category (c) — our capture introduced it, the page inherited it —
corrected forward with dated entries, no wording otherwise changed. All three
surfaced the same way: the recipe capture stopped matching the old quotation.
Nothing else would have found them, because the page traced perfectly against
the packet that carried the same artifact.

**The scan.** A space before `,` `.` `;` or `:` inside a quoted span on a page
is almost never the publisher's. Run it over the live sections of every page,
excluding the change log, which quotes superseded wording on purpose:

```
grep -n '"[^"]*[[:space:]][,.;:][[:space:]]' states/*.md
```

Two leads remain open, both on states that have no recipe yet:

- **West Virginia**: `Ombudsman Supervisor and nine Regional Ombudsmen .` and
  `Phone: (304) 558-3317 , (877) 987-3646`, both from source 4, an aspx page
  captured by tag strip — the same class, almost certainly. Fix when the state's
  recipe is written; it needs the `docx` extractor for sources 1 to 3 anyway.
- **Idaho**: `section 39-1303 , Idaho Code`, which is **not** the same class and
  must not be assumed to be. It sits in source 1, a PDF of the enrolled Session
  Law, where there are no link boundaries; the space is more likely the
  document's own typesetting or a `-layout` artifact. Read the PDF before
  touching the page.

## Transports learned building Vermont, the District of Columbia and Alaska (2026-09-04)

All three states captured entirely by curl through recipes; none needed a
browser or the session fetch tool. Reachable with a browser user-agent:
legislature.vermont.gov (full-chapter statute pages), dail.vermont.gov and
dlp.vermont.gov (PDFs and pages), humanservices.vermont.gov, asd.vermont.gov,
vtlegalaid.org, vtmedicaid.com; code.dccouncil.gov, dchealth.dc.gov,
oah.dc.gov, aarp.org (Legal Counsel for the Elderly), dcregs.dc.gov listings,
dcgov.seamlessdocs.com; akleg.gov, health.alaska.gov, akoltco.org.

**akleg.gov BASIS is a scripted client over a GET endpoint.** The Alaska
Administrative Code page, akleg.gov/basis/aac.asp, renders nothing to curl,
but the same script answers `?media=print&secStart=7.140.540&secEnd=7.140.585`
with the requested sections as an HTML fragment: no session token, no query
hash, so it is admitted as first-party under the API rule in PROVENANCE.md.
Two things to know. The fragment has no `<html>` or `<body>`, only a single
`div.statute`, so a recipe's html-text scope must name `div.statute`; `body`
matches nothing and the source fails. And the print rendering carries no
effective date, register number or history line, so the source's own date is
"none stated in the print rendering" and must not be supplied from elsewhere.
`?media=js&type=TOC&title=7.140` returns a chapter's table of contents, which is
how the section ranges were found. The statutes side (statutes.asp) takes the
same parameters and was not needed.

**The Council's D.C. Code prints no currency date on a section page.** The
Code's home page does ("Current through ... Law 26-175 effective Aug. 20, 2026")
and is captured as a version witness for the sections, the way Utah carries a
rule-metadata source. Open Law Library asks not to be scraped and to use the
bulk download instead; a handful of section pages is not that, but a whole-title
capture should use the bulk files.

**DC Health's prescribed 6-108 notice form lives on SeamlessDocs.** The
department page embeds `dcgov.seamlessdocs.com/f/DOHNoticeofDischargeTransferor
RelocationForm` in an iframe; the form's labels, its appeal-rights statement
and the department-prescribed ombudsman contact block are in the served markup
and curl returns them. It is the department's instrument on a hosted platform,
not a third party's document. Its own notice paragraph says thirty days where
the statute says 21 calendar days; both are on the page as a finding.

**dcregs.dc.gov serves rule text only through an ASP.NET postback.** The
SectionList page (title, effective date, rulemaking history) is curl-able; the
"View Text" links are `__doPostBack` calls bound to a session, and a direct
RuleDetail address returns 403. Capture the listing and record the text as
capture-pending, as Texas does with the TAC portal.

**Hawaii is deliberately unbuilt (2026-09-04).** HAR 11-94.2, Nursing
Facilities, adopted September 16, 2022, is published by the Department of
Health at health.hawaii.gov/opppd/files/2022/10/11-94.2-2022.pdf as a 66-page
scanned image whose only text layer is the cover sheet: pdftotext yields 17
lines, and pdffonts shows fonts on the cover alone. No second first-party
publisher of the chapter was found: the Department of Health's own
Title 11 index links only that file, the Legislature publishes statutes and
not administrative rules, and 11-94.1 (which text databases still carry) is
repealed by the same instrument. OCR is not a capture. A page built without
the operative chapter would rest on the ombudsman and Med-QUEST pages alone
and state Hawaii's law more thinly than it is. Retry when the department posts
a text version or a per-section publisher exists. Wyoming was also examined and
set aside for a different reason: its licensing rules (HLS chapters 11 and 19)
state no transfer or discharge grounds at all, which is a finding rather than a
transport failure, and its Medicaid nursing-facility chapters on rules.wyo.gov
were not yet reached; it is next in line.

**Vermont's Medicaid hold-bed statement has moved out of the current manuals.**
The department's current General Provider Manual, General Billing and Forms
Manual and Nursing Facility Provider Manual (vtmedicaid.com/api/manuals is the
index) carry no hold-bed section; a 2/1/2019 Vermont Medicaid Provider Manual
still served at vtmedicaid.com/assets/manuals/VTMedicaidProviderManual.pdf
carries §15.2.5 (six consecutive days) but is no longer listed. It was not
captured; the licensing rule's own bed-hold statement (rule 3.12, ten
successive days) is what the page carries. If a full page is built, look for
the current DVHA statement before quoting the 2019 manual with its date.

## A 403 to curl can be a refusal of HTTP/2, not of curl (2026-09-04)

Arizona was recorded as unreachable on 2026-08-30 because apps.azsos.gov (the
Administrative Code PDFs) returned 403 to curl with every header set tried. The
headers were never the problem. The host refuses every HTTP/2 request curl
makes and serves the identical request over HTTP/1.1: `curl --http1.1` alone,
no Referer, no Accept, no Sec-Fetch headers, returns the 10 MB chapter file.
des.az.gov (the ombudsman program) does the same thing with a Cloudflare
challenge page instead of a 403: HTTP/2 gets "Just a moment...", HTTP/1.1 gets
the page. The refusal is keyed to the protocol negotiation (most likely a TLS
fingerprint check that only runs on the h2 path), so bisect on `--http1.1`
before concluding a host is unreachable, and before reaching for a browser.

`capture.py` now takes `"http_version": "1.1"` per source, curl only, pinned to
that one value, opt-in and digest-stable when unset (self-test added). The
packet's capture notes print it. A capture that comes back a few KB long with
"Just a moment..." in it is a challenge page, not the source, and is a failed
fetch.

Two more things from the same pass. **Two-column AAC PDFs read correctly in
`pdftotext -raw`**, which follows the content stream and, for the Arizona
chapter file, yields column order; `-layout` interleaves the columns as it does
for Missouri and Louisiana. Check both before choosing. And the AAC file
hyphenates at line ends (nurs-ing, physi-cian): those are the typesetter's
hyphens, so `join-wrap-hyphens` must NOT be used on it (it would produce
"nurs-ing"); quotations stop at the break or carry it as two spans.

**Arkansas.** codeofarrules.arkansas.gov, which failed TLS to curl on
2026-08-30, answered normally on 2026-09-04; treat that failure as transient. It
is a server-rendered ASP.NET site whose section addresses carry database keys
(titleID, chapterID, subChapterID, partID, subPartID, sectionID) discoverable
from `/Home/GetRulesTreeViewData?levelType=<title|chapter|subchapter|part|
subpart|section>&titleID=..&chapterID=..&subchapterID=..&partID=..&subpartID=..`,
which returns JSON; the keys are stable, not session-bound. Rule pages print the
text twice, rendered and as escaped HTML in a hidden field; both land in a body
capture. humanservices.arkansas.gov (the department's main site) returns a bare
nginx 403 to curl on every path, over HTTP/1.1 and HTTP/2, with or without
headers, and the session fetch tool returns only its menus; its pages are
readable only in a browser, and Arkansas carries one such page in a supplemental
packet marked not re-verifiable. arombudsman.dhs.arkansas.gov is curl-able but
prints no contact in its text — the numbers sit behind a county-search widget —
and that is recorded on the page as what the program publishes.

**Wyoming.** Its Medicaid rules on health.wyo.gov are listed on the HCBS
"Services & Regulations" page, not on a Medicaid rules page (those addresses
404); rules.wyo.gov, the Secretary of State's portal, serves its search only
through ASP.NET postbacks. wyoleg.gov serves the statutes as one PDF per title
(title35.pdf is 2.9 MB); slice on the body heading of the first section with its
first words beneath it, as the recipe does for the Health Facilities Act.

**Hawaii remains unbuilt** after a second look: the Department of Health's
11-94.2 file is still the only publisher, still a scanned image, and the
Lieutenant Governor's rules page links back to the department.
