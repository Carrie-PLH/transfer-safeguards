#!/usr/bin/env python3
"""Packet retention: keep every capture that ever differed, and a dated record of every pass.

The problem this closes. Until 2026-08-27 a confirmed nightly review replaced
tools/packets/<slug>-packet.txt with the fresh capture, and the capture it
replaced survived only in git. That is recoverable but not queryable: nothing
could answer "what did this provision say on this date" or show a reader the
text a change log entry says moved. The public change log promises change
tracking; this is what lets it show its work.

What is stored, and what is not. A confirmed pass usually means the sources did
not change, and a second identical copy of an unchanged capture asserts nothing.
So retention is difference-based: the fresh capture's SOURCE bodies are hashed,
and a file is written only when that hash differs from the newest one already
retained. Every pass appends a manifest line either way, so the series records
attendance (what was checked, when, with what result) separately from content
(what the sources actually said). History holds one file per revision, not one
per pass.

What the hash covers. Everything from the first SOURCE header to the end of the
file, with retrieval dates normalized away and whitespace collapsed. Deliberately
excluded: the canary line, the assembly date, and the capture notes, which
describe the capture rather than the source. Two captures of the same unchanged
notice hash alike even though their headers differ, which is the point. Source
URLs are recorded separately, so a moved document is visible as a finding even
when its text is identical — the redirect is the change.

Drift captures are retained unconditionally and permanently. They are the only
artifact holding the new text and the old text side by side, and they stay in
the series after the owner's rebuild as the record of what was superseded.

Transport strings are checked, not trusted. build-status.py reads a capture as
recipe-era when its transport carries `recipe <12 hex>`, and that string used to
exist only because an operator typed it correctly. It is now derived from the
capture: a packet written by capture.py declares its recipe and digest in its
capture notes, so --transport describes the fetch and the tool appends the
reference. A transport naming a digest the capture does not declare is refused,
and so is one that says "recipe" over a capture that declares none.

Layout:
    tools/packets/history/<slug>/<YYYY-MM-DD>.txt      a capture that differed
    tools/packets/history/<slug>/manifest.jsonl        append-only, one line per pass

Usage:
    python3 tools/retain-packet.py <capture.txt> --result confirmed|drift|rebuild
                                   [--date YYYY-MM-DD] [--state <slug>]
                                   [--kind main|es|languages] [--transport <note>]
                                   [--no-promote]
    python3 tools/retain-packet.py --backfill [--dry-run]
    python3 tools/retain-packet.py --log <slug>
    python3 tools/retain-packet.py --verify
    python3 tools/retain-packet.py --self-test

A confirmed retention also promotes the capture to tools/packets/<slug>-packet.txt,
which is the workflow's definition of confirmed: these are now the current sources.
Drift never promotes — the page and its packet are the owner's to change, through
the sped-state-page skill, after a human reads the drift.

Exit codes: 0 clean, 1 failures, 2 usage error.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKETS = os.path.join(ROOT, "tools", "packets")
HISTORY = os.path.join(PACKETS, "history")

RESULTS = ("baseline", "confirmed", "drift", "rebuild")

SOURCE_RE = re.compile(r'^SOURCE\s+\d+:\s*(.*)$', re.MULTILINE)
RETRIEVED_RE = re.compile(r'retrieved:\s*\d{4}-\d{2}-\d{2}', re.IGNORECASE)
URL_RE = re.compile(r'https?://[^\s|]+')
DATE_RE = re.compile(r'(\d{4}-\d{2}-\d{2})')

# The transport string is not free text when the capture was produced by a
# recipe. build-status.py decides whether a capture is recipe-era by looking for
# `recipe <12 hex>` in the transport, and until now nothing produced that string
# except an operator typing it. On 2026-08-29 three captures were recorded as
# `recipe kansas (digest ab0eef872761)` — accurate English, unmatched by the
# pattern — and all three dropped out of the comparable series silently, which
# is worse than an error because the count of method-unknown captures went up as
# recipes were added. The reference is now derived from the capture itself: a
# packet written by capture.py names its recipe and digest in its capture notes,
# so the one true answer is in the file and does not need to be retyped.
RECIPE_NOTE_RE = re.compile(
    r'tools/recipes/([A-Za-z0-9_-]+)\.json\s*\(recipe digest ([0-9a-f]{12})\)')
RECIPE_TRANSPORT_RE = re.compile(r'\brecipe\s+([0-9a-f]{12})\b')
RECIPE_WORD_RE = re.compile(r'\brecipes?\b', re.IGNORECASE)


def recipe_of(text):
    """(recipe name, digest) if this capture says which recipe produced it."""
    m = RECIPE_NOTE_RE.search(text)
    return (m.group(1), m.group(2)) if m else (None, None)


def transport_for(text, given):
    """The transport string to record, or a refusal.

    Returns (transport, note, error). Exactly one of transport and error is set;
    note is prose for the operator when the string was altered.

    Three rules, and they are all about the same thing — that the recorded
    provenance should be checkable against the artifact rather than asserted:

    - A capture that names its recipe gets the canonical `recipe <digest>`
      reference appended if the operator's text does not already carry it. The
      operator keeps describing the fetch; the tool writes the reference.
    - A transport naming a digest the capture does not declare is refused. That
      is a claim about provenance contradicted by the file in hand.
    - A transport that says `recipe` on a capture with no recipe digest is
      refused. It is unverifiable, and it is precisely the string that would be
      counted as recipe-era on the strength of nobody having checked.
    """
    name, digest = recipe_of(text)
    claimed = RECIPE_TRANSPORT_RE.findall(given or '')

    if digest:
        ref = f'recipe {digest}'
        wrong = [c for c in claimed if c != digest]
        if wrong:
            return None, None, (
                f'transport names recipe digest {wrong[0]}, but the capture was '
                f'produced by tools/recipes/{name}.json (recipe digest {digest}). '
                f'Drop the digest from --transport and the reference will be '
                f'written from the capture.')
        if not given:
            return ref, None, None
        if digest in claimed:
            return given, None, None
        return f'{given}, {ref}', (
            f'transport reference written from the capture: {ref}'), None

    if given and RECIPE_WORD_RE.search(given):
        return None, None, (
            'transport claims a recipe, but this capture declares none in its '
            'capture notes. A capture produced by tools/capture.py names its '
            'recipe and digest there; one that does not is not recipe-era, and '
            'recording it as though it were would put an incomparable capture '
            'into the comparable series. Describe the fetch without the word.')

    return given, None, None

# Both header dialects: "ASSEMBLED: 2026-08-25" (current) and the nine early
# packets' prose "Assembled: 2026-08-23. State slug: texas."
ASSEMBLED_RE = re.compile(r'^\s*assembled:\s*(\d{4}-\d{2}-\d{2})', re.IGNORECASE | re.MULTILINE)
STATE_RE = re.compile(r'^\s*STATE:\s*([a-z-]+)\s*$', re.MULTILINE)
SLUG_RE = re.compile(r'state slug:\s*([a-z-]+)', re.IGNORECASE)


# --- reading a capture -------------------------------------------------------

def source_headers(text):
    """The SOURCE header lines, which carry title | url | source date | retrieved."""
    return SOURCE_RE.findall(text)


def source_urls(text):
    """URLs in header lines only. A URL inside a captured document body is the
    source's own content, not an address this project fetched."""
    out = []
    for h in source_headers(text):
        m = URL_RE.search(h)
        if m:
            out.append(m.group(0).rstrip('.,;)'))
    return out


