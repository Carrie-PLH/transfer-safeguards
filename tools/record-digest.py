#!/usr/bin/env python3
"""Monthly public change record: triage the drift the retention series already holds.

The problem this closes. retain-packet.py keeps every capture that ever
differed and appends a manifest line for every pass, so this repository already
knows when a source stopped matching what was held. What it does not know is
*why*. A `drift` row means the fresh capture's SOURCE bodies hashed differently
from the newest retained copy, and this repo's own notes name three unrelated
causes with three different remedies. Only one of them is the agency's doing,
and only that one belongs in a public change record.

Two sped-safeguards cases are the standing examples, and both failure modes
occur in every collection. Montana's 2026-08-31 and 2026-09-02 drifts are the
same notice, still printing "11/18/2025 Rev." on every page, extracted under two
different poppler builds; publishing that as a change to Montana's procedural
safeguards would be false. Alabama is the second kind: a recipe backfill changed
which running headers the filters strip, so nearly every paragraph differs while
the document says exactly what it said before.

So the drift count is not a finding, and nothing downstream may treat it as
one. This tool separates the causes per source and reports which is which, so a
session can write a change record from evidence rather than from a tally.

Built on capture-core, not on a parser of its own. `_core.packet_sources`
is the canonical reader and `_core.compare_capture` already classifies what a
fresh capture does to each source: gone, new, same, respaced, grew, shrank.
An earlier version of this file wrote its own header regex and had two of the
exact defects the 2026-09-03 cases record -- it matched only `SOURCE 1:` and
ignored END SOURCE markers, so it read the wrong spans in every packet carrying
one. Both shapes occur inside a single repository, which is the trap: measured
2026-09-03, sped-safeguards had 31 packets with END SOURCE of 117 carrying
sources, transfer-safeguards 43 of 47, licensure mobility 9 of 58, and gathered
work none at all. That is why the rule exists.

What this adds to compare_capture, and nothing else:

  1. **A filter-change discriminator.** `respaced` catches an extractor that
     moved spaces. It cannot catch a filter that started or stopped stripping a
     running header, because that adds and removes whole lines. Comparing again
     with lines that recur at least RUNHEAD_MIN_REPEATS times dropped
     separates a recipe change from a document change.
  2. **Header reading.** compare_capture works by source number, so a document
     that moved to a new address while keeping its position is invisible to it.
     A changed URL, and a changed `source date:`, are each decisive on their own
     and are reported separately.
  3. **What moved.** The paragraphs that actually differ, with a similarity
     ratio, so a one-word difference cannot masquerade as a revision.
  4. **Transport comparison.** Each capture's recorded transport is read and
     the pair compared, because a log entry must say whether the capture method
     was held steady. That is what separates a real revision from extraction
     noise, and it can reframe a whole window: every candidate in
     sped-safeguards' series through 2026-09-08 carries a changed method,
     because that retained history begins inside a recipe backfill.
  5. **A window over the series.** The manifests, read for a date range, with
     attendance counted separately from content.

**This tool never edits a page and never writes a change-log entry.** Same
posture as spn.py and vendor-watch.py: the finding is the output, and deciding
what a change means to a reader stays with the session that has Carrie in it
(FA-D-20260831-09). It needs no network, reads nothing outside
tools/packets/history/, and publishes nothing -- the retention series and the
manifests stay outside site/ under the tier boundary, so an issue written from
this is prose quoting specific wording, never this report.

Usage
-----
    python3 tools/record-digest.py                      # previous calendar month
    python3 tools/record-digest.py --from 2026-09-01 --to 2026-09-30
    python3 tools/record-digest.py --all                # whole retention series
    python3 tools/record-digest.py --slug montana
    python3 tools/record-digest.py --json
    python3 tools/record-digest.py --draft              # issue skeleton
    python3 tools/record-digest.py --tripwire montana   # prove it reacts
    python3 tools/record-digest.py --self-test

Exit codes: 0 report produced, 1 a manifest named a capture that is not on disk
(the series is incomplete and the report cannot be trusted) or a tripwire did
not fire, 2 usage error.
"""

import argparse
import calendar
import datetime as dt
import difflib
import glob
import importlib.util
import json
import os
import re
import sys

