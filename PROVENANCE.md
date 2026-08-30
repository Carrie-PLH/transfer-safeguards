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

A packet header is not evidence. The capture notes and the pending list
describe how the capture was taken and what is missing; only the text
inside a `SOURCE n:` block proves anything. Anything a page will quote must
therefore sit in a source body, and where the thing worth quoting is
something a publisher says about its own document — Massachusetts calls its
posted copy of 130 CMR 456.000 an unofficial version and names the
Massachusetts Register as official — the page carrying that statement is
captured as its own source rather than summarised in the header. The
fidelity checker enforces this on its own: it reads only source bodies, so
a quotation supported by header text fails, which is how the rule was
found.

The rule this enforces: a page may not assert what no packet holds.
Research notes in `research/` are working material and are not evidence for
anything on a published page. If a finding is good enough to put in the
docket, it is good enough to capture — and if it cannot be captured, the
page should not carry it.

Agency APIs as a transport. Adopted 2026-08-30, at the owner's decision,
when Alabama's operative rule proved unreachable by every ordinary means:
the Department of Public Health publishes chapter 420-5-10 only as a
scanned PDF with no text layer, and the Legislature's code site renders its
pages only to a scripted client. The site is backed by a public GraphQL
endpoint that returns the rule as text to curl, and that capture is
admitted as first-party — it is the publisher's own text from the
publisher's own system, not a rendering, a mirror, or a machine's reading
of a picture. Three conditions attach. The capture notes must carry the
full request URL, including any query hash. They must state plainly that
the capture came from the site's API rather than from its pages, so that a
reader and a reviewer both know which surface was read. And where the URL
carries an application-level identifier — a persisted-query hash, a session
or build token — the notes must say so, because such an identifier can
change when the site is redeployed: when a previously good request stops
returning the document, the reviewer treats it as capture drift to be
re-established, never as evidence that the document moved or was withdrawn.
A browser-rendered capture remains a last resort below this, and must be
marked as not re-verifiable by the automated pass. OCR is not a capture at
all: it is a machine's reading of an image of the text, and admitting it as
quotable would put a silent error channel inside the discipline the whole
corpus rests on.

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
from Board & Border, adopted as pages are built. Anchoring initialized
2026-08-30 at the owner's request: first chain entry 2026-08-30T144139Z
over tools/packets/ (federal, ohio, texas), both TSA tokens verifying, OTS
proof pending upgrade. Unlike the siblings' first entries, this one is
near-contemporaneous with the initial captures, not a backfill. No open
deviations from STANDARD.md §3.
