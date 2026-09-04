#!/usr/bin/env python3
"""Shared primitives for the portfolio's capture.py copies: the poppler build
pin, the running-header filter, table-cell link targets, and the fetched-
artifact id. Import this rather than re-implementing any of the four.

Why this file exists. On 2026-09-03, sped-safeguards found that the poppler
build was an undeclared input to every captured PDF body: the same file, same
recipe, same digest, same pinned pdftotext flags, produced a cleanly spaced
body under one poppler build and a body full of fused words under another.
Four review passes across three days misread the difference as source drift,
a filter defect, and a bad install; one wrong drift finding was logged,
queued, anchored and pushed before anyone checked it. The same session found
that table-row flattening in extract_html ran before the link-emission pass,
so the `links` recipe field silently did nothing for any table in any source
-- a gap North Carolina's own recipe notes had correctly diagnosed and could
not fix, because the fix was not available at the recipe layer.

Both defects existed because four other copies of capture.py each carried
their own implementation of the same logic, none of them fixed, none of them
even aware the others existed. This file is the fix, in one place, so the
next one only has to happen once.

What is deliberately NOT here: recipe schema, extraction scope logic, HTML
parsing (extract_html itself), fetch transport, and anything else that has
already diverged across the five repos for reasons specific to each. Only the
four primitives that turned out to be dangerous when divergent are shared;
everything else stays local to each repo, on purpose.

Distribution. This file's canonical copy lives in field-assembly-standard.
Each consuming repo keeps a local copy at tools/capture-core.py, loaded via
importlib.util the way this codebase already loads cross-file modules (see
retain-packet.py's build-status.py cross-check). Copies are kept in sync by
tools/capture-core-sync.py in field-assembly-standard, which reports drift and
writes only on --push -- the same report-first idiom as routine-sync.py, for
the same reason: a tool that could silently overwrite would eventually
overwrite the wrong thing.

Usage as a library:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'capture_core', os.path.join(ROOT, 'tools', 'capture-core.py'))
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    core.require_poppler()
    text = core.extract_pdf(blob, 'pdftotext-raw')

Usage as a script:
    python3 tools/capture-core.py --self-test

Exit codes: 0 clean, 1 self-test failure.
"""

import hashlib
import os
import re
import subprocess
import sys
import tempfile


# --- the poppler / pdfplumber pin --------------------------------------------
#
# The binary is an input, and until 2026-09-03 no copy of capture.py declared
# it. Montana is the proof: the same PDF -- artifact sha256:0dd22c7ba3247581,
# byte-identical across three fetches -- run through the same recipe at the
# same digest with the same pinned pdftotext flags produced a clean, properly
# spaced body under poppler 26.07.0 and a body full of fused words under
# 22.02.0 ("theirbiological oradoptive parent", "RighttoParticipation").
# Deterministic software, identical inputs, two different texts: something
# undeclared had changed, and the only thing left was poppler.
#
# So the version is pinned and checked. A capture on the wrong build does not
# warn and continue -- it stops. Changing this pin re-baselines every
# PDF-sourced packet and requires re-cutting any quotation that rests on one;
# it is a portfolio decision, not a convenience, and each repo pins its own
# value below rather than sharing one, because a change here should never
# silently re-baseline a repo nobody meant to touch.
DEFAULT_POPPLER_PIN = "26.07.0"
DEFAULT_PDFPLUMBER_PIN = "0.11.10"

# pdftotext flags. -nopgbrk was removed on 2026-09-03 from every mode: it
# suppresses the form feed, and a suppressed form feed is not a page break
# rendered harmless -- it is a page break deleted, welding the running head to
# the prose it interrupted with no separator at all. Keeping the form feed
# costs nothing downstream: it is the first thing the running-header filter
# below cuts on, and ordinary whitespace collapse absorbs the rest.
PDFTOTEXT_RAW = ["-raw", "-enc", "UTF-8"]
PDFTOTEXT_LAYOUT = ["-layout", "-enc", "UTF-8"]
PDFTOTEXT_PLAIN = ["-enc", "UTF-8"]
PDFTOTEXT_FLAGS = {
    "pdftotext-raw": PDFTOTEXT_RAW,
    "pdftotext-layout": PDFTOTEXT_LAYOUT,
    "pdftotext-plain": PDFTOTEXT_PLAIN,
}

POPPLER_VERSION_RE = re.compile(r'pdftotext\s+version\s+(\S+)')