# tools/capture-core.py is the portfolio's shared capture module, synced from
# field-assembly-standard. Used here for packet_sources (the canonical reader),
# compare_capture (per-source classification) and normalize_retrieval_dates.
_core_spec = importlib.util.spec_from_file_location(
    'capture_core',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'capture-core.py'))
_core = importlib.util.module_from_spec(_core_spec)
_core_spec.loader.exec_module(_core)

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(HERE, "packets", "history")

SQUASH = re.compile(r"[^a-z0-9]+")

MOVED = "document moved"
DATE_CHANGED = "revision date changed"
TEXT_CHANGED = "text changed"
DROPPED = "source dropped"
ADDED = "source added"
FILTER = "recipe filter changed"
RESPACED = "extractor respacing"

PUBLISHABLE = {MOVED, DATE_CHANGED, TEXT_CHANGED, DROPPED, ADDED}
TOOLING = {FILTER, RESPACED}

VERDICT_ORDER = [MOVED, DATE_CHANGED, TEXT_CHANGED, DROPPED, ADDED, FILTER, RESPACED]


def squash(text):
    """Letters and digits only, lowercased. Spacing and punctuation removed."""
    return SQUASH.sub("", text.lower())


def strip_repeats(text, floor=None):
    """Drop lines recurring at least `floor` times anywhere in the body.

    A line repeated on every page of a PDF is a running header or footer, and
    which of those the filters strip is a property of the recipe. The floor is
    capture-core's own RUNHEAD_MIN_REPEATS so this agrees with what
    f_strip_running_headers considers a running head.
    """
    if floor is None:
        floor = getattr(_core, "RUNHEAD_MIN_REPEATS", 3)
    lines = text.splitlines()
    counts = {}
    for line in lines:
        key = line.strip()
        if key:
            counts[key] = counts.get(key, 0) + 1
    return "\n".join(l for l in lines
                     if not l.strip() or counts.get(l.strip(), 0) < floor)


def header_fields(header_line):
    """URL and the source's own date, from a canonical SOURCE header line."""
    parts = [p.strip() for p in header_line.split("|")]
    url = next((p for p in parts if p.startswith("http")), "")
    sdate = next((p[len("source date:"):].strip()
                  for p in parts if p.lower().startswith("source date:")), "")
    title = re.sub(r"^SOURCE\s*\d+\s*[|:]?\s*", "", parts[0]) if parts else ""
    return {"url": url, "source_date": sdate, "title": title}


def changed_paragraphs(old_body, new_body, limit):
    """Paragraph blocks that differ once spacing and punctuation are discounted."""
    def paras(text):
        return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    old, new = paras(old_body), paras(new_body)
    matcher = difflib.SequenceMatcher(a=[squash(p) for p in old],
                                      b=[squash(p) for p in new])
    out = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        out.append({"tag": tag, "old": old[i1:i2], "new": new[j1:j2]})
        if len(out) >= limit:
            break
    return out


def classify(old_raw, new_raw, limit=4):
    """Why two captures of the same slug differ, source by source."""
    old_raw = _core.normalize_retrieval_dates(old_raw)
    new_raw = _core.normalize_retrieval_dates(new_raw)

    cmp = _core.compare_capture(old_raw, new_raw)
    A = _core.packet_sources(old_raw, with_headers=True)
    B = _core.packet_sources(new_raw, with_headers=True)

    sources, verdicts = [], set()

    for n in cmp["gone"]:
        h = header_fields(A[n][0])
        verdicts.add(DROPPED)
        sources.append({"source": n, "verdict": DROPPED, "url": h["url"],
                        "note": "present in the superseded capture, absent from this one"})
    for n in cmp["new"]:
        h = header_fields(B[n][0])
        verdicts.add(ADDED)
        sources.append({"source": n, "verdict": ADDED, "url": h["url"],
                        "note": "new in this capture"})

    changed_nums = ({n for n, _a, _b in cmp["grew"]} |
                    {n for n, _a, _b in cmp["shrank"]})

    for n in sorted(set(A) & set(B)):
        old_head, old_body = A[n]
        new_head, new_body = B[n]
        oh, nh = header_fields(old_head), header_fields(new_head)
        entry = {"source": n, "url": nh["url"], "notes": [], "segments": [],
                 "similarity": None}

        if oh["url"] and nh["url"] and oh["url"] != nh["url"]:
            entry["notes"].append(f"address: {oh['url']} -> {nh['url']}")
            entry["verdict"] = MOVED
        if oh["source_date"] != nh["source_date"]:
            entry["notes"].append(
                f"source date: {oh['source_date']!r} -> {nh['source_date']!r}")
            entry.setdefault("verdict", DATE_CHANGED)

        if n in cmp["same"]:
            entry.setdefault("verdict", None)
        elif n in cmp["respaced"]:
            entry.setdefault("verdict", RESPACED)
            entry["notes"].append("identical but for whitespace")
        elif n in changed_nums:
            if squash(strip_repeats(old_body)) == squash(strip_repeats(new_body)):
                entry.setdefault("verdict", FILTER)
                entry["notes"].append(
                    "identical once recurring header and footer lines are dropped")
            else:
                entry["verdict"] = TEXT_CHANGED
                entry["segments"] = changed_paragraphs(
                    strip_repeats(old_body), strip_repeats(new_body), limit)
                ratio = difflib.SequenceMatcher(
                    a=squash(old_body), b=squash(new_body)).ratio()
                entry["similarity"] = round(ratio, 4)
                if ratio >= 0.995:
                    entry["notes"].append(
                        f"similarity {entry['similarity']} — a very small share of "
                        "the text moved; read the paragraphs before calling this a revision")

        if entry.get("verdict"):
            verdicts.add(entry["verdict"])
            sources.append(entry)

    ordered = sorted(verdicts, key=VERDICT_ORDER.index)
    return {"verdicts": ordered, "sources": sources,
            "publishable": any(v in PUBLISHABLE for v in ordered)}


