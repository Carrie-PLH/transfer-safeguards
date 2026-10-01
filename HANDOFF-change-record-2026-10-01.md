# Handoff — publish the first Room & Recourse change-record issue

> **COMPLETED. Do not run this.** Verified 2026-10-01: /changes/ is live at
> roomandrecourse.com with the September 2026 issue (commit 25a935b, owner
> review 2026-10-01), and the Built by Reassembly credit is on all 59 pages,
> enforced by predeploy check 7b. The handoff's lists were incomplete: the
> issue carries fifteen corrections, not seven, and Texas's Sep 5 handbook
> revision as a state change. See QUEUE.md, 2026-10-01.

Written 2026-10-01. Paste the section below into a Claude Code session running
on the Mac, in `~/Projects/Field Assembly/transfer-safeguards`.

This is a working session's job, not an unattended pass's. It makes editorial
calls about what a reader is told, decides whether a capture artifact needs a
live-source check, and may design and build a page template that does not
exist yet — all things the `rr-monthly-change-record` scheduled task is
constrained from doing (`MONTHLY-RECORD-PASS.md`: "it does not write the
issue, edit any page, touch `site/`, or deploy").

Read `MONTHLY-RECORD-PASS.md` and the draft it produced,
`change-record/drafts/2026-09.md` (committed `44ea8a4`, pushed), before
changing anything.

---

## The prompt

> **Where this stands.** The monthly change-record pass ran for the first time
> 2026-10-01, covering 2026-09-01 through 2026-09-30. It confirmed
> `tools/record-digest.py --self-test` and `--tripwire alabama` both pass, ran
> the triage (96 passes: 44 confirmed, 1 drift, 51 rebuild), triaged the one
> candidate finding, committed the draft, and pushed. It wrote no page,
> touched no `site/` file, and ran no capture, retention, or deploy tool, per
> its own constraints. Three jobs are left, and the third is the real one.
>
> **1. The one candidate isn't a finding, and the reason matters for how you
> read the rest of this month.** texas (main), 2026-09-05, was reported as "no
> superseded capture recorded" — `tools/packets/history/texas/manifest.jsonl`
> holds exactly one entry, so there is nothing to diff against. That is
> already marked `TRIAGE:` in the draft as a retention-series question, not a
> finding, and needs no further action. But it is not an isolated oddity:
> `tools/packets/history/` currently holds 19 states with exactly one capture,
> 19 with two, 7 with three, and two with four or five. The retention series
> itself only started 2026-08-27 (CLAUDE.md, "The change log is a record, not
> a claim"), and September was the month most states got their *second* ever
> retained capture — which is exactly why `record-digest.py` surfaced almost
> nothing: most of what changed this month has no earlier capture to be
> compared against yet. Expect sparse digest output again in October and
> November, growing less sparse as the series deepens, and do not read a thin
> candidate list as a quiet month.
>
> **2. The draft's four remaining sections need filling in**, and here the
> mechanical/judgment split that worked for the siblings doesn't fully hold —
> the "Corrections" section especially needs more than a pull, because the
> digest's silence on it is a real gap, not a null result:
>
> - **Corrections** — `record-digest.py` reported zero tooling-attributable
>   drift this window, but at least seven page corrections dated inside it
>   describe exactly the class of defect that section exists to record, all
>   caught by hand while writing recipes rather than by the digest:
>   Oklahoma (2026-09-04, wrong rule citation carried in from the packet
>   header), North Dakota, Ohio, Nebraska (all 2026-09-04), West Virginia
>   (2026-09-08), and Idaho (2026-09-22) — all link-boundary spacing the
>   2026-08-30 tag-strip capture inserted at an `<a>` boundary, the class
>   CLAUDE.md documents under "Link-boundary spaces" — and New Hampshire
>   (2026-09-22, FA-D-20260922-04: commas the page had added when none of the
>   publisher's own markup separated the address fields). Checked why the
>   digest missed all seven: every one of those states' `tools/packets/
>   history/` directories holds exactly one capture, dated at or after the
>   correction — the same "no superseded capture recorded" shape as texas.
>   The correction is real and already reviewer-confirmed on each page; it
>   just predates this collection's retention series, so there is no pair for
>   the tool to diff. Read each entry at the line cited above before writing
>   the issue — none of them changed what a quotation *means*, only its
>   literal characters, so whether any belongs in a public change-record issue
>   (as opposed to staying a page-level note) is a judgment call, not a given.
>   This gap is itself worth a line in Tooling notes or a queue entry if you
>   think record-digest should flag "first capture, but the page's own change
>   log records a correction dated in this window" as a distinct case — right
>   now it can't see the page prose at all, only the capture pairs.
> - **Published and deepened** — pull from `STATUS.md` (generated 2026-10-01:
>   baseline 51/51, full pages 50/51, Hawaii the one exception, already
>   documented as capture-blocked — no "Without a recipe" list exists in this
>   repo's `STATUS.md`, unlike sped-safeguards'). The real story is bigger than
>   STATUS.md's snapshot shows: September is the month this collection went
>   from partial baseline coverage (`git log` shows baseline pages still being
>   added as late as "Add Utah, New Mexico, Maine baseline pages (39/51)") to
>   51/51 baseline and 50/51 full pages — on the order of forty "deepen to full
>   page" commits across the month. That is this month's headline, not a
>   footnote, and the issue should probably say so in its own words rather than
>   listing every state.
> - **Still not published by the state** — capture-pending markers exist on
>   nearly every one of the 51 pages (`grep -rln "Capture pending" states/
>   *.md` currently returns 50 of 51), so a literal pull would be the whole
>   collection and isn't useful as written. Narrow to absences worth a reader's
>   attention: Hawaii's whole operative rule (scanned image, no text layer, no
>   second publisher — CLAUDE.md, "Hawaii: a rule present but unquotable");
>   New Hampshire's He-P 803 and He-E 802 (403 to every transport tried); and
>   Idaho's repealed framework (SB 1015 voided the state's entire
>   transfer/discharge chapter effective 2025-07-01, and the replacement
>   statute states none of it — a legislative fact, not a capture failure).
> - **Where two of a state's documents disagree** — several numbered findings
>   already state this precisely; start from North Dakota's 2026-09-02 entry
>   (findings 1-4: a 24- vs 30-day Medicaid leave allowance in two of the
>   department's own documents; two different addresses for the same Appeals
>   Supervisor; a pre-merger department name still live in the rule; a street
>   address the ombudsman's own page omits but the department's provider
>   directory states), Oklahoma's 2026-09-18 entry (finding 9: the health
>   department's rule and the Medicaid agency's rule state opposite things
>   about whether a hospital-stay bed is held), and Nebraska's 2026-09-22
>   entry (finding 3: a 1995-dated compiled manual against a department index
>   page claiming a 2024 amendment that appears nowhere in the compiled text).
>   These three are a start, not a sweep — no exhaustive pass across all 51
>   change logs was done for this handoff.
>
> **3. Decide what the issue itself says, and where it lives — this is the
> real open question.**
>
> Nothing called `/changes/` exists on this site yet (`site/changes/` is
> absent, and neither CHARTER.md nor PROVENANCE.md mentions it — the entire
> spec is `MONTHLY-RECORD-PASS.md`'s own closing line, that issues "publish at
> `/changes/`, which is separate from any reader-facing records page"). Two of
> the three sibling collections have already built theirs this cycle
> (sped-safeguards shipped its first issue 2026-10-01, licensure mobility's
> equivalent handoff is still open) — so there is now a working pattern to
> look at rather than a blank page.
>
> Recommended order, most preferred first:
>
> 1. **Build `/changes/` now, one entry per month, each a few sentences per
>    state plus a link to that state's own page and change-log anchor, and
>    use September as its first entry — following the shape sped-safeguards
>    just shipped.** The content mostly already exists, reviewer-confirmed, on
>    the state pages themselves (the September deepening wave, the seven
>    corrections, the three cross-document disagreements above); writing the
>    digest is mostly linking and summarizing. It also closes the same gap the
>    sibling closed: this project's own tooling and `MONTHLY-RECORD-PASS.md`
>    have been promising a `/changes/` page since before any page existed to
>    make that promise true.
> 2. **Decide this month isn't worth a first issue and hold**, noting why in
>    `QUEUE.md`. Weaker here than it was for sped-safeguards: September's
>    actual content (the deepening wave plus seven real corrections plus three
>    documented disagreements) is substantial, not a quiet month — holding
>    would be deferring a decision that has gotten easier, not harder, to make.
> 3. **Wait for `/changes/` conventions to settle across the other three repos
>    first, then build all remaining ones in one pass.** Not recommended on
>    its own schedule: this collection's September has more to show than a
>    typical sibling month, and waiting trades a concrete reader benefit now
>    for a consistency benefit that a later pass can still deliver by simply
>    matching the pattern already shipped.
>
> Option 1 is preferred. If you build it: this will be the first deploy this
> cycle for roomandrecourse.com, which means it is also the deploy that must
> carry the pending footer-credit line (root `CLAUDE.md`, "Footer credit
> (pending, added 2026-09-29)" — `Built by <a
> href="https://reassembly.fieldassembly.net/">Reassembly</a>`, matching the
> site's existing footer style, no new colors or fonts). The colophon footer
> is template-generated in `tools/render-state.py` (the single f-string that
> builds `<footer class="colophon">`), so edit the template, not any output
> page — add the line in the same pass, mention it in your deploy report, and
> add `roomandrecourse.com` to the "Done" list in root `CLAUDE.md` once
> deployed. sped-safeguards and gathered work both enforce their version with
> a predeploy check (7b) and a small `footer-credit.py`; this repo's
> `site/predeploy-check.sh` has no such check yet (its check 7 covers only the
> disclaimer and the existing colophon content) — worth adding the same
> enforcement in the same pass, but not required to ship the line itself.
>
> Keep the project's existing discipline: the issue quotes specific
> superseded and current wording for the correction-equivalent findings above,
> never pastes this report, a diff, or a manifest line
> (`MONTHLY-RECORD-PASS.md`, "What the pass must never publish"), and goes
> through a passing `site/predeploy-check.sh` before anything ships.
>
> **Do not** treat this handoff as authorization to deploy. Deploy only if the
> owner asks in this session, and only on a passing predeploy check.

---

## Where the evidence is

- Draft: `change-record/drafts/2026-09.md`, commit `44ea8a4`.
- The seven correction entries referenced above: `states/oklahoma.md`
  (2026-09-04 entry), `states/north-dakota.md` (2026-09-04),
  `states/ohio.md` (2026-09-04), `states/nebraska.md` (2026-09-04),
  `states/west-virginia.md` (2026-09-08), `states/idaho.md` (2026-09-22),
  `states/new-hampshire.md` (2026-09-22).
- The three disagreement findings referenced above: `states/north-dakota.md`
  (2026-09-02 entry, findings 1-4), `states/oklahoma.md` (2026-09-18 entry,
  finding 9), `states/nebraska.md` (2026-09-22 entry, finding 3).
- Retention-series shape: `tools/packets/history/*/manifest.jsonl` — 19
  states at one capture, 19 at two, 7 at three, 2 at four or more, counted
  2026-10-01.
- Open queue items this pass left untouched, unrelated to the change record
  but filed against this repo: `field-assembly-standard/queue/open/
  FA-Q-20260924-03-rr-capture-tooling.md` (fetch_curl's UTF-8-only decoding
  corrupts windows-1252 sources, e.g. New Mexico) and `FA-Q-20260924-04-
  rr-capture-tooling.md` (missing python-docx dependency, plus a Maine recipe
  defect that would persist even once it's installed).
- `STATUS.md` (generated 2026-10-01) for the baseline/full/Spanish counts.
- Footer-credit instruction: root `CLAUDE.md`, "Footer credit (pending, added
  2026-09-29)". `tools/render-state.py`, the f-string building `<footer
  class="colophon">`, for where to add the line.
