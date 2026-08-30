# Provenance

This project was scaffolded 2026-08-29 as the fourth Field Assembly
database, from the conventions of Gathered Work (first), Rules & Record
(sped-safeguards, second), and Board & Border (licensure-mobility, third,
and the nearer sibling: same one-page-per-jurisdiction shape, same packet
discipline, same generated trackers, same shared-layer structure). A
project of Field Assembly LLC.

Packets. Every page is built from a captured source packet in
`tools/packets/<slug>-packet.txt`: first line the canary, then a header
block, then labeled `SOURCE n:` blocks with URL, the source's own date, and
the retrieval date, closing with `END OF PACKET — n sources`. Large fetched
texts are appended mechanically (file copy), never retyped — retyping is
transcription drift, the exact failure this workflow exists to prevent.
Packets are immutable once a page is built from them; evidence captured
later goes in a supplemental packet beside the original
(`<slug>-packet-<topic>.txt`), and `check-fidelity.py` accepts any number
of packets and checks the page against their concatenation.

The rule this enforces: a page may not assert what no packet holds.
Research notes in `research/` are working material and are not evidence for
anything on a published page. If a finding is good enough to put in the
docket, it is good enough to capture — and if it cannot be captured, the
page should not carry it.

The federal layer. The federal materials (42 CFR 483.15(c), 42 CFR part
431 subpart E, CMS guidance) are a source universe of their own and get
their own packet (`tools/packets/federal-packet.txt`) and their own page. A
state page quotes the state's own statements; the federal page quotes the
federal publisher's. Neither packet is evidence for the other's page, and
where the two publishers disagree, both are quoted and the discrepancy is a
numbered finding — reconciled nowhere.

Deadlines and periods. A notice period, appeal deadline, or bed-hold window
is a quotation like any other: verbatim, double-dated, never calculated
against any calendar, never restated in a different unit. What a deadline
means for a particular case is for the hearing office to determine.

Ombudsman contacts. The ombudsman row quotes the program's own published
contact. Where the state page and the program's own site differ, both are
shown, per the sibling discrepancy rule.

Naming. Built under the working slug transfer-safeguards. On 2026-08-29 —
the day of the scaffold — the owner settled the name: Room & Recourse, at
roomandrecourse.com (unregistered at scaffold time; registration pending).
Wordmarks, page titles, colophons, and the fidelity checker's allowlist
carry the name; the repository directory and the internal tooling keep the
slug.

## Record Standard conformance

Collected under Field Assembly Record Standard 1.0 (effective 2026-08-30;
~/Projects/Field Assembly/field-assembly-standard, release frozen under
versions/1.0 and externally anchored). Local extensions: CHARTER.md and this
file. Adoption status: packet grammar, immutability and supplements, and the
fidelity gate conform; the tooling lineage carries retention and recipes
from Board & Border, adopted as pages are built. Anchoring is not yet
initialized (per CLAUDE.md, it starts under the Gathered Work scheme when
the owner says so, now that real evidence exists) — until the first anchor
run, that is the recorded deviation from STANDARD.md §3.6.