def previous_month(today=None):
    today = today or dt.date.today()
    year, month = ((today.year, today.month - 1) if today.month > 1
                   else (today.year - 1, 12))
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, 1).isoformat(), dt.date(year, month, last).isoformat()


def read_capture(slug, filename):
    path = os.path.join(HISTORY, slug, filename)
    if not os.path.exists(path):
        return None, path
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read(), path


def load_rows(slug_filter=None):
    rows = []
    for path in sorted(glob.glob(os.path.join(HISTORY, "*", "manifest.jsonl"))):
        slug = os.path.basename(os.path.dirname(path))
        if slug_filter and slug != slug_filter:
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    row = json.loads(line)
                    row["slug"] = slug
                    rows.append(row)
    return rows


def build(rows, start, end, limit=4):
    window = [r for r in rows if start <= r.get("date", "") <= end]
    attendance = {}
    for r in window:
        key = r.get("result", "unknown")
        attendance[key] = attendance.get(key, 0) + 1

    # capture filename -> transport recorded for it, per slug. A drift whose
    # two captures were taken by different methods is extraction, not movement
    # (CLAUDE.md, "Promotion happens only as a side effect of retention").
    transports = {}
    for r in rows:
        if r.get("capture"):
            transports[(r["slug"], r["capture"])] = r.get("transport") or ""

    findings, tooling, missing = [], [], []
    for r in sorted(window, key=lambda r: (r.get("date", ""), r["slug"])):
        if r.get("result") != "drift":
            continue
        entry = {"slug": r["slug"], "date": r.get("date"), "kind": r.get("kind"),
                 "capture": r.get("capture"), "supersedes": r.get("supersedes")}
        if not r.get("supersedes"):
            entry.update({"verdicts": ["no superseded capture recorded"],
                          "sources": [], "publishable": True})
            findings.append(entry)
            continue
        new_raw, new_path = read_capture(r["slug"], r["capture"])
        old_raw, old_path = read_capture(r["slug"], r["supersedes"])
        if new_raw is None or old_raw is None:
            missing.append(new_path if new_raw is None else old_path)
            continue
        entry.update(classify(old_raw, new_raw, limit))
        was = transports.get((r["slug"], r["supersedes"]), "")
        now = transports.get((r["slug"], r["capture"]), "")
        entry["transport"] = {"was": was, "now": now, "held": was == now}
        if not entry["transport"]["held"]:
            entry["method_changed"] = (
                f"capture method changed between these two captures "
                f"({was or 'unrecorded'} -> {now or 'unrecorded'}); "
                "read this as extraction before reading it as movement")
        (findings if entry["publishable"] else tooling).append(entry)

    return {"window": {"from": start, "to": end}, "attendance": attendance,
            "passes": len(window), "findings": findings, "tooling": tooling,
            "missing_captures": missing}


