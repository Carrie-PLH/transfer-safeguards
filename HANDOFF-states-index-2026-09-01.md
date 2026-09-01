# Handoff — the states index: 34 missing table rows, and the footer question

Written 2026-09-01. Paste the section below into a fresh Claude Code session
in `~/Projects/Field Assembly/transfer-safeguards`.

Found by looking at https://roomandrecourse.com/states/ : the page lists two
published states against 37 built. Neither problem is a rendering fault. Both
are gaps in what the build routine was told to do, so both will keep
recurring until the instructions and the gate change — fixing the rows without
fixing those two is a fix with a shelf life of one night.

---

## The prompt

> Read CLAUDE.md, CHARTER.md and the `rr-state-page` skill before changing
> anything.
>
> **What is wrong.** `site/states/index.html` has two maintenance surfaces and
> only one is generated. The abbreviation grid, and the "36 of 51 pages
> published" line under it, come from `tools/build-state-picker.py` and are
> correct. The published-pages table below it is hand-written prose, one row
> per state, with no generator behind it. It holds two rows — Ohio and Texas,
> the exemplar pages written when the index was created. Thirty-four states
> have been built since and none of them added a row.
>
> The build routine is not at fault. The `rr-state-page` skill's closing
> checklist requires that "STATUS.md and the state picker regenerated" and
> never mentions the table, so every one of those nights did exactly what it
> was told.
>
> Board & Border (`~/Projects/Field Assembly/licensure mobility`) has the same
> hand-written table and stays in sync because it has two things this repo
> does not: `tools/sync-checked-dates.py`, and check 10 in its
> `site/predeploy-check.sh`, which treats each page's
> `<dd class="docket-checked">` as the authority and fails the deploy when the
> table cell or the index JSON disagrees. That check exists because the table
> cell drifted unnoticed on five jurisdictions until 2026-08-31. Read both
> before writing anything here; do not modify that repo.
>
> **Three pieces of work, in this order. The last two are what stop it
> recurring, so do not stop after the first.**
>
> **1. Write the 34 missing rows.** One per built state, matching the form
> Ohio and Texas already use: the jurisdiction linked to its page, a status
> sentence saying what that state's own sources state, and the sources-last-
> checked date. Take every fact from the state's own page — the docket rows
> are where it already sits — and take the date from that page's
> `docket-checked` value, which is the authority. Do not take facts from a
> packet, from memory, or from another state's row.
>
> The status sentence is independently written prose, not a copy of the
> blurb in the index JSON: in the siblings those two differ for forty of
> fifty-one, deliberately, because they answer different questions in
> different places. Keep the sentence to what the state publishes — grounds,
> notice period, the office that hears the appeal, the ombudsman — and write
> nothing the page does not already say. No advice, no comparison between
> states, no characterization of whether a state's protections are strong or
> weak. A state whose page records an absence gets a row that says the
> sources do not state it.
>
> A baseline page and a full page both get a row. The difference between
> jurisdictions is depth, and the index already says so.
>
> **2. Port the guard, so a missing row fails the deploy.** Adapt
> `sync-checked-dates.py` from Board & Border and add its gate check to
> `site/predeploy-check.sh`. Adapt rather than copy: that repo has a STATES
> JSON island in `index.html` feeding a pill tooltip, and this one may not
> have the same structure — read this repo's `index.html` before assuming a
> third surface exists. Two properties matter, and the second is the one that
> would have caught this:
>
> - the page's `docket-checked` is the single authority, and the script
>   rewrites dates only, never the status prose;
> - a *missing* row fails, not only a stale one. A check that verifies the
>   rows that exist would have passed happily on this page for thirty-four
>   nights.
>
> Tripwire it both ways before trusting it, the way check 3 was tripwired on
> 2026-09-01: delete a row -> must FAIL; change a row's date to a wrong one ->
> must FAIL; restore -> must pass.
>
> **3. Fix the skill, so tomorrow's build maintains the table.** Add the index
> row to `rr-state-page`'s build steps and to its closing checklist, beside
> STATUS.md and the picker. The checklist is what the nightly routine actually
> works through, so an instruction that is not in it does not happen.
>
> **Then:** `bash site/predeploy-check.sh` must pass with the new check
> included, and the row count must equal the built-page count. Commit, run
> `python3 tools/anchor.py run --note "states index: 34 rows written, date
> guard added"` and confirm it prints "ots: proof stored". Deploy only if the
> owner asks, and verify by fetching https://roomandrecourse.com/states/
> rather than by reading the wrangler log.

---

## The footer, which is a decision rather than a bug

The states index is not missing its footer. It carries the short colophon that
about.html, federal.html and every state page carry: the Field Assembly line,
the contact address, Privacy and Terms, and "The limits".

The home page carries a longer one — the same, plus "Published at
roomandrecourse.com" and a "The deal" block stating that the state pages are
published in full and remain free, that the site transmits and stores nothing
about the reader, and that nothing about any resident or any case reaches it.

Across the portfolio that block sits on Rules & Record's states index but not
on Board & Border's or this one. So three sites disagree, and no rule says
which is right.

Worth deciding rather than patching, and it belongs to the owner. The argument
for putting it on both state indexes: the permanence-and-no-tracking
commitment is the thing a reader most needs to see on the page they actually
land on, and a hub page is where they land. The argument against: a commitment
repeated on every hub reads as marketing rather than as a term, and the home
page is where terms belong.

If it goes on the indexes, it goes on Board & Border's too, in the same pass —
the point is the convention holding, not this one page matching.
