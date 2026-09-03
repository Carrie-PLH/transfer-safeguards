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