def render(result, out=sys.stdout):
    w = result["window"]
    out.write(f"Change record triage — {w['from']} to {w['to']}\n")
    out.write(f"{result['passes']} pass(es): " +
              ", ".join(f"{k} {v}" for k, v in sorted(result["attendance"].items()))
              + "\n")

    if result["missing_captures"]:
        out.write("\nINCOMPLETE SERIES — manifest names captures not on disk:\n")
        for p in result["missing_captures"]:
            out.write(f"  {p}\n")

    out.write(f"\nCANDIDATE FINDINGS ({len(result['findings'])}) — "
              "read each capture before publishing anything\n")
    if not result["findings"]:
        out.write("  none in this window\n")
    for f in result["findings"]:
        out.write(f"\n  {f['date']}  {f['slug']} ({f['kind']})  "
                  f"{f['supersedes']} -> {f['capture']}\n")
        out.write("    " + "; ".join(f["verdicts"]) + "\n")
        if f.get("method_changed"):
            out.write(f"    ! {f['method_changed']}\n")
        for s in f.get("sources", []):
            out.write(f"    source {s['source']}: {s['verdict']}\n")
            if s.get("url"):
                out.write(f"      {s['url']}\n")
            for n in s.get("notes", []):
                out.write(f"      - {n}\n")
            for seg in s.get("segments", []):
                out.write(f"      [{seg['tag']}] {len(seg['old'])} para out, "
                          f"{len(seg['new'])} in\n")
                for p in seg["old"][:2]:
                    out.write("        was: " + " ".join(p.split())[:200] + "\n")
                for p in seg["new"][:2]:
                    out.write("        now: " + " ".join(p.split())[:200] + "\n")

    out.write(f"\nTOOLING, NOT NEWS ({len(result['tooling'])}) — this project's own "
              "extraction and filters, never a state's edit\n")
    for f in result["tooling"]:
        out.write(f"  {f['date']}  {f['slug']} ({f['kind']})  "
                  f"{'; '.join(f['verdicts'])}\n")


def render_draft(result, out=sys.stdout):
    w = result["window"]
    pub = result["findings"]
    out.write(f"# The change record — {w['from']} to {w['to']}\n\n")
    out.write("DRAFT. Every line is either evidence from the retention series or a "
              "TODO for the session writing this. Nothing is publishable until a "
              "person has read the captures it names. The retained captures and the "
              "manifests stay outside site/ — quote specific wording, never paste "
              "this report.\n\n")

    out.write("## What moved in the states' own documents\n\n")
    if not pub:
        out.write("No source-side change was recorded in this window. "
                  f"{result['attendance'].get('confirmed', 0)} pass(es) confirmed the "
                  "sources unchanged. Say so plainly rather than omitting the "
                  "section.\n\n")
    for f in pub:
        out.write(f"- **{f['slug']}** ({f['date']}) — {'; '.join(f['verdicts'])}. "
                  "TODO: one sentence on what changed, then the superseded and current "
                  f"wording quoted from tools/packets/history/{f['slug']}/"
                  f"{f['supersedes']} and {f['capture']}.\n")
        if f.get("method_changed"):
            out.write(f"  - {f['method_changed']}\n")
        for s in f.get("sources", []):
            for n in s.get("notes", []):
                out.write(f"  - source {s['source']}: {n}\n")
    out.write("\n## Corrections\n\nTODO: what was wrong, what it says now, the date, "
              "and who caught it (named only with their agreement). A category (c) "
              "entry quotes the superseded wording beside the new.\n")
    out.write("\n## Published and deepened\n\nTODO: from STATUS.md, including the "
              "*Without a recipe* list.\n")
    out.write("\n## Still not published by the state\n\nTODO: from the pages' "
              "capture-pending lists.\n")
    out.write("\n## Where two of a state's documents disagree\n\nTODO: from numbered "
              "findings in the page change logs.\n")
    out.write("\n## Tooling notes\n\n")
    out.write(f"{len(result['tooling'])} drift event(s) in this window came from this "
              "project's own extraction or filters rather than from any state: ")
    out.write(", ".join(sorted({f["slug"] for f in result["tooling"]})) or "none")
    out.write(". Publishing them is the difference between a change record and a "
              "marketing page.\n")


# --- tripwire ------------------------------------------------------------------