def header_lines(text):
    """SOURCE header lines with the retrieval date stripped: title, URL, and the
    source's own date. Compared separately from the body so that a document which
    moved, or was re-dated by the agency without being rewritten, still registers
    as a change. A redirect is a finding even when the text behind it is identical."""
    return [RETRIEVED_RE.sub('', h).strip(' |') for h in source_headers(text)]


def normalized_body(text):
    """The captured document text alone. Header lines are dropped along with the
    canary, the assembly date, and the capture notes, all of which describe the
    capture rather than the source. Two captures of the same unchanged notice
    hash alike however their headers differ, which is what makes an unchanged
    confirm distinguishable from a real revision."""
    m = SOURCE_RE.search(text)
    body = text[m.start():] if m else text
    body = SOURCE_RE.sub('', body)
    return re.sub(r'\s+', ' ', body).strip()


def body_hash(text):
    return hashlib.sha256(normalized_body(text).encode('utf-8')).hexdigest()[:16]


def assembled_date(path, text):
    """The capture's own assembly date, then git's first sight of the file, then mtime.
    Fabricating a date here would put a false date on evidence, so each fallback is
    recorded by the caller rather than silently substituted."""
    m = ASSEMBLED_RE.search(text)
    if m:
        return m.group(1), 'header'
    try:
        out = subprocess.run(
            ['git', '-C', ROOT, 'log', '--diff-filter=A', '--format=%ad',
             '--date=short', '--', os.path.relpath(path, ROOT)],
            capture_output=True, text=True, timeout=30)
        d = out.stdout.strip().splitlines()
        if d and DATE_RE.match(d[-1]):
            return d[-1], 'git'
    except Exception:
        pass
    return date.fromtimestamp(os.path.getmtime(path)).isoformat(), 'mtime'