def poppler_version():
    """The installed pdftotext's version string, or None if it cannot be read.

    pdftotext -v writes to stderr and exits non-zero on some builds, so both
    streams are read and the exit code is ignored."""
    try:
        r = subprocess.run(['pdftotext', '-v'], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    out = (r.stdout + r.stderr).decode('utf-8', 'replace')
    m = POPPLER_VERSION_RE.search(out)
    return m.group(1) if m else None


def require_poppler(pin=DEFAULT_POPPLER_PIN):
    """Stop unless the installed poppler is the pinned one.

    Pass the calling repo's own pin if it differs from the default -- each
    repo's pin is its own decision, re-baselining is per repo, and this
    function must never let one repo's pin silently govern another's."""
    got = poppler_version()
    if got is None:
        raise RuntimeError(
            'cannot read pdftotext version; poppler ' + pin +
            ' is required for PDF extraction and the binary must be on PATH')
    if got != pin:
        raise RuntimeError(
            f'poppler {got} is installed; this project pins {pin} for PDF '
            f'extraction. The build is an input to the captured text -- the '
            f'same file under a different poppler produces a different body, '
            f'which reads downstream as source drift. Capture on the pinned '
            f'build, or change the pin deliberately and re-baseline every '
            f'PDF-sourced packet.')
    return got


def require_pdfplumber(pin=DEFAULT_PDFPLUMBER_PIN):
    """Same rule as require_poppler, for the pdfplumber extractor."""
    import pdfplumber
    got = getattr(pdfplumber, '__version__', None)
    if got != pin:
        raise RuntimeError(
            f'pdfplumber {got} is installed; this project pins {pin}. See '
            f'require_poppler for why the extractor version is an input and '
            f'not an environment detail.')
    return got


def extractor_build(mode, poppler_pin=DEFAULT_POPPLER_PIN,
                    pdfplumber_pin=DEFAULT_PDFPLUMBER_PIN):
    """The pinned build string to record in a packet's capture notes."""
    return (f'pdfplumber {pdfplumber_pin}' if mode == 'pdfplumber'
            else f'poppler {poppler_pin}')


def extract_pdf(blob, mode, pages=None, poppler_pin=DEFAULT_POPPLER_PIN,
                pdfplumber_pin=DEFAULT_PDFPLUMBER_PIN):
    """Text from a PDF, optionally from an inclusive page range only, on the
    pinned build. Raises if the installed build does not match the pin."""
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, 'in.pdf')
        open(p, 'wb').write(blob)
        if mode == 'pdfplumber':
            require_pdfplumber(pdfplumber_pin)
            import pdfplumber
            with pdfplumber.open(p) as pdf:
                sel = pdf.pages if not pages else pdf.pages[pages[0] - 1:pages[1]]
                return '\n'.join((pg.extract_text() or '') for pg in sel)
        require_poppler(poppler_pin)
        flags = PDFTOTEXT_FLAGS[mode]
        if pages:
            flags = flags + ['-f', str(pages[0]), '-l', str(pages[1])]
        r = subprocess.run(['pdftotext'] + flags + [p, '-'],
                           capture_output=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError('pdftotext: '
                               + r.stderr.decode('utf-8', 'replace').strip())
        return r.stdout.decode('utf-8', 'replace')


# --- the fetched-artifact id --------------------------------------------------

def artifact_id(blob, supplied=False):
    """A short, stable id for exactly what was fetched, hashed before any
    extraction touches it. Two captures of one source recording the same id
    are proof the raw input was byte-identical -- any difference in their
    extracted text from that point on is the extractor's doing, not the
    source's. This is what a body-hash comparison alone cannot prove, and it
    is what a retention layer's short-packet regression guard needs to tell a
    legitimate re-extraction apart from a filter quietly dropping text."""
    if isinstance(blob, str):
        blob = blob.encode('utf-8', 'replace')
    return (('supplied:' if supplied else 'sha256:')
            + hashlib.sha256(blob).hexdigest()[:16])


# --- the running-header filter ------------------------------------------------

WRAP_FLOOR = 40      # below this a document has no column worth speaking of
WRAP_SLACK = 12      # how far short of the column a line may fall and still be full
RUNHEAD_MIN_REPEATS = 3  # a running head recurs; a short sentence does not
RUNHEAD_BREAK = '\x0c'   # the page break itself, which is where a head begins
RUNHEAD_BREAK_MIN_CHARS = 3  # the floor for a line at a page edge
RUNHEAD_EDGE_LINES = 2       # how many lines deep a head or footer may reach


def wrap_width(t):
    """The column width a document was set to, derived from the document
    itself: the 90th percentile of non-blank line lengths, less slack for the
    word that did not fit, rounded to the nearest five."""
    lens = sorted(len(l.rstrip()) for l in t.split('\n') if l.strip())
    if not lens:
        return WRAP_FLOOR
    p90 = lens[min(len(lens) - 1, int(len(lens) * 0.9))]
    return max(WRAP_FLOOR, 5 * round((p90 - WRAP_SLACK) / 5))


def f_strip_running_headers(t):
    """Drop a repeated short line at a page edge -- a running head or footer --
    without touching a repeated short line anywhere else on the page.

    The text is first cut at every form feed (the page break itself), which
    puts a running head fused mid-sentence onto its own line before the tests
    below ever see it -- pdftotext does not always emit a head on its own
    line, and a head welded to prose is long and unique, so it survives any
    length- or repeat-based test that runs before the cut.

    Then, three conditions, all required: the line must be shorter than the
    document's own column width (a head is short; prose is not), it must
    contain a letter (numeric-only lines stay with a page-number filter),
    and, with digit runs folded to '#' so a page number does not make every
    occurrence unique, it must recur RUNHEAD_MIN_REPEATS times. Only a line
    within RUNHEAD_EDGE_LINES non-blank lines of a page edge is eligible at
    all -- a running head is at a page boundary by definition, and a repeated
    short line in the middle of a page is content, not header. This edge
    restriction is what keeps a repeated contact block (a mailing address, a
    phone number printed at the top of every page) from being read as a
    running head and silently dropped -- the earlier version of this filter,
    which counted repeats anywhere in the document, ate exactly that from a
    Texas notice, and CLAUDE.md's contact-node rule exists to prevent it."""
    pages = [block.split('\n') for block in t.split(RUNHEAD_BREAK)]
    lines, at_edge = [], []
    for page in pages:
        live = [i for i, l in enumerate(page) if l.strip()]
        edge = set(live[:RUNHEAD_EDGE_LINES]) | set(live[-RUNHEAD_EDGE_LINES:])
        for i, line in enumerate(page):
            lines.append(line)
            at_edge.append(i in edge)
    if len(pages) == 1:
        at_edge = [False] * len(lines)
    width = wrap_width('\n'.join(lines))

    def candidate(line, edge=False):
        s = line.strip()
        if not edge:
            return False
        return (s and len(s) < width and len(s) >= RUNHEAD_BREAK_MIN_CHARS
                and re.search(r'[A-Za-z]', s))

    def key(line):
        return re.sub(r'\d+', '#', ' '.join(line.split()))

    counts = {}
    for line, edge in zip(lines, at_edge):
        if candidate(line, edge):
            k = key(line)
            counts[k] = counts.get(k, 0) + 1
    drop = {k for k, n in counts.items() if n >= RUNHEAD_MIN_REPEATS}
    return '\n'.join(l for l, edge in zip(lines, at_edge)
                     if not (candidate(l, edge) and key(l) in drop))


def form_feed_to_linebreak(t):
    """Convert any form feed a filter chain left behind into a plain line
    break, so no packet carries a control character. Call this last, after
    f_strip_running_headers and any other filter that reads RUNHEAD_BREAK."""
    return t.replace(RUNHEAD_BREAK, '\n')


# --- Cloudflare email obfuscation ----------------------------------------------
#
# Promoted here 2026-09-03 from sped-safeguards and licensure mobility, where two
# byte-identical copies had grown independently. The scan that prompted it is
# worth recording, because it is as clean a natural experiment as this portfolio
# is likely to produce: the two repos carrying this function held zero
# obfuscation placeholders in their packet bodies, and the two without it held
# 76 across 11 packets. The function accounts for the whole difference.
#
# What makes this worth sharing rather than duplicating is that the failure is
# silent in a specific way no gate catches. The fidelity checker requires every
# address a page publishes to appear in its packet, not the reverse -- so a
# packet full of placeholders passes every check while quietly being unable to
# support any contact at all. The damage is to what a page can say, not to what
# it says, and nothing reports it. Room & Recourse's Alabama packet is the case
# that shows the cost: "For nursing home complaints, email us at [email
# protected]" -- the complaint address, missing from the page whose readers are
# families trying to complain about a facility.


def decode_cfemail(hexstr):
    """Plaintext of a Cloudflare-obfuscated email (data-cfemail attribute).

    The encoding is a one-byte XOR: the first byte is the key, each later byte
    XORs against it. The plaintext is therefore genuinely present in the served
    bytes, and decoding it is extraction in the same category as reading a
    __NEXT_DATA__ island -- not interpretation. Without this, a capture carries
    '[email protected]', which is Cloudflare's placeholder standing in for text
    the publisher published. Maryland is the case that forced it originally:
    mbon.maryland.gov publishes no email address as visible text anywhere, so a
    capture without this decode holds not one @maryland.gov string and cannot
    vouch for a contact the page prints."""
    b = bytes.fromhex(hexstr)
    return ''.join(chr(c ^ b[0]) for c in b[1:])


def decode_cfemail_nodes(soup):
    """Replace every data-cfemail node in a parsed document with its address.

    Callers differ in how they build the soup and what they do afterwards, so
    this takes the parsed document rather than markup. A malformed attribute is
    left exactly as the page rendered it: a capture that guesses at a broken
    encoding is worse than one that records what was served.

    Unconditional by design, not opt-in. Unlike the links field, this does not
    add anything the publisher did not publish -- it renders text that is
    already in the served bytes and would otherwise reach the packet as a
    placeholder."""
    from bs4 import NavigableString
    n = 0
    for cf in soup.find_all(attrs={'data-cfemail': True}):
        try:
            cf.replace_with(NavigableString(decode_cfemail(cf['data-cfemail'])))
            n += 1
        except (ValueError, IndexError, KeyError):
            pass  # a malformed attribute is left as the page rendered it
    return n


# --- table-cell link targets ---------------------------------------------------
#
# These three operate on already-parsed bs4 Tag/anchor objects; this module
# does not import bs4 itself, so a caller's own HTML extractor stays free to
# parse however it already does and just calls these at the right point.

def link_target(a):
    """The citable target of an anchor, or None if it has none worth emitting.

    mailto: is unwrapped to the bare address, because that is the form a page
    prints and a fidelity checker looks for; anything that is not http,
    https or mailto is not a target."""
    href = (a.get('href') or '').strip()
    if href.startswith('mailto:'):
        return href[7:].split('?')[0]
    if href.startswith(('http://', 'https://')):
        return href
    return None


def link_is_redundant(a, target):
    """True when the anchor already prints its own target as its visible text.

    Emitting the target anyway is what broke a working quote in North
    Carolina's recipe: 'Requests for mediation should be emailed to
    mediation@dpi.nc.gov.' has that address as its own anchor text, so
    appending the target landed the annotation between the address and its
    period, turning an exact match into a failure. The address was already in
    the text -- the anchor text put it there -- so a second copy added no fact
    and cost a quotation."""
    seen = ' '.join((a.get_text(' ', strip=True) or '').split()).casefold()
    if not seen:
        return False
    t = target.casefold()
    return seen == t or seen.rstrip('/') == t.rstrip('/')


def cell_text(c, links=False):
    """One flattened table cell's text, with its own link targets appended
    when links is true.

    Table-row flattening runs before an HTML extractor's own link-emission
    pass in every copy of capture.py surveyed on 2026-09-03, so a fact stated
    only as an href inside a <td> -- North Carolina publishes two consultants'
    email addresses and a hostname exactly this way -- was unreachable
    regardless of a recipe's links setting. Call this instead of a bare
    get_text() when flattening a table row, and the fact is reachable."""
    txt = ' '.join(c.get_text(' ', strip=True).split())
    if not links:
        return txt
    extras = []
    for a in c.find_all('a'):
        target = link_target(a)
        if target is None or link_is_redundant(a, target):
            continue
        bit = f'<{target}>'
        if bit not in extras:
            extras.append(bit)
    return ' '.join([txt] + extras).strip() if extras else txt


# --- comparing a fresh capture against the packet it would replace ------------
#
# Added 2026-09-03, after a day in which four separate defects were found and
# not one of them made anything fail. A source page returned HTTP 200 with its
# content replaced by a pointer elsewhere; a board's email addresses captured as
# obfuscation placeholders; a page's wording vanished when a recipe consolidated
# two transports into one; and a capture came back a source short because of a
# transient fetch error, announcing it only in its own count. Every gate in the
# portfolio passed through all of it, because the gates check that a page traces
# to its packet, and all four defects damaged the packet instead.
#
# So this compares the capture about to be promoted against the packet it would
# replace, and it is deliberately not a pass/fail gate. It classifies, and a
# human reads the classification:
#
#   gone      a source in the old packet is absent from the new one
#   new       a source in the new packet was not in the old one
#   same      byte-identical
#   respaced  identical once whitespace is collapsed -- the signature of the
#             -nopgbrk correction, and of nothing else
#   grew      content added; ordinary drift, or a decode recovering text
#   shrank    content lost -- the one that always deserves a read
#
# "shrank" is a prompt, not a verdict, and today taught why. Decoding an
# obfuscated address shortens the text ("[email protected]" is eighteen
# characters, "otl@uvu.edu" is eleven), so a correct repair reports as loss. A
# byte-length heuristic cannot tell recovery from loss. The diff can, which is
# why this returns the numbers and leaves the judgement where it belongs.


# The header shape is not one shape. All four collections' check-fidelity.py
# already agree on this pattern, and it is adopted here verbatim rather than
# re-derived: a source header is `SOURCE n` alone on its line, or `SOURCE n:`,
# or `SOURCE n |`. Three collections write the colon; two sped-safeguards
# packets (nebraska, new-hampshire) write the pipe; new-mexico and the language
# template write the bare form.
#
# The first draft of this function required a colon. It returned an empty dict
# for the pipe form and dropped every source those packets hold, which the
# self-test did not catch because the fixtures used the colon. It was found by
# diffing this parser against the existing checkers across all 299 packets in
# the portfolio -- which is the check worth repeating after any change here.
SOURCE_HEADER_RE = re.compile(r'^SOURCE\s*(\d+)\s*(?:[|:]|$)', re.M)
END_SOURCE_RE = re.compile(r'^(?:END SOURCE\b|END OF PACKET\b).*$', re.M)
RETRIEVED_RE = re.compile(r'(retrieved:\s*)\d{4}-\d{2}-\d{2}', re.I)


def packet_sources(text, with_headers=False):
    """{n: body} for every SOURCE block in a packet. The canonical reader.

    Use this rather than writing a parser. Every ad-hoc one written against a
    packet on 2026-09-03 was wrong, and each was wrong differently:

      * one matched `RETRIEVED:` where the format writes `retrieved:`, and
        reported twenty-five jurisdictions as content drift when the only
        difference was a date;
      * one ended a source at the next SOURCE header without checking for an
        END SOURCE marker first, and mis-attributed a quotation to the wrong
        document, nearly filing a drift finding against a source that had not
        moved;
      * one ended a source at END SOURCE without falling back, and in a packet
        with no such markers swallowed nine following sources into a supplement
        that was meant to hold one -- 139,022 characters instead of 3,613.

    The formats are not per repo, which is the trap. Measured across all four
    collections on 2026-09-03: sped-safeguards has 117 packets carrying SOURCE
    headers and 31 carrying END SOURCE; licensure mobility 58 and 9; gathered
    work 73 and none; transfer-safeguards 47 and 43. Both shapes occur inside
    the same repo, so a reader must decide per source, not per collection.

    A block therefore ends at its own END SOURCE line when one follows it before
    the next header, and at the next header otherwise. Text before the first
    SOURCE header -- the canary, capture notes, pending list -- is never
    returned: a packet header describes, and only a source body evidences.

    with_headers=True returns {n: (header_line, body)} for callers that need to
    read a source's URL or retrieval date.
    """
    out = {}
    heads = list(SOURCE_HEADER_RE.finditer(text))
    for i, m in enumerate(heads):
        # The pattern stops at the delimiter, so the header line runs from the
        # match to the end of that line; the body begins on the next one.
        eol = text.find('\n', m.start())
        eol = len(text) if eol == -1 else eol
        header = text[m.start():eol]
        stop = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        block = text[eol:stop]
        e = END_SOURCE_RE.search(block)
        if e:
            block = block[:e.start()]
        body = block.strip('\n')
        out[int(m.group(1))] = (header, body) if with_headers else body
    return out


def packet_header(text):
    """Everything before the first SOURCE header: canary, notes, pending list.

    Returned separately so a caller can read it deliberately. It is description,
    never evidence, and must not be searched for quotations -- a capture note
    that mentions an obfuscation placeholder is not a packet carrying one, and
    counting it as one produced a wrong portfolio-wide tally on 2026-09-03.
    """
    m = SOURCE_HEADER_RE.search(text)
    return text[:m.start()] if m else text


def normalize_retrieval_dates(text, placeholder='retrieved: X'):
    """Retrieval dates flattened, case-insensitively, for comparing captures.

    Two captures of an unchanged source differ in exactly this one field. A
    comparison that does not flatten it reports every source as changed; one
    that flattens it case-sensitively reports every source in a repo using the
    other casing as changed, which is the first bug in the list above.
    """
    return RETRIEVED_RE.sub(lambda m: m.group(1) + 'X', text)


def compare_capture(old_text, new_text):
    """Classify what a fresh capture does to each source of a packet.

    Returns {'gone': [...], 'new': [...], 'same': [...], 'respaced': [...],
    'grew': [(n, before, after)], 'shrank': [(n, before, after)]}, where the
    counts are characters with whitespace collapsed. Reports; decides nothing.
    """
    A, B = packet_sources(old_text), packet_sources(new_text)
    r = {'gone': sorted(set(A) - set(B)), 'new': sorted(set(B) - set(A)),
         'same': [], 'respaced': [], 'grew': [], 'shrank': []}
    for n in sorted(set(A) & set(B)):
        a, b = A[n], B[n]
        if a == b:
            r['same'].append(n); continue
        ca, cb = re.sub(r'\s+', '', a), re.sub(r'\s+', '', b)
        if ca == cb:
            r['respaced'].append(n)
        elif len(cb) >= len(ca):
            r['grew'].append((n, len(ca), len(cb)))
        else:
            r['shrank'].append((n, len(ca), len(cb)))
    return r


def capture_report(cmp, label=''):
    """One-line-per-finding rendering of compare_capture, quietest first."""
    lines = []
    if cmp['gone']:
        lines.append(f"  SOURCE GONE     {cmp['gone']} -- present in the packet, "
                     f"absent from this capture")
    if cmp['new']:
        lines.append(f"  source new      {cmp['new']}")
    for n, a, b in cmp['shrank']:
        lines.append(f"  SHRANK          source {n}: {a} -> {b} chars -- read the diff")
    for n, a, b in cmp['grew']:
        lines.append(f"  grew            source {n}: {a} -> {b} chars")
    if cmp['respaced']:
        lines.append(f"  respaced only   {cmp['respaced']} -- identical but for whitespace")
    if cmp['same']:
        lines.append(f"  unchanged       {cmp['same']}")
    head = f'capture comparison{" for " + label if label else ""}:'
    return head + '\n' + ('\n'.join(lines) if lines else '  (no sources)')


def capture_needs_review(cmp):
    """True when something in this comparison a human should look at."""
    return bool(cmp['gone'] or cmp['shrank'])


# --- self-test -----------------------------------------------------------------

def self_test():
    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print(f'FAIL: {msg}')
            ok = False

    check(artifact_id(b'abc') == artifact_id(b'abc'), 'artifact_id is not stable')
    check(artifact_id(b'abc') != artifact_id(b'abd'),
          'different bytes hashed to the same artifact id')
    check(artifact_id('abc') == artifact_id(b'abc'),
          'str and the same bytes, utf-8 encoded, hashed differently')
    check(artifact_id(b'abc', supplied=True) != artifact_id(b'abc', supplied=False),
          'supplied and fetched bytes are not distinguished')
    check(artifact_id(b'abc').startswith('sha256:'), 'fetched artifact id has the wrong prefix')
    check(artifact_id(b'abc', supplied=True).startswith('supplied:'),
          'supplied artifact id has the wrong prefix')
    check(len(artifact_id(b'abc').split(':')[1]) == 16, 'artifact id is not 16 hex digits')

    # Cloudflare email obfuscation. The vector is the address Maryland's board
    # publishes only as an attribute, and the one this decode was written for.
    check(decode_cfemail('8dc5e8ecffe4e3eaa3c2ebebe4eee8cde9eea3eae2fb')
          == 'Hearing.Office@dc.gov', 'cfemail XOR decode is wrong')
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        BeautifulSoup = None
    if BeautifulSoup is not None:
        cf = ('<div><a href="/cdn-cgi/l/email-protection#8dc5e8ecffe4e3eaa3c2eb'
              'ebe4eee8cde9eea3eae2fb"><span class="__cf_email__" '
              'data-cfemail="8dc5e8ecffe4e3eaa3c2ebebe4eee8cde9eea3eae2fb">'
              '[email&#160;protected]</span></a></div>')
        soup = BeautifulSoup(cf, 'html.parser')
        n = decode_cfemail_nodes(soup)
        txt = soup.get_text()
        check(n == 1, 'decode_cfemail_nodes did not report the node it replaced')
        check('Hearing.Office@dc.gov' in txt,
              'data-cfemail did not decode to the published address')
        check('email' not in txt.replace('Hearing.Office@dc.gov', ''),
              "Cloudflare's placeholder text survived the decode")
        # A broken attribute must not raise and must not be guessed at: a
        # capture that invents an address is worse than one holding a
        # placeholder, because the placeholder is visibly not an address.
        bad = BeautifulSoup('<div><span data-cfemail="zz">x</span></div>',
                            'html.parser')
        check(decode_cfemail_nodes(bad) == 0,
              'a malformed data-cfemail was counted as decoded')
        check(bad.get_text().strip() == 'x',
              'a malformed data-cfemail raised or was rewritten')

    narrow = '\n'.join(['short line'] * 5)
    wide = '\n'.join(['a much longer line than the ones in the narrow '
                      'document, well past any rounding boundary'] * 5)
    check(wrap_width(narrow) < wrap_width(wide),
          'wrap_width did not respond to the document')
    check(wrap_width('') == WRAP_FLOOR, 'an empty document did not floor to WRAP_FLOOR')

    # Fixtures below are the ones proven in sped-safeguards' own capture.py
    # self-test, reused rather than re-derived.
    page = ('(a) File a due process\n'
            '\x0cPart B Procedural Safeguards Notice 4\n'
            'complaint to request a hearing to show that its evaluation\n'
            'of your child is appropriate; or\n'
            '\x0cPart B Procedural Safeguards Notice 5\n'
            '(b) Provide an independent educational evaluation.\n'
            '\x0cPart B Procedural Safeguards Notice 6\n'
            'A short unique line.\n')
    stripped = f_strip_running_headers(page)
    check('Part B Procedural Safeguards Notice' not in stripped,
          'strip-running-headers left a running head behind')
    check(re.search(r'\(a\) File a due process\s*\ncomplaint to request a hearing',
                    stripped),
          'strip-running-headers did not restore the interrupted sentence')
    check('A short unique line.' in stripped,
          'strip-running-headers dropped a short line that appears only once')

    contact = ''.join(
        f'\x0cRunning Head {n}\nbody text for page {n} which is long enough to '
        f'set a column\nTexas Education Agency\n1701 N. Congress Avenue\n'
        f'more body text on page {n} carrying the column a little further\n'
        f'page {n} footer line\n' for n in (1, 2, 3, 4))
    kept = f_strip_running_headers(contact)
    check('Running Head' not in kept,
          'strip-running-headers left a head at the page edge')
    check(kept.count('1701 N. Congress Avenue') == 4,
          'strip-running-headers ate a repeated contact block in mid-page')
    check(kept.count('Texas Education Agency') == 4,
          'strip-running-headers ate a repeated agency name in mid-page')

    twice = '\x0cHeading here again\nbody\n\x0cHeading here again\nbody\n'
    check(f_strip_running_headers(twice).count('Heading here again') == 2,
          'strip-running-headers dropped a line repeating fewer than three times')

    fused = ('one two three four five six seven eight nine ten eleven twelve\n'
             'either: (a) File a due process\x0cPart B Safeguards Notice 4\n'
             'complaint to request a hearing to show that its evaluation\n'
             'of your child is appropriate; or\x0cPart B Safeguards Notice 5\n'
             '(b) Provide an independent educational evaluation at public\n'
             'expense, unless the school district demonstrates in a hearing\n'
             'that the evaluation of your child that you obtained did not\x0c'
             'Part B Safeguards Notice 6\n'
             'meet the school district criteria.\n')
    fixed = f_strip_running_headers(fused)
    check('Part B Safeguards Notice' not in fixed,
          'strip-running-headers left a head fused to a line by a form feed')
    check('(a) File a due process\ncomplaint to request a hearing' in fixed,
          'strip-running-headers did not restore a sentence cut by a form feed')

    check('\x0c' not in form_feed_to_linebreak('a\x0cb'),
          'a form feed survived the conversion')
    check(form_feed_to_linebreak('a\x0cb') == 'a\nb',
          'form feed was not converted to a plain line break')
    check(form_feed_to_linebreak('a\nb') == 'a\nb',
          'a document with no form feed was altered')

    class FakeAnchor:
        def __init__(self, href, text):
            self.href, self.text = href, text
        def get(self, k, default=None):
            return self.href if k == 'href' else default
        def get_text(self, sep=' ', strip=True):
            return self.text

    class FakeCell:
        def __init__(self, text, anchors):
            self.text, self.anchors = text, anchors
        def get_text(self, sep=' ', strip=True):
            return self.text
        def find_all(self, name):
            return self.anchors

    a1 = FakeAnchor('mailto:johanna.lynch@dpi.nc.gov', 'Johanna Lynch')
    check(link_target(a1) == 'johanna.lynch@dpi.nc.gov',
          'a mailto target was not unwrapped to the bare address')
    check(not link_is_redundant(a1, link_target(a1)),
          'an anchor named for a person was called redundant')

    a2 = FakeAnchor('mailto:mediation@dpi.nc.gov', 'mediation@dpi.nc.gov')
    check(link_is_redundant(a2, link_target(a2)),
          'a self-naming anchor was not recognized as redundant')

    a3 = FakeAnchor('/relative/path', 'local')
    check(link_target(a3) is None, 'a relative href was treated as a target')

    cell = FakeCell('Mediation', [a1])
    check(cell_text(cell, links=False) == 'Mediation',
          'cell_text emitted a link target when links was off')
    check(cell_text(cell, links=True) == 'Mediation <johanna.lynch@dpi.nc.gov>',
          'cell_text did not reach an anchor inside a table cell')

    dup_cell = FakeCell('mediation@dpi.nc.gov', [a2])
    check(cell_text(dup_cell, links=True) == 'mediation@dpi.nc.gov',
          'cell_text duplicated a self-naming address')


    # packet_sources: the three ad-hoc parsers of 2026-09-03, each as a case.
    # These are regression tests for mistakes actually made, not hypotheticals.
    #
    # (a) END SOURCE present -- the block must stop there, not at the next
    #     header, or a supplement built from one source swallows the rest.
    marked = ('CANARY\nCAPTURE NOTES: header text, never evidence\n\n'
              'SOURCE 1: A | u | retrieved: 2026-01-01\nalpha\nEND SOURCE 1\n\n'
              'SOURCE 2: B | u | retrieved: 2026-01-01\nbeta\nEND SOURCE 2\n')
    m = packet_sources(marked)
    check(m == {1: 'alpha', 2: 'beta'}, f'END SOURCE form parsed wrong: {m!r}')
    # (b) no END SOURCE anywhere -- the block must stop at the next header.
    plain = ('CANARY\nCAPTURE NOTES: header text\n\n'
             'SOURCE 1: A | u | retrieved: 2026-01-01\nalpha\n\n'
             'SOURCE 2: B | u | retrieved: 2026-01-01\nbeta\n')
    p2 = packet_sources(plain)
    check(p2 == {1: 'alpha', 2: 'beta'}, f'unmarked form parsed wrong: {p2!r}')
    check('SOURCE 2' not in p2[1],
          'a source without an END marker swallowed the one after it')
    # (c) the pipe-delimited header shape, which two sped-safeguards packets
    #     use. A reader assuming the colon returns {} and drops everything.
    piped = ('SOURCE 1 | A | u | retrieved 2026-01-01\nalpha\nEND SOURCE 1\n\n'
             'SOURCE 2 | B | u | retrieved 2026-01-01\nbeta\nEND SOURCE 2\n')
    check(packet_sources(piped) == {1: 'alpha', 2: 'beta'},
          'the pipe-delimited SOURCE header shape was not parsed')
    # (c) mixed within one packet, which is the shape that actually occurs.
    mixed = ('SOURCE 1: A | u | retrieved: 2026-01-01\nalpha\nEND SOURCE 1\n\n'
             'SOURCE 2: B | u | retrieved: 2026-01-01\nbeta\n')
    check(packet_sources(mixed) == {1: 'alpha', 2: 'beta'},
          'a packet mixing both forms parsed wrong')
    # The closing trailer is structure too, and a last source with no END
    # SOURCE marker must not swallow it -- six supplements written on
    # 2026-09-03 did exactly that.
    trailer = ('SOURCE 1: A | u | retrieved: 2026-01-01\nalpha\n\n'
               'END OF PACKET — 1 source\n')
    check(packet_sources(trailer) == {1: 'alpha'},
          'the END OF PACKET trailer was returned as source text')
    # The header block is description and must never be returned as evidence.
    check('CAPTURE NOTES' not in ''.join(packet_sources(marked).values()),
          'packet_sources returned capture notes as source text')
    check('CAPTURE NOTES' in packet_header(marked),
          'packet_header lost the capture notes')
    check(packet_header('no headers here') == 'no headers here',
          'packet_header on a headerless packet did not return it whole')
    check(packet_sources('nothing here') == {},
          'packet_sources invented a source in a packet with none')
    # with_headers exposes the header line for callers needing url or date.
    wh = packet_sources(marked, with_headers=True)
    check(wh[1][0].startswith('SOURCE 1:') and wh[1][1] == 'alpha',
          'with_headers did not return (header, body)')
    # Retrieval-date flattening is case-insensitive: the casing bug that
    # reported twenty-five unchanged jurisdictions as content drift.
    for form in ('retrieved: 2026-01-01', 'RETRIEVED: 2026-01-01',
                 'Retrieved: 2026-01-01'):
        out = normalize_retrieval_dates('x | ' + form)
        check(out.endswith('X'), f'retrieval date not flattened for {form!r}')
    check(normalize_retrieval_dates('retrieved: 2026-01-01').lower()
          == normalize_retrieval_dates('RETRIEVED: 2026-01-01').lower(),
          'two casings of the same date did not flatten to the same text')
    check('2026-01-01' not in normalize_retrieval_dates('RETRIEVED: 2026-01-01'),
          'an upper-case retrieval date survived flattening')

    # compare_capture: the four defects of 2026-09-03, each as a case.
    def _pk(*blocks):
        out = ['CANARY', 'CAPTURE NOTES: header text is not evidence']
        for n, body in blocks:
            out += [f'SOURCE {n}: t | u | retrieved: 2026-01-01', body, f'END SOURCE {n}']
        return '\n'.join(out + ['END OF PACKET'])

    base = _pk((1, 'Alpha beta gamma.'), (2, 'Delta epsilon.'))
    check(sorted(packet_sources(base)) == [1, 2], 'packet_sources missed a source')
    check('CAPTURE NOTES' not in ''.join(packet_sources(base).values()),
          'packet_sources let the header into a source body')

    # a capture that came back a source short -- virginia, transiently
    c = compare_capture(base, _pk((1, 'Alpha beta gamma.')))
    check(c['gone'] == [2] and capture_needs_review(c),
          'a missing source was not reported as gone')

    # the -nopgbrk correction: separators restored, nothing else
    c = compare_capture(base, _pk((1, 'Alpha beta\ngamma.'), (2, 'Delta epsilon.')))
    check(c['respaced'] == [1] and c['same'] == [2] and not capture_needs_review(c),
          'a whitespace-only change was not classified as respaced')

    # content replaced by a pointer elsewhere -- lsu, behind an HTTP 200
    c = compare_capture(base, _pk((1, 'See elsewhere.'), (2, 'Delta epsilon.')))
    check(c['shrank'] and c['shrank'][0][0] == 1 and capture_needs_review(c),
          'a source losing content was not flagged for review')

    # a decode recovering an address: shorter, and correct. Flagged, not judged.
    ob = _pk((1, 'Write to [email protected] today.'), (2, 'Delta epsilon.'))
    c = compare_capture(ob, _pk((1, 'Write to otl@uvu.edu today.'), (2, 'Delta epsilon.')))
    check(c['shrank'] and c['shrank'][0][0] == 1,
          'a shortening repair was not surfaced at all')
    check(capture_needs_review(c),
          'compare_capture decided a shortening repair was fine on its own')

    c = compare_capture(base, base)
    check(c['same'] == [1, 2] and not capture_needs_review(c),
          'an identical capture was reported as changed')
    check('unchanged' in capture_report(c, 'x') and 'capture comparison for x' in capture_report(c, 'x'),
          'capture_report did not render an unchanged comparison')

    try:
        require_poppler(pin='not-a-real-version')
        check(False, 'require_poppler accepted an obviously wrong pin')
    except RuntimeError as e:
        check('poppler' in str(e), 'require_poppler refusal did not name poppler')

    print('capture-core self-test: ' + ('all checks passed' if ok else 'FAILURES'))
    return 0 if ok else 1


def main(argv):
    if len(argv) > 1 and argv[1] == '--self-test':
        return self_test()
    print(__doc__)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
