#!/usr/bin/env python3
"""Every published state page must appear on both index surfaces, with its own date.

The date a state's sources were last checked is published in four places, and
only one of them is authoritative — since 2026-09-05 (FA-D-20260905-02) that
is the Markdown source, as it is for every other published fact:

  1. states/<slug>.md          **Sources last checked.** (ISO)  AUTHORITY
  2. site/states/<slug>.html   <dd class="docket-checked">      derived (render-state.py, display form)
  3. site/index.html           STATES JSON "checked"            derived (this script)
  4. site/states/index.html    the table row's last cell        derived (this script)

A review pass that confirms a state updates the .md and re-renders the page
through tools/render-state.py; it never edits the HTML. (2) is kept honest by
the deploy gate's parity check, and this script's --check reports a stale page
without ever writing one. (3) feeds the pill tooltip through
tools/build-state-picker.py. (4) is hand-written prose with a date embedded in
it, and has no generator behind it. Before 2026-09-05 this docstring declared
the rendered page the authority and nothing wrote back to the Markdown — the
design under which a review pass edits generated output and the parity gate
then correctly fails the next deploy.

Adapted from Board & Border's tools/sync-checked-dates.py on 2026-09-01, with
one thing added that the sibling's version does not do, and that its absence
here cost thirty-four nights.

The sibling checks the rows that exist. This repository's failure was not a
stale row but a missing one: site/states/index.html held two rows — Ohio and
Texas, written when the index was created — against thirty-six published
pages, and the STATES JSON held the same two records, so thirty-four states
were live with no row, no record and a pill tooltip carrying no date at all.
A check that verified only the rows present would have passed on that page
every night. So coverage is checked first and is a failure in its own right:
a published page with no row, or no JSON record, fails.

What this script rewrites, and what it does not. It rewrites dates. It never
touches the status prose in either surface. Those two descriptions are
independently written and answer different questions in different places — the
table sentence is what a reader scanning the index reads, the JSON blurb feeds
the pill and the search index — and regenerating one from the other would
silently rewrite published descriptions. It also never invents a row: a
missing row needs a sentence written from the state's own page, which is a
person's work, so coverage failures are reported and never repaired.

    python3 tools/sync-checked-dates.py            # fix the derived dates
    python3 tools/sync-checked-dates.py --check    # report only, exit 1 on drift
    python3 tools/sync-checked-dates.py --self-test

Run from the project root.
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOME = ROOT / "site" / "index.html"
STATES_INDEX = ROOT / "site" / "states" / "index.html"
SITE_STATES = ROOT / "site" / "states"

# One published row: the slug is taken from the link in the first cell, the
# date from the last. The middle cell is prose and is never captured for
# rewriting — only spanned.
ROW = re.compile(
    r'(<tr><td><a href="(?:/states/)?([a-z\-]+)(?:\.html|/)">.*?</td><td>)([^<]*)(</td></tr>)', re.S
)
JSON_BLOCK = re.compile(
    r'(<script type="application/json" id="state-index">\s*)(\[.*?\])(\s*</script>)', re.S
)
CHECKED = re.compile(r'class="docket-checked">([^<]+)<')
MD_CHECKED = re.compile(r'\*\*Sources last checked\.\*\*\s*(.+)')

STATES_MD = ROOT / "states"

# House display form, duplicated from render-state.py deliberately: each
# repository carries its own copy of shared logic, per the portfolio rule
# against a shared library across repos.
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def display_date(s):
    m = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})', s.strip())
    if not m:
        return s.strip()
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not 1 <= month <= 12:
        return s.strip()
    return f"{_MONTHS[month - 1]} {day}, {year}"


def authority(states_md=None):
    """slug -> the date the Markdown source declares, in display form."""
    states_md = states_md or STATES_MD
    out = {}
    for f in sorted(states_md.glob("*.md")):
        if f.stem == "README":
            continue
        m = MD_CHECKED.search(f.read_text(encoding="utf-8"))
        if m:
            out[f.stem] = display_date(m.group(1))
    return out


def page_dates(site_states=None):
    """slug -> the date the rendered page publishes (derived; report-only)."""
    site_states = site_states or SITE_STATES
    out = {}
    for f in sorted(site_states.glob("*.html")):
        if f.stem == "index":
            continue
        m = CHECKED.search(f.read_text(encoding="utf-8"))
        if m:
            out[f.stem] = m.group(1).strip()
    return out


def table_rows(text):
    """slug -> date, as the table publishes it."""
    return {m.group(2): m.group(3).strip() for m in ROW.finditer(text)}


def json_records(text):
    m = JSON_BLOCK.search(text)
    if not m:
        return None, None
    return m, json.loads(m.group(2))


def main(argv):
    check_only = "--check" in argv
    pages = authority()
    if not pages:
        print("ERROR: no published state pages found", file=sys.stderr)
        return 2

    idx = STATES_INDEX.read_text(encoding="utf-8")
    home = HOME.read_text(encoding="utf-8")

    mj, records = json_records(home)
    if mj is None:
        print("ERROR: STATES JSON block not found in site/index.html", file=sys.stderr)
        return 2

    # --- coverage first. A page nobody listed is the failure this check exists
    # for, and it cannot be repaired mechanically: the row carries a sentence
    # about that state's own sources.
    in_table = set(table_rows(idx))
    in_json = {r.get("slug") for r in records}
    missing = []
    for slug in sorted(pages):
        if slug not in in_table:
            missing.append(("table", slug))
        if slug not in in_json:
            missing.append(("json", slug))
    # And the reverse: a row for a page that is not published.
    for slug in sorted(in_table - set(pages)):
        missing.append(("table", slug + " (no such source)"))
    for slug in sorted(in_json - set(pages)):
        missing.append(("json", slug + " (no such source)"))
    # A source with no rendered page at all.
    rendered = page_dates()
    for slug in sorted(set(pages) - set(rendered)):
        missing.append(("page", slug + " (source has no published page)"))

    for where, slug in missing:
        print(f"MISSING {where:<6} {slug}")

    # --- dates
    drift = []

    # The rendered page is derived by render-state.py; report a stale one but
    # never write it — the fix is a re-render, and the parity gate enforces it.
    for slug, want in pages.items():
        cur = rendered.get(slug)
        if cur is not None and cur != want:
            drift.append(("page", slug, cur, want))

    def fix_row(m):
        head, slug, cur, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        want = pages.get(slug)
        if want and cur.strip() != want:
            drift.append(("table", slug, cur.strip(), want))
            return f"{head}{want}{tail}"
        return m.group(0)

    idx_new = ROW.sub(fix_row, idx)

    home_new = home
    changed = False
    for r in records:
        want = pages.get(r.get("slug"))
        if want and r.get("checked") != want:
            drift.append(("json", r["slug"], r.get("checked"), want))
            r["checked"] = want
            changed = True
    if changed:
        body = "[\n" + ",\n".join(
            json.dumps(r, ensure_ascii=False) for r in records
        ) + "\n]"
        home_new = home[: mj.start(2)] + body + home[mj.end(2):]

    for where, slug, cur, want in drift:
        print(f"{where:<6} {slug:<22} {cur} -> {want}")

    page_drift = [d for d in drift if d[0] == "page"]

    if not drift and not missing:
        print(f"every source has a page, a row and a record, and the checked "
              f"dates agree across all four places ({len(pages)} sources).")
        return 0

    if missing:
        print(f"\n{len(missing)} entr(ies) missing. A row carries a sentence "
              f"written from that state's own page and is not generated — write it "
              f"in site/states/index.html and site/index.html by hand.")
        return 1

    if check_only:
        print(f"\n{len(drift)} derived date(s) disagree with the Markdown. "
              f"Run: python3 tools/sync-checked-dates.py"
              + (" — and re-render any 'page' rows through tools/render-state.py"
                 if page_drift else ""))
        return 1

    if idx_new != idx:
        STATES_INDEX.write_text(idx_new, encoding="utf-8")
    if home_new != home:
        HOME.write_text(home_new, encoding="utf-8")
    fixed = len(drift) - len(page_drift)
    print(f"\n{fixed} derived date(s) corrected from the Markdown.")
    if page_drift:
        print(f"{len(page_drift)} page(s) disagree with their source and must be "
              f"re-rendered through tools/render-state.py — this script never edits pages.")
        return 1
    return 0


def self_test():
    """The three behaviours worth pinning: prose is never rewritten, a stale
    date is caught, and a missing row is caught."""
    import tempfile
    ok = True

    row = ('<tr><td><a href="/states/ohio/">Ohio</a></td><td>Eight grounds; thirty '
           'days’ notice — an em dash, and a "quoted" phrase</td>'
           '<td>2026-08-01</td></tr>')
    m = ROW.search(row)
    if not m or m.group(2) != "ohio" or m.group(3) != "2026-08-01":
        print("FAIL: row did not parse"); ok = False
    else:
        rebuilt = f"{m.group(1)}2026-08-30{m.group(4)}"
        if "Eight grounds" not in rebuilt or "a \"quoted\" phrase" not in rebuilt:
            print("FAIL: prose was not preserved verbatim"); ok = False
        if "2026-08-30" not in rebuilt or "2026-08-01" in rebuilt:
            print("FAIL: date was not rewritten"); ok = False

    # a table cell containing a tag would break the [^<]* date capture; the
    # date cell is a bare date by construction and this pins it.
    if ROW.search('<tr><td><a href="/states/ohio/">Ohio</a></td><td>x</td>'
                  '<td><b>2026-08-30</b></td></tr>'):
        print("FAIL: a marked-up date cell should not parse as a date"); ok = False

    if display_date("2026-08-30") != "Aug 30, 2026":
        print("FAIL: display_date did not convert an ISO date"); ok = False
    if display_date("Aug 30, 2026") != "Aug 30, 2026":
        print("FAIL: display_date rewrote a non-ISO date"); ok = False

    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d)
        (p / "ohio.md").write_text("# Ohio\n\n**Sources last checked.** 2026-08-30\n")
        (p / "README.md").write_text("not a state source")
        got = authority(p)
        if got != {"ohio": "Aug 30, 2026"}:
            print(f"FAIL: authority() returned {got}"); ok = False

    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d)
        (p / "ohio.html").write_text('<dd class="docket-checked">Aug 30, 2026</dd>')
        (p / "index.html").write_text("not a state page")
        got = page_dates(p)
        if got != {"ohio": "Aug 30, 2026"}:
            print(f"FAIL: page_dates() returned {got}"); ok = False

    covered = table_rows(row)
    if "texas" in covered:
        print("FAIL: coverage saw a slug that is not there"); ok = False
    if "ohio" not in covered:
        print("FAIL: coverage missed a slug that is there"); ok = False

    print("self-test passed" if ok else "SELF-TEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main(sys.argv))