def slug_of(path, text):
    m = STATE_RE.search(text) or SLUG_RE.search(text)
    if m:
        return m.group(1)
    base = os.path.basename(path)
    base = re.sub(r'-packet(-[a-z]+)?\.txt$', '', base)
    base = re.sub(r'-\d{4}-\d{2}-\d{2}\.txt$', '', base)
    return base or None


# --- the manifest ------------------------------------------------------------

def manifest_path(slug):
    return os.path.join(HISTORY, slug, "manifest.jsonl")


def read_manifest(slug):
    p = manifest_path(slug)
    if not os.path.exists(p):
        return []
    rows = []
    with open(p, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_manifest(slug, row):
    os.makedirs(os.path.join(HISTORY, slug), exist_ok=True)
    with open(manifest_path(slug), 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def newest_stored(rows, kind):
    """The most recent entry of this kind that resolves to a retained file."""
    for r in reversed(rows):
        if r.get('kind', 'main') == kind and r.get('capture'):
            return r
    return None


def capture_filename(slug, day, kind, taken):
    stem = day if kind == 'main' else f'{day}-{kind}'
    name = f'{stem}.txt'
    suffix = 'b'
    while name in taken:
        name = f'{stem}-{suffix}.txt'
        suffix = chr(ord(suffix) + 1)
    return name


# --- retention ---------------------------------------------------------------

def retain(capture, result, day=None, slug=None, kind='main',
           transport=None, promote=None, out=print):
    if result not in RESULTS:
        out(f'unknown result {result!r}; expected one of {", ".join(RESULTS)}')
        return 2
    if not os.path.exists(capture):
        out(f'no such capture: {capture}')
        return 2

    text = open(capture, encoding='utf-8').read()
    slug = slug or slug_of(capture, text)
    if not slug:
        out(f'cannot determine state slug for {capture}; pass --state')
        return 2

    date_source = 'given'
    if not day:
        m = DATE_RE.search(os.path.basename(capture))
        if m:
            day, date_source = m.group(1), 'filename'
        else:
            day, date_source = assembled_date(capture, text)

    h = body_hash(text)
    urls = source_urls(text)
    headers = header_lines(text)
    rows = read_manifest(slug)
    prev = newest_stored(rows, kind)

    def header_changes():
        old = prev.get('headers') if prev else None
        if not old or old == headers:
            return None
        return {'gone': [x for x in old if x not in headers],
                'new': [x for x in headers if x not in old]}

    row = {
        'date': day,
        'result': result,
        'kind': kind,
        'hash': h,
        'sources': len(headers),
        'urls': urls,
        'headers': headers,
    }
    if date_source != 'given':
        row['date_source'] = date_source
    transport, note, err = transport_for(text, transport)
    if err:
        out(err)
        return 2
    if note:
        out(note)
    if transport:
        row['transport'] = transport

    unchanged = prev is not None and prev['hash'] == h
    # Drift is retained whatever the hash says. A drift result means the checker
    # found a fact on the page that no longer verifies, and the capture proving
    # that is worth keeping even in the odd case where the body hash is stable
    # (a contact changed inside an otherwise identical document, say).
    if unchanged and result != 'drift':
        row['capture'] = prev['capture']
        row['stored'] = False
        hc = header_changes()
        if hc:
            row['header_changes'] = hc
    else:
        taken = {r['capture'] for r in rows if r.get('capture')}
        name = capture_filename(slug, day, kind, taken)
        os.makedirs(os.path.join(HISTORY, slug), exist_ok=True)
        shutil.copy2(capture, os.path.join(HISTORY, slug, name))
        row['capture'] = name
        row['stored'] = True
        if prev:
            row['supersedes'] = prev['capture']
            hc = header_changes()
            if hc:
                row['header_changes'] = hc

    append_manifest(slug, row)

    if promote is None:
        promote = result in ('confirmed', 'rebuild')
    if promote:
        dest = os.path.join(PACKETS, f'{slug}-packet.txt' if kind == 'main'
                            else f'{slug}-packet-{kind}.txt')
        shutil.copy2(capture, dest)

    state = 'retained' if row['stored'] else f'unchanged since {prev["capture"]}'
    out(f'{slug} {day} {result}: {state} · hash {h} · {row["sources"]} source(s)'
        + (' · promoted' if promote else ''))
    if row.get('header_changes'):
        out('  source headers changed (a moved or re-dated document is a finding):')
        for x in row['header_changes']['gone']:
            out(f'    - {x}')
        for x in row['header_changes']['new']:
            out(f'    + {x}')
    return 0


# --- backfill ----------------------------------------------------------------

def backfill(dry_run=False, out=print):
    """Seed history from the packets standing today. These files are the original
    captures, so their own assembly dates are genuine provenance, not a guess."""
    packets = sorted(p for p in os.listdir(PACKETS)
                     if p.endswith('-packet.txt') and not p.startswith('TEMPLATE'))
    n = seeded = 0
    for name in packets:
        path = os.path.join(PACKETS, name)
        text = open(path, encoding='utf-8').read()
        slug = slug_of(path, text)
        if read_manifest(slug):
            continue
        day, src = assembled_date(path, text)
        n += 1
        if dry_run:
            out(f'would seed {slug} at {day} ({src}) · hash {body_hash(text)}')
            continue
        rc = retain(path, 'baseline', day=day, slug=slug, promote=False, out=out)
        if rc == 0:
            seeded += 1
    if dry_run:
        out(f'{n} state(s) would be seeded')
    else:
        out(f'{seeded} state(s) seeded into history')
    return 0


# --- reading the series ------------------------------------------------------

def show_log(slug, out=print):
    rows = read_manifest(slug)
    if not rows:
        out(f'no history for {slug}')
        return 1
    out(f'{slug} — {len(rows)} pass(es), '
        f'{len({r["capture"] for r in rows if r.get("capture")})} retained capture(s)')
    for r in rows:
        mark = '*' if r.get('stored') else ' '
        out(f'  {mark} {r["date"]}  {r["result"]:<9} {r["hash"]}  {r.get("capture", "-")}')
        for x in (r.get('header_changes') or {}).get('gone', []):
            out(f'      - {x[:120]}')
        for x in (r.get('header_changes') or {}).get('new', []):
            out(f'      + {x[:120]}')
    out('  (* = capture retained here; unmarked = sources unchanged, '
        'resolves to the capture named)')
    return 0


def verify(out=print):
    """Every manifest entry must resolve to a file whose body still hashes as recorded."""
    if not os.path.isdir(HISTORY):
        out('no history directory')
        return 1
    fails = 0
    checked = 0
    for slug in sorted(os.listdir(HISTORY)):
        d = os.path.join(HISTORY, slug)
        if not os.path.isdir(d):
            continue
        seen = set()
        for r in read_manifest(slug):
            cap = r.get('capture')
            if not cap:
                fails += 1
                out(f'{slug} {r["date"]}: entry names no capture')
                continue
            p = os.path.join(d, cap)
            if not os.path.exists(p):
                fails += 1
                out(f'{slug} {r["date"]}: missing capture {cap}')
                continue
            if r.get('stored'):
                h = body_hash(open(p, encoding='utf-8').read())
                if h != r['hash']:
                    fails += 1
                    out(f'{slug} {r["date"]}: {cap} hashes {h}, manifest says {r["hash"]}')
            seen.add(cap)
            checked += 1
        for f in os.listdir(d):
            if f.endswith('.txt') and f not in seen:
                fails += 1
                out(f'{slug}: {f} on disk but in no manifest entry')
    out(f'{fails} failure(s) across {checked} manifest entries')
    return 1 if fails else 0


# --- self-test ---------------------------------------------------------------

def self_test():
    import tempfile
    global ROOT, PACKETS, HISTORY
    ok = True

    def cap(sources, assembled='2026-01-01', notes='first capture'):
        head = (f'FIRST LINE OF PACKET\n\nSTATE: testland\nASSEMBLED: {assembled}\n'
                f'CAPTURE NOTES: {notes}\n\n')
        return head + '\n'.join(
            f'SOURCE {i+1}: Doc | {u} | source date: none | retrieved: {assembled}\n{b}'
            for i, (u, b) in enumerate(sources))

    a = cap([('https://x.gov/a', 'The child must remain in placement.')])
    # Same sources, different day and different capture notes: must hash alike.
    b = cap([('https://x.gov/a', 'The child must remain in placement.')],
            assembled='2026-02-01', notes='nightly rotation re-capture')
    c = cap([('https://x.gov/a', 'The child must remain in placement for 30 days.')],
            assembled='2026-03-01')
    # Same text as the capture before it, served from a moved address: the
    # document did not change, its location did.
    d = cap([('https://x.gov/moved', 'The child must remain in placement for 30 days.')],
            assembled='2026-04-01')

    if body_hash(a) != body_hash(b):
        print('FAIL: capture metadata leaked into the body hash'); ok = False
    if body_hash(a) == body_hash(c):
        print('FAIL: changed source text did not change the hash'); ok = False
    if body_hash(c) != body_hash(d):
        print('FAIL: a moved URL should not alter the body hash'); ok = False
    if source_urls(d) != ['https://x.gov/moved']:
        print('FAIL: URL extraction'); ok = False

    # --- transport strings -----------------------------------------------
    # The capture notes line capture.py actually writes, and one without it.
    with_recipe = ('CAPTURE NOTES:\n- Captured by tools/capture.py from '
                   'tools/recipes/maryland.json (recipe digest 20323db1cf2b). '
                   'Each source below was fetched by its recorded recipe.\n')
    hand = 'CAPTURE NOTES: Nightly rotation re-capture, pdftotext -layout.\n'

    got, note, err = transport_for(with_recipe, 'curl (browser user-agent)')
    if err or got != 'curl (browser user-agent), recipe 20323db1cf2b':
        print(f'FAIL: reference not written from the capture: {got!r} {err!r}'); ok = False
    if not note:
        print('FAIL: rewriting the operator transport was not reported'); ok = False

    got, _, err = transport_for(with_recipe, None)
    if err or got != 'recipe 20323db1cf2b':
        print(f'FAIL: bare recipe capture: {got!r} {err!r}'); ok = False

    # Already canonical: left exactly as the operator wrote it.
    already = 'curl, recipe 20323db1cf2b'
    got, note, err = transport_for(with_recipe, already)
    if err or got != already or note:
        print('FAIL: a canonical transport was not left alone'); ok = False

    # The 2026-08-29 defect, in its own words. Accurate English, wrong shape,
    # and previously accepted in silence.
    _, _, err = transport_for(with_recipe, 'recipe maryland (digest 20323db1cf2b)')
    if err:
        print('FAIL: the malformed 2026-08-29 phrasing should be repaired, not refused')
        ok = False
    got, _, _ = transport_for(with_recipe, 'recipe maryland (digest 20323db1cf2b)')
    if not RECIPE_TRANSPORT_RE.search(got or ''):
        print(f'FAIL: repaired transport still not recipe-era: {got!r}'); ok = False

    # A digest the capture does not declare is a provenance claim contradicted
    # by the file in hand.
    _, _, err = transport_for(with_recipe, 'curl, recipe ab0eef872761')
    if not err:
        print('FAIL: a mismatched digest was accepted'); ok = False

    # A recipe claim over a hand capture is unverifiable.
    _, _, err = transport_for(hand, 'curl, per the kansas recipe')
    if not err:
        print('FAIL: an unverifiable recipe claim was accepted'); ok = False

    # Hand captures keep taking free text.
    got, _, err = transport_for(hand, 'curl over plain HTTPS; pdftotext -raw')
    if err or got != 'curl over plain HTTPS; pdftotext -raw':
        print('FAIL: a hand capture lost its free-text transport'); ok = False

    # build-status.py is the consumer of this string and holds its own copy of
    # the pattern. Two regexes in two files drift; this fails when they do.
    bs = os.path.join(ROOT, 'tools', 'build-status.py')
    if os.path.exists(bs):
        import importlib.util
        spec = importlib.util.spec_from_file_location('_bs', bs)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f'FAIL: could not load build-status.py to cross-check: {e}'); ok = False
        else:
            # Board & Border has no capture.py and no recipes yet, so its
            # build-status.py holds no copy of the pattern and there is nothing
            # to cross-check. The guard is written as a condition rather than
            # deleted so that this test starts running by itself the day
            # recipes arrive here.
            if hasattr(mod, 'RECIPE_TRANSPORT_RE'):
                canon, _, _ = transport_for(with_recipe, 'curl')
                if not mod.RECIPE_TRANSPORT_RE.search(canon):
                    print('FAIL: build-status.py does not read the reference this tool writes')
                    ok = False
                if mod.RECIPE_TRANSPORT_RE.search('recipe maryland (digest 20323db1cf2b)'):
                    print('FAIL: build-status.py now accepts the malformed shape; '
                          'the repair path here is no longer needed'); ok = False

    with tempfile.TemporaryDirectory() as td:
        ROOT = td
        PACKETS = os.path.join(td, 'tools', 'packets')
        HISTORY = os.path.join(PACKETS, 'history')
        os.makedirs(PACKETS)
        quiet = lambda *a, **k: None

        def write(name, text):
            p = os.path.join(td, name)
            open(p, 'w', encoding='utf-8').write(text)
            return p

        retain(write('c1.txt', a), 'baseline', promote=False, out=quiet)
        retain(write('c2.txt', b), 'confirmed', out=quiet)
        rows = read_manifest('testland')
        if len(rows) != 2:
            print('FAIL: manifest should have two entries'); ok = False
        if rows[1]['stored']:
            print('FAIL: unchanged confirm stored a duplicate capture'); ok = False
        if rows[1]['capture'] != rows[0]['capture']:
            print('FAIL: unchanged confirm should resolve to the standing capture'); ok = False
        if not os.path.exists(os.path.join(PACKETS, 'testland-packet.txt')):
            print('FAIL: confirmed retention did not promote'); ok = False

        retain(write('c3.txt', c), 'drift', out=quiet)
        rows = read_manifest('testland')
        if not rows[2]['stored']:
            print('FAIL: drift capture was not retained'); ok = False
        if rows[2].get('supersedes') != rows[0]['capture']:
            print('FAIL: drift entry does not name what it supersedes'); ok = False
        promoted = open(os.path.join(PACKETS, 'testland-packet.txt'), encoding='utf-8').read()
        if promoted != b:
            print('FAIL: drift promoted over the current packet'); ok = False

        retain(write('c4.txt', d), 'confirmed', out=quiet)
        rows = read_manifest('testland')
        if rows[3]['stored']:
            print('FAIL: a moved URL alone should not store a duplicate body'); ok = False
        if not rows[3].get('header_changes'):
            print('FAIL: moved URL not recorded as a change'); ok = False

        files = [f for f in os.listdir(os.path.join(HISTORY, 'testland'))
                 if f.endswith('.txt')]
        if len(files) != 2:
            print(f'FAIL: expected 2 retained captures across 4 passes, got {len(files)}')
            ok = False
        if verify(out=quiet) != 0:
            print('FAIL: verify rejected a well-formed history'); ok = False

    print('self-test: ' + ('all checks passed' if ok else 'FAILURES'))
    return 0 if ok else 1


# --- cli ---------------------------------------------------------------------

def main(argv):
    args = argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        return 2
    if args == ['--self-test']:
        return self_test()
    if args[0] == '--verify':
        return verify()
    if args[0] == '--backfill':
        return backfill(dry_run='--dry-run' in args)
    if args[0] == '--log':
        if len(args) < 2:
            print('--log needs a state slug', file=sys.stderr)
            return 2
        return show_log(args[1])

    capture = args[0]
    opts = {}
    i = 1
    while i < len(args):
        a = args[i]
        if a == '--no-promote':
            opts['promote'] = False
            i += 1
            continue
        if a.startswith('--') and i + 1 < len(args):
            opts[a[2:].replace('-', '_')] = args[i + 1]
            i += 2
            continue
        print(f'unexpected argument: {a}', file=sys.stderr)
        return 2
    if 'state' in opts:
        opts['slug'] = opts.pop('state')
    if 'date' in opts:
        opts['day'] = opts.pop('date')
    if 'result' not in opts:
        print('--result is required (confirmed, drift, rebuild, baseline)', file=sys.stderr)
        return 2
    return retain(capture, opts.pop('result'), **opts)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