def tripwire(slug, out=sys.stdout):
    """Prove the classifier reacts, against this slug's own retained captures.

    A checker trusted on synthetic input only has not been tested. This takes
    the two newest retained captures for a slug, mutates one in memory two ways,
    and asserts the verdicts. It writes nothing.
    """
    files = sorted(f for f in os.listdir(os.path.join(HISTORY, slug))
                   if f.endswith(".txt"))
    if len(files) < 1:
        out.write(f"no retained captures for {slug}\n")
        return 1
    raw, _ = read_capture(slug, files[-1])
    sources = _core.packet_sources(raw, with_headers=True)
    if not sources:
        out.write(f"{files[-1]} carries no SOURCE blocks\n")
        return 1
    n = sorted(sources)[0]
    body = sources[n][1]
    words = [w for w in body.split() if len(w) > 4]
    if not words or body not in raw:
        out.write(f"{files[-1]} source {n} offers nothing safe to mutate\n")
        return 1

    # Mutate inside the source body, not anywhere in the file. An earlier
    # version replaced the first match in the whole raw text, which often landed
    # in the capture notes above SOURCE 1 -- where packet_sources correctly sees
    # nothing, so the tripwire reported a failure that was its own.
    at = raw.index(body)

    def splice(new_body):
        return raw[:at] + new_body + raw[at + len(body):]

    word = words[0]

    fails = []

    r = classify(raw, splice(body.replace(word, word.upper() + "XQZ", 1)))
    if TEXT_CHANGED not in r["verdicts"] or not r["publishable"]:
        fails.append(f"one-word edit not reported as a text change: {r['verdicts']}")

    r = classify(raw, splice(body.replace(" " + word + " ", word, 1)))
    if r["publishable"]:
        fails.append(f"respacing reported as publishable: {r['verdicts']}")

    r = classify(raw, raw)
    if r["verdicts"]:
        fails.append(f"identical captures produced verdicts: {r['verdicts']}")

    out.write(f"tripwire against {slug}/{files[-1]}, source {n}\n")
    for f in fails:
        out.write(f"  FAIL {f}\n")
    if not fails:
        out.write("  one-word edit FAILS as a text change\n")
        out.write("  respacing does not\n")
        out.write("  an identical pair produces nothing\n")
        out.write("  PASSED\n")
    return 1 if fails else 0


# --- self-test -----------------------------------------------------------------

HEAD = ("CANARY: line\nASSEMBLED: 2026-09-01\nCAPTURE NOTES\n"
        "- SOURCE 1: transport curl; extractor pdftotext-raw.\n\n")


def _pk(*sources, end_marker=False):
    """Build a packet. sources is (url, source_date, body) triples."""
    out = [HEAD]
    for i, (url, sdate, body) in enumerate(sources, 1):
        out.append(f"SOURCE {i}: A document | {url} | source date: {sdate} | "
                   f"retrieved: 2026-09-01\n\n{body}\n")
        if end_marker:
            out.append("END SOURCE\n")
    return "\n".join(out)


def self_test():
    fails = []

    def want(r, verdict, label, publishable=True):
        if verdict is None:
            if r["verdicts"]:
                fails.append(f"{label}: expected nothing, got {r['verdicts']}")
            return
        if verdict not in r["verdicts"]:
            fails.append(f"{label}: expected {verdict}, got {r['verdicts']}")
        if r["publishable"] != publishable:
            fails.append(f"{label}: publishable={r['publishable']}, expected {publishable}")

    # Extractor respacing: same words, spaces moved inside them.
    a = _pk(("https://x/n.pdf", '"11/18/2025 Rev."',
             "Under IDEA Part B\n\nthe parent is presumed to be the parent."))
    b = _pk(("https://x/n.pdf", '"11/18/2025 Rev."',
             "Under IDEA PartB\n\nthe parentis presumed tobe the parent."))
    want(classify(a, b), RESPACED, "respacing", publishable=False)

    # Real text change.
    c = _pk(("https://x/n.pdf", "none", "You have 30 calendar days to file."))
    d = _pk(("https://x/n.pdf", "none", "You have 60 calendar days to file."))
    r = classify(c, d)
    want(r, TEXT_CHANGED, "text change")
    if not r["sources"] or not r["sources"][0]["segments"]:
        fails.append("text change produced no paragraphs")

    # Retrieval date alone is never a change.
    e = HEAD + "SOURCE 1: A | https://x/n.pdf | source date: none | retrieved: 2026-08-25\n\nSame.\n"
    f = HEAD + "SOURCE 1: A | https://x/n.pdf | source date: none | retrieved: 2026-09-02\n\nSame.\n"
    want(classify(e, f), None, "retrieval date only")

    # Revision date changed though the body is identical.
    g = _pk(("https://x/n.pdf", '"11/18/2025 Rev."', "Same."))
    h = _pk(("https://x/n.pdf", '"04/02/2026 Rev."', "Same."))
    want(classify(g, h), DATE_CHANGED, "revision date")

    # Document moved.
    i = _pk(("https://x/old.pdf", "none", "Same."))
    j = _pk(("https://x/new.pdf", "none", "Same."))
    want(classify(i, j), MOVED, "moved document")

    # Running-header filter change: one side repeats the head on every page.
    hd = "Alabama Procedural Safeguards"
    plain = "Right to Participation\n\nYou may attend.\n\nRight to Notice"
    withhd = (f"{hd}\n\nRight to Participation\n\n{hd}\n\nYou may attend.\n\n"
              f"{hd}\n\nRight to Notice")
    want(classify(_pk(("https://x/n.pdf", "none", plain)),
                  _pk(("https://x/n.pdf", "none", withhd))),
         FILTER, "running-header filter", publishable=False)

    # A moved document whose text also respaced is still publishable.
    want(classify(_pk(("https://x/old.pdf", "none", "Under IDEA Part B")),
                  _pk(("https://x/new.pdf", "none", "Under IDEA PartB"))),
         MOVED, "moved and respaced")

    # END SOURCE markers must not change the reading. This is the case the
    # earlier hand-rolled parser got wrong.
    k = _pk(("https://x/1.pdf", "none", "First document says A."),
            ("https://x/2.pdf", "none", "Second document says B."), end_marker=True)
    m = _pk(("https://x/1.pdf", "none", "First document says A."),
            ("https://x/2.pdf", "none", "Second document says C."), end_marker=True)
    r = classify(k, m)
    want(r, TEXT_CHANGED, "END SOURCE packet")
    if [s["source"] for s in r["sources"]] != [2]:
        fails.append(f"END SOURCE packet: change attributed to "
                     f"{[s['source'] for s in r['sources']]}, expected [2]")

    # A dropped source.
    n1 = _pk(("https://x/1.pdf", "none", "A."), ("https://x/2.pdf", "none", "B."))
    n2 = _pk(("https://x/1.pdf", "none", "A."))
    want(classify(n1, n2), DROPPED, "dropped source")

    # Window filtering and attendance.
    rows = [{"slug": "s", "date": "2026-08-15", "result": "confirmed"},
            {"slug": "s", "date": "2026-09-02", "result": "confirmed"}]
    res = build(rows, "2026-08-01", "2026-08-31")
    if res["passes"] != 1 or res["attendance"] != {"confirmed": 1}:
        fails.append(f"window filter wrong: {res['passes']} {res['attendance']}")

    if previous_month(dt.date(2026, 1, 14)) != ("2025-12-01", "2025-12-31"):
        fails.append("previous_month wrong across a year boundary")

    total = 11
    if fails:
        print("\n".join(fails))
        print(f"\nSELF-TEST FAILED: {len(fails)} failure(s) of {total} cases.")
        return 1
    print(f"SELF-TEST PASSED: {total} cases.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="end")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--slug")
    ap.add_argument("--segments", type=int, default=4)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--tripwire", metavar="SLUG")
    ap.add_argument("--self-test", action="store_true", dest="selftest")
    args = ap.parse_args(argv)

    if args.selftest:
        return self_test()
    if not os.path.isdir(HISTORY):
        sys.stderr.write(f"no retention series at {HISTORY}\n")
        return 2
    if args.tripwire:
        return tripwire(args.tripwire)

    if args.all:
        start, end = "0000-00-00", "9999-99-99"
    elif args.start or args.end:
        start = args.start or "0000-00-00"
        end = args.end or "9999-99-99"
    else:
        start, end = previous_month()

    result = build(load_rows(args.slug), start, end, args.segments)

    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    elif args.draft:
        render_draft(result)
    else:
        render(result)
    return 1 if result["missing_captures"] else 0


if __name__ == "__main__":
    sys.exit(main())
