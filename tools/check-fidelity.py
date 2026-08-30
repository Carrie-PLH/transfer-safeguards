#!/usr/bin/env python3
"""Fidelity checker: every checkable fact on a jurisdiction page must trace to its packet.

Three layers, because each catches a different fabrication mode:
1. Quotations (>=15 chars between double quotes) must be verbatim,
   whitespace-normalized substrings of the packet. Catches invented or
   paraphrased quotes.
2. Contact facts — every phone number, email address, postal address and
   external hostname on the page — must appear in the packet. Catches the
   failure the quote check cannot see: a plausible hallucinated phone
   number or mailing address written outside quotation marks. These are
   the facts a resident or family member would actually dial or post to. Postal
   addresses joined this layer on 2026-08-29, when the index was clean and
   the check therefore cost nothing to add.
3. Advisory language must not appear outside verbatim quotation.

A fourth layer applies only to translated pages (--lang es). A Spanish page
quotes the state's Spanish-language notice, so its quotations are checked
against the Spanish packet (<state>-packet-es.txt) rather than the English
one. That much is just layer 1 pointed at a different file. The new check is
pairing: every quotation on a translated page must carry the quote-index ID
of the English passage it corresponds to, written as a data-quote-id
attribute (HTML) or a [[id]] marker (markdown), and that ID must exist in
the index. An unpaired Spanish quote is the failure this project should fear
most — a passage that reads as the state's own word but corresponds to
nothing on the English page, which no amount of verbatim-substring checking
would catch, because it may well be verbatim from somewhere in a 40-page PDF.

Advisory-language screening is English-only; the Spanish register has its own
prohibited constructions and they are not yet enumerated. The checker says so
rather than passing silently, so nobody reads a clean Spanish run as evidence
the advisory rule was enforced.

More than one packet may be given, and every quotation and contact fact is
checked against their concatenation. Evidence captured later — the language
survey in <state>-packet-languages.txt, and any future supplement — therefore
becomes checkable without rewriting the original capture, which stays immutable
with its own assembly date. A page that cites evidence held in no packet is the
failure this guards against: the checker's silence on such a claim is not a
pass, it is the checker never having seen the claim's source.

Usage:
    python3 tools/check-fidelity.py <page.md|page.html> <packet.txt> [<packet2.txt> ...]
    python3 tools/check-fidelity.py --lang es <page.es.md> <packet-es.txt>
                                    [--index research/quote-index.jsonl]
    python3 tools/check-fidelity.py --self-test

Exit codes: 0 clean, 1 failures, 2 usage error.

Allowlist: the site's own domains and mailbox (roomandrecourse.com, and
fieldassembly.net for the publisher link), which legitimately appear on every
page and in no packet.
"""

import html as H
import json
import os
import re
import sys

ALLOW_HOSTS = {"fieldassembly.net", "www.fieldassembly.net",
                "roomandrecourse.com", "www.roomandrecourse.com"}
ALLOW_EMAILS = {"hello@fieldassembly.net"}

# "you qualify" and "we advise" were Board & Border's additions to the
# sibling list; Room & Recourse keeps them and adds "you have grounds" and
# "file by". Whether grounds apply, whether a notice is lawful, and what any
# deadline means for a case are the hearing office's determinations and never
# this page's, so a construction that reads as telling a resident their case
# crosses the charter's hardest boundary.
ADVISORY = ["you should", "we recommend", "your deadline", "be sure to",
            "you qualify", "we advise", "you have grounds", "file by"]

# Editorial annotation written into a packet's source body by whoever assembled
# it. A packet body is meant to hold the source's text and nothing else: the
# moment a note about the capture sits inside it, a later quotation can pick up
# words the agency never published. One such note was written into Hawaii's
# Source 2 on 2026-08-28 — harmless there, because nothing quotes it, but the
# packet contract does not survive on luck.
#
# A blanket rule against brackets would be useless: sources bracket their own
# citations constantly (Florida's notice carries "[§300.504(a)]"), and quote
# ellipses and [sic] are legitimate. So the signature is narrow — a bracketed
# span that talks about capture, rendering, or retrieval. Those are words an
# agency has no reason to put in brackets in a procedural safeguards notice,
# and the assembler has every reason to.
ANNOTATION_VOCAB = [
    "obfuscated", "recoverable", "rendered html", "not captured",
    "capture", "extractor", "extraction", "fetch", "truncated",
    "unreadable", "illegible", "javascript", "page metadata",
    "no body content", "could not be", "unable to", "see capture notes",
]
BRACKET_SPAN_RE = re.compile(r'\[([^\[\]]{12,200})\]')


def check_packet_annotations(packet_text, out, fails):
    """Bracketed editorial notes inside a packet's SOURCE bodies."""
    m = re.search(r'^SOURCE\s+\d+:', packet_text, re.MULTILINE)
    if not m:
        return
    for span in BRACKET_SPAN_RE.finditer(packet_text, m.start()):
        inner = span.group(1)
        low = inner.lower()
        if any(v in low for v in ANNOTATION_VOCAB):
            fails.append('PACKET annotation inside a source body: '
                         f'{inner[:90]!r} — remove it; capture notes belong in '
                         'the header block, never in captured text')

# The preamble — everything above the first SOURCE header line — is the
# assembler's writing, not the source's: the canary, STATE/SLUG/ASSEMBLED, the
# capture notes, the PENDING list. Until 2026-08-29 the checker read it as part
# of the packet, which meant a quotation on a page could be certified by the
# note that described the capture rather than by anything an agency published.
# Idaho's 2026-08-29 review found three such quotations, one of them a
# paraphrase of a sentence the source states in different words: "is offered as
# a matter of course when a complaint or due process hearing is filed" appears
# nowhere in Idaho's materials, and passed for four days because the assembler
# had written it into the capture notes.
#
# This is the same rule as the annotation screen below, applied to the other
# half of the file. That screen catches notes written into a source body; this
# split stops notes being quotable from where they legitimately live. It also
# puts the checker back in agreement with retain-packet.py, which already
# excludes capture notes from the body hash on the same reasoning.
#
# SOURCE header lines were left readable when this split was made, on the
# reasoning that the hostname layer reads source URLs out of them. Later the
# same day that was narrowed to what it actually justifies: see source_bodies()
# below, where quotations and contact facts stopped reading headers and only
# the hostname layer still does. Packet preambles come in at least four shapes
# across the index ("CAPTURE NOTES:", "CAPTURE NOTES", "Capture notes:", and
# headers written "SOURCE 1 |" or bare "SOURCE 1"), which anything parsing them
# has to survive.
SOURCE_HEADER_RE = re.compile(r'^SOURCE\s*\d+\s*[|:]?\s*$|^SOURCE\s*\d+\s*[|:]',
                              re.MULTILINE)


SOURCE_HEADER_LINE_RE = re.compile(r'^SOURCE\s*\d+.*$', re.MULTILINE)


def source_bodies(packet_text):
    """Source text with the SOURCE header lines removed.

    The headers are the assembler's description of each document — its title,
    its own date, sometimes a sentence about how it was read — and on
    2026-08-29 the capture-notes split left them readable on the reasoning
    that the hostname layer needs the URLs out of them. That reasoning holds
    for hostnames and for nothing else. A quotation matching a header matches
    the transcription rather than the document: six such quotations sat across
    four states, every one of them a document's own date or title that the
    capture had not reached in the body. Those are the same shape as Georgia's
    mailing address, which is to say a capture too narrow to support what the
    page says, not a page saying something false.

    So quotations and contact facts are matched against bodies alone, and only
    the hostname layer still reads the whole source region.
    """
    return SOURCE_HEADER_LINE_RE.sub('', source_region(packet_text))


def source_region(packet_text):
    """The packet from its first SOURCE header line on: source text, not commentary.

    Returns the whole text unchanged when no SOURCE header is found, so a
    malformed or hand-written packet fails loudly against its page rather than
    silently checking every quotation against an empty string.
    """
    m = SOURCE_HEADER_RE.search(packet_text)
    return packet_text[m.start():] if m else packet_text


DEFAULT_INDEX = "research/quote-index.jsonl"

# Pairing markers: data-quote-id="ohio:timelines:07" in HTML, [[ohio:timelines:07]]
# in markdown. Both forms carry the same ID from tools/quote-index.py.
QID_RE = re.compile(r'data-quote-id="([^"]+)"|\[\[([a-z0-9-]+:[a-z]+:\d+)\]\]')
QID_SHAPE = re.compile(r'^[a-z0-9-]+:[a-z]+:\d+$')

PHONE_RE = re.compile(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]?\d{4}')
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')

# Postal addresses, added 2026-08-29. Phones, emails and hostnames were checked
# from the start on the reasoning that they are the facts a stressed parent
# actually uses; a mailing address is the fourth, and complaints in most states
# may be filed by post. Thirty-three unquoted addresses sit on the pages today
# and every one of them is in a packet, so this layer costs nothing to add now
# — which is the argument for adding it now rather than after the first
# plausible-looking P.O. Box that no source ever printed.
#
# Deliberately narrow: a box number, or a street number followed by a street
# name and a street-type word. A looser pattern matches statutory citations and
# room numbers and would spend its life crying wolf.
ADDRESS_RE = re.compile(
    r'P\.?\s?O\.?\s+Box\s+\d+'
    r'|\d{1,6}\s+(?:[NSEW]\.?\s+|North\s+|South\s+|East\s+|West\s+)?'
    r'(?:[A-Z][A-Za-z.\']*\s+){1,4}'
    r'(?:Street|St\.|Avenue|Ave\.|Road|Rd\.|Drive|Dr\.|Boulevard|Blvd\.'
    r'|Lane|Ln\.|Way|Place|Pl\.|Court|Ct\.|Circle|Cir\.|Highway|Hwy\.|Plaza|Mall)'
    r'(?![A-Za-z])')
HREF_RE = re.compile(r'href="([^"]+)"|\]\((https?://[^)\s]+)\)')

# Typographic ligatures, decomposed before comparison (added 2026-08-29).
#
# A PDF exported by a modern toolchain may encode "office" as o + U+FB03 + ce
# and "benefits" as bene + U+FB01 + ts. That is a decision about glyph shape
# made by the font, not a decision about wording made by the agency: the
# document says "office" either way, and a reader copying the word out of the
# published page and searching the agency's site for it should find it.
#
# Kansas is the case that forced the question. KSDE replaced Chapters 10 and 11
# of its Process Handbook in June 2026, and the replacement PDFs ligate where
# the superseded ones did not. Seven of the eight quotations that failed on
# 2026-08-29 were identical word for word and differed only here. Left alone,
# that reads as drift, freezes a page that is correct, and spends a human's
# attention on typography — and it will recur every time any of the 51 agencies
# re-exports a document.
#
# The fix belongs in the checker rather than at capture, because a packet
# should hold exactly what the document says. Whether two strings are the same
# word is a question about comparison, and it is asked here.
#
# Deliberately narrow: the seven Latin ligatures in the Alphabetic Presentation
# Forms block, and nothing else. NFKC would also fold non-breaking spaces,
# fractions, superscripts and full-width forms, several of which carry meaning
# a source may have chosen on purpose.
LIGATURES = {
    'ﬀ': 'ff', 'ﬁ': 'fi', 'ﬂ': 'fl',
    'ﬃ': 'ffi', 'ﬄ': 'ffl',
    'ﬅ': 'st', 'ﬆ': 'st',
    # The curly apostrophe is the same decision in different clothing. Kansas's
    # replacement chapters print U+2019 where the superseded ones printed the
    # ASCII apostrophe, so "the agency's list of qualified due process hearing
    # officers" failed on a punctuation glyph. Folding here rather than at
    # capture keeps the packet faithful to the document and is symmetric: a page
    # spelling it either way satisfies a source spelling it either way.
    #
    # Apostrophes only. Curly double quotes are deliberately left alone, because
    # quotations are extracted from the page by their ASCII double quotes before
    # this runs, and teaching the two marks to be interchangeable is a change to
    # what counts as a quotation rather than to how two strings are compared.
    '’': "'", '‘': "'", 'ʼ': "'",
}
LIGATURE_RE = re.compile('[' + ''.join(LIGATURES) + ']')


def unligate(s):
    return LIGATURE_RE.sub(lambda m: LIGATURES[m.group(0)], s)


norm = lambda s: re.sub(r'\s+', ' ', unligate(s))
digits = lambda s: re.sub(r'\D', '', s)


def canon_phone(s):
    d = digits(s)
    if len(d) == 11 and d.startswith('1'):
        d = d[1:]
    return d if len(d) == 10 else None


def host_of(url):
    m = re.match(r'https?://([^/]+)', url)
    return m.group(1).lower() if m else None


def load_index(index_path):
    """quote-index.jsonl -> {id: record}. Missing file is a usage error, not a pass."""
    if not os.path.exists(index_path):
        return None
    idx = {}
    with open(index_path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            idx[r['id']] = r
    return idx


def check_pairing(text, quotes, index, page_state, out, fails):
    """Every translated quotation must name the English span it corresponds to.

    A quote is paired when a marker appears within 200 characters after its
    closing quote — close enough to be unambiguous, loose enough to allow the
    attribution and source link that normally follow a quotation.
    """
    paired = set()
    for q, start, end in quotes:
        window = text[end:end + 200]
        m = QID_RE.search(window)
        if not m:
            fails.append(f'UNPAIRED quote (no quote-index id within 200 chars): {q[:70]!r}')
            continue
        qid = m.group(1) or m.group(2)
        if not QID_SHAPE.match(qid):
            fails.append(f'MALFORMED quote id: {qid!r}')
            continue
        # State prefix first: a cross-state id is also absent from this state's
        # index, and the specific diagnosis is the useful one.
        if page_state and not qid.startswith(page_state + ':'):
            fails.append(f'CROSS-STATE quote id on a {page_state} page: {qid}')
            continue
        if index is not None and qid not in index:
            fails.append(f'UNKNOWN quote id (not in index): {qid}')
            continue
        if qid in paired:
            fails.append(f'DUPLICATE quote id used twice: {qid}')
            continue
        paired.add(qid)
    return paired


def check(page_path, packet_path, out=print, lang='en', index_path=None):
    raw = open(page_path, encoding='utf-8').read()
    packet_paths = ([packet_path] if isinstance(packet_path, str)
                    else list(packet_path))
    packet = "\n".join(source_region(open(p, encoding='utf-8').read())
                       for p in packet_paths)
    packet_label = " + ".join(packet_paths)
    # Quotations and contact facts match against source bodies; hostnames may
    # still be satisfied by a URL in a SOURCE header, which is where a source's
    # address legitimately lives.
    bodies = "\n".join(source_bodies(open(p, encoding='utf-8').read())
                       for p in packet_paths)
    pn = norm(bodies)
    fails = []

    # 0. the packet itself must be source text, not source text plus commentary
    check_packet_annotations(packet, out, fails)

    # hrefs from raw text (before tag stripping)
    hrefs = [a or b for a, b in HREF_RE.findall(raw)]

    text = raw
    if page_path.endswith('.html'):
        text = H.unescape(re.sub(r'<[^>]+>', ' ', text))

    # 1. quotations — pair all quotes first, filter by length after
    quotes = []
    for m in re.finditer(r'"([^"]*)"', text):
        q = m.group(1)
        if len(q) < 15:
            continue
        quotes.append((q, m.start(1), m.end(1)))
        if norm(q) not in pn:
            fails.append(f'QUOTE not in packet: {q[:80]!r}')

    # 2a. phones: page phones (visible text + tel: hrefs) vs packet phones
    packet_phones = {canon_phone(m) for m in PHONE_RE.findall(bodies)}
    packet_phones.discard(None)
    page_phones = {canon_phone(m) for m in PHONE_RE.findall(text)}
    for h in hrefs:
        if h.startswith('tel:'):
            page_phones.add(canon_phone(h))
    page_phones.discard(None)
    for p in sorted(page_phones):
        if p not in packet_phones:
            fails.append(f'PHONE not in packet: {p[:3]}-{p[3:6]}-{p[6:]}')

    # 2b. emails
    packet_emails = {e.lower().rstrip('.') for e in EMAIL_RE.findall(bodies)}
    page_emails = {e.lower().rstrip('.') for e in EMAIL_RE.findall(text)}
    for h in hrefs:
        if h.startswith('mailto:'):
            addr = h[7:].split('?')[0]
            page_emails.add(addr.lower())
    for e in sorted(page_emails - ALLOW_EMAILS):
        if e not in packet_emails:
            fails.append(f'EMAIL not in packet: {e}')

    # 2b-ii. postal addresses — the fourth contact fact, and the one a parent
    # uses when a state requires a complaint by post
    packet_addrs = {norm(a).lower().rstrip('.,')
                    for a in ADDRESS_RE.findall(bodies)}
    for a in sorted({norm(x).lower().rstrip('.,') for x in ADDRESS_RE.findall(text)}):
        if a not in packet_addrs:
            fails.append(f'ADDRESS not in packet: {a[:60]}')

    # 2c. external hostnames
    packet_l = packet.lower()
    for h in hrefs:
        host = host_of(h) if h.startswith('http') else None
        if host and host not in ALLOW_HOSTS:
            bare = host[4:] if host.startswith('www.') else host
            if host not in packet_l and bare not in packet_l:
                fails.append(f'HOSTNAME not in packet: {host}')

    # 3. advisory language outside quotation: strip quoted spans first
    notes = []
    if lang == 'en':
        unquoted = re.sub(r'"[^"]*"', ' ', text).lower()
        for phrase in ADVISORY:
            if phrase in unquoted:
                fails.append(f'ADVISORY language outside quotation: "{phrase}"')
    else:
        notes.append('NOTE advisory-language screening not run: the prohibited '
                     f'constructions are enumerated for English only, not {lang}')

    # 4. pairing — translated pages only
    if lang != 'en':
        index_path = index_path or DEFAULT_INDEX
        index = load_index(index_path)
        if index is None:
            fails.append(f'INDEX missing: {index_path} — run tools/quote-index.py '
                         '--out research/quote-index.jsonl first')
            index = {}
        page_state = re.sub(r'\.(es|[a-z]{2})$', '',
                            os.path.basename(page_path).split('.')[0])
        paired = check_pairing(text, quotes, index or None, page_state, out, fails)
        in_scope = [r for r in (index or {}).values()
                    if r['state'] == page_state and r.get('in_scope')]
        if in_scope:
            notes.append(f'COVERAGE {len(paired)} of {len(in_scope)} in-scope '
                         f'{page_state} spans carried on this page')

    seen = set()
    for f in fails:
        if f not in seen:
            seen.add(f)
            out(f)
    for n in notes:
        out(n)
    out(f'{len(seen)} failure(s) — {page_path} vs {packet_label}'
        + (f' [{lang}]' if lang != 'en' else ''))
    return 0 if not seen else 1


def self_test():
    import tempfile, os
    packet = (
        "SOURCE 1: Test Agency | https://agency.example.gov/page | retrieved: 2026-01-01\n"
        "The agency states that a complaint must be signed and filed in writing "
        "with the Dispute Office. Call 800-222-3353 or write to "
        "help@agency.example.gov or P.O. Box 12345, or visit 700 North Pine "
        "Street. See https://agency.example.gov/rules.\n"
    )
    good = (
        '"a complaint must be signed and filed in writing" per the agency '
        '(retrieved 2026-01-01). Call [800-222-3353](tel:+18002223353) or '
        '[help@agency.example.gov](mailto:help@agency.example.gov). '
        '[rules](https://agency.example.gov/rules) '
        '[site](https://fieldassembly.net) hello@fieldassembly.net '
        'Write to P.O. Box 12345 or call at 700 North Pine Street.\n'
    )
    bad = (
        '"complaints are always resolved within ten days" per the agency. '
        'Call [800-555-0147](tel:+18005550147) or '
        '[intake@agency-help.example.com](mailto:intake@agency-help.example.com). '
        '[guide](https://spedhelp.example.org/guide) Write to P.O. Box 99417 or '
        '4120 Kingfisher Boulevard. You should file quickly.\n'
    )
    with tempfile.TemporaryDirectory() as d:
        pk = os.path.join(d, 'packet.txt'); open(pk, 'w').write(packet)
        g = os.path.join(d, 'good.md'); open(g, 'w').write(good)
        b = os.path.join(d, 'bad.md'); open(b, 'w').write(bad)
        sink = []
        ok = check(g, pk, out=sink.append)
        bad_out = []
        notok = check(b, pk, out=bad_out.append)
        failures = []
        if ok != 0:
            failures.append('good page failed: ' + '; '.join(sink))
        expected = ['QUOTE', 'PHONE', 'EMAIL', 'HOSTNAME', 'ADVISORY', 'ADDRESS']
        for tag in expected:
            if not any(line.startswith(tag) for line in bad_out):
                failures.append(f'bad page: {tag} fabrication not caught')
        # --- multiple packets: evidence split across files must all count ---
        pk2 = os.path.join(d, 'packet-languages.txt')
        open(pk2, 'w').write(
            "SOURCE 1: Lang page | https://agency.example.gov/langs | retrieved: 2026-08-26\n"
            "The notice is available in English only at this time.\n")
        split = os.path.join(d, 'split.md')
        open(split, 'w').write(
            '"a complaint must be signed and filed in writing" and '
            '"available in English only at this time"\n')
        sink = []
        if check(split, [pk, pk2], out=sink.append) != 0:
            failures.append('multi-packet: page spanning two packets failed: '
                            + '; '.join(sink))
        sink = []
        if check(split, pk, out=sink.append) == 0:
            failures.append('multi-packet: second-packet quote passed against the '
                            'first packet alone — the split is not being enforced')

        # --- typographic ligatures are not wording (Kansas, 2026-08-29) ---
        # A source that ligates must satisfy a page that spells the word out,
        # and the reverse, since either side may be the ligated one. A real
        # difference in wording next door to a ligature must still fail, or the
        # decomposition has been made to cover for something.
        pk_lig = os.path.join(d, 'packet-lig.txt')
        open(pk_lig, 'w', encoding='utf-8').write(
            "SOURCE 1: Ligature Agency | https://agency.example.gov/lig | retrieved: 2026-08-29\n"
            "The oﬃce lists the beneﬁts aﬀorded to parents and the LEA’s staff.\n")
        lig_page = os.path.join(d, 'lig.md')
        open(lig_page, 'w', encoding='utf-8').write(
            '"The office lists the benefits afforded to parents and the LEA\'s staff."\n')
        sink = []
        if check(lig_page, pk_lig, out=sink.append) != 0:
            failures.append('ligature: spelled-out page failed against a ligated '
                            'packet: ' + '; '.join(sink))
        lig_rev = os.path.join(d, 'lig-rev.md')
        open(lig_rev, 'w', encoding='utf-8').write(
            '"The oﬃce lists the beneﬁts aﬀorded to parents"\n')
        pk_plain = os.path.join(d, 'packet-plain.txt')
        open(pk_plain, 'w', encoding='utf-8').write(
            "SOURCE 1: Plain Agency | https://agency.example.gov/plain | retrieved: 2026-08-29\n"
            "The office lists the benefits afforded to parents and the LEA.\n")
        sink = []
        if check(lig_rev, pk_plain, out=sink.append) != 0:
            failures.append('ligature: ligated page failed against a spelled-out '
                            'packet: ' + '; '.join(sink))
        lig_bad = os.path.join(d, 'lig-bad.md')
        open(lig_bad, 'w', encoding='utf-8').write(
            '"The office lists the benefits afforded to parents and the school\'s staff."\n')
        sink = []
        if check(lig_bad, pk_lig, out=sink.append) == 0:
            failures.append('ligature: a real wording change (LEA -> school) passed '
                            'because the ligatures around it were decomposed')

        # --- capture notes are not quotable evidence (Idaho, 2026-08-29) ---
        # A packet's preamble is the assembler's writing. A page quoting it is
        # quoting this project, not the agency, and must fail. Each preamble
        # shape in the index is exercised, because the shapes differ and a
        # parser that handles only the current one would silently readmit the
        # notes of eight pilot-era packets.
        preambles = {
            'colon': "CAPTURE NOTES:\n- The office is described as the sole intake point.\n",
            'bare': "CAPTURE NOTES\n- The office is described as the sole intake point.\n",
            'inline': "Capture notes: the office is described as the sole intake point.\n",
        }
        headers = {
            'colon-header': "SOURCE 1: Test Agency | https://agency.example.gov/page | retrieved: 2026-01-01\n",
            'pipe-header': "SOURCE 1 | Test Agency | https://agency.example.gov/page | retrieved: 2026-01-01\n",
            'bare-header': "SOURCE 1\n",
        }
        body = ("The agency states that a complaint must be signed and filed "
                "in writing with the Dispute Office.\n")
        quotes_a_note = ('"described as the sole intake point"\n')
        quotes_the_body = ('"a complaint must be signed and filed in writing"\n')
        for pname, pre in preambles.items():
            for hname, hdr in headers.items():
                pkn = os.path.join(d, f'packet-{pname}-{hname}.txt')
                open(pkn, 'w').write(
                    "FIRST LINE OF PACKET\n\nSTATE: Testland\n\n" + pre + "\n"
                    + hdr + body + "END SOURCE 1\n")
                note_pg = os.path.join(d, f'note-{pname}-{hname}.md')
                open(note_pg, 'w').write(quotes_a_note)
                sink = []
                if check(note_pg, pkn, out=sink.append) == 0:
                    failures.append(
                        f'capture notes ({pname}/{hname}): a quotation matching '
                        'only the assembler\'s notes passed')
                body_pg = os.path.join(d, f'body-{pname}-{hname}.md')
                open(body_pg, 'w').write(quotes_the_body)
                sink = []
                if check(body_pg, pkn, out=sink.append) != 0:
                    failures.append(
                        f'capture notes ({pname}/{hname}): a quotation from the '
                        'source body was rejected: ' + '; '.join(sink))
        # A packet with no SOURCE header at all is malformed. It must not
        # silently become an empty haystack in which nothing verifies quietly;
        # it is read whole, so the page fails loudly against it instead.
        headerless = os.path.join(d, 'headerless.txt')
        open(headerless, 'w').write("CAPTURE NOTES:\n- no sources were captured\n")
        sink = []
        if check(body_pg, headerless, out=sink.append) == 0:
            failures.append('headerless packet: page passed against a packet '
                            'holding no source text')

        # --- Spanish path: quotes checked against the es packet, plus pairing ---
        packet_es = (
            "SOURCE 1 (es): Agencia de Prueba | https://agency.example.gov/es | retrieved: 2026-01-01\n"
            "La agencia indica que una queja debe presentarse por escrito y estar firmada.\n"
            "El nino permanece en la ubicacion educativa actual durante el proceso.\n"
        )
        index = [
            {"id": "testland:docket:01", "state": "testland", "layer": "docket", "in_scope": True},
            {"id": "testland:hoist:01", "state": "testland", "layer": "hoist", "in_scope": True},
        ]
        es_good = (
            'La agencia indica: "una queja debe presentarse por escrito y estar firmada" '
            '[[testland:docket:01]]\n'
        )
        es_unpaired = (
            'La agencia indica: "una queja debe presentarse por escrito y estar firmada"\n'
        )
        es_badid = (
            'La agencia indica: "una queja debe presentarse por escrito y estar firmada" '
            '[[testland:docket:99]]\n'
        )
        es_crossstate = (
            'La agencia indica: "una queja debe presentarse por escrito y estar firmada" '
            '[[ohio:docket:01]]\n'
        )
        pk_es = os.path.join(d, 'packet-es.txt'); open(pk_es, 'w').write(packet_es)
        idx = os.path.join(d, 'index.jsonl')
        with open(idx, 'w') as fh:
            for r in index:
                fh.write(json.dumps(r) + '\n')

        def run_es(name, content):
            p = os.path.join(d, name); open(p, 'w', encoding='utf-8').write(content)
            sink = []
            rc = check(p, pk_es, out=sink.append, lang='es', index_path=idx)
            return rc, sink

        rc, sink = run_es('testland.es.md', es_good)
        if rc != 0:
            failures.append('good Spanish page failed: ' + '; '.join(sink))
        if not any(l.startswith('NOTE advisory') for l in sink):
            failures.append('Spanish page did not disclose that advisory screening was skipped')
        if not any(l.startswith('COVERAGE') for l in sink):
            failures.append('Spanish page did not report in-scope coverage')

        for name, content, tag in (
            ('testland.es.md', es_unpaired, 'UNPAIRED'),
            ('testland.es.md', es_badid, 'UNKNOWN'),
            ('testland.es.md', es_crossstate, 'CROSS-STATE'),
        ):
            rc, sink = run_es(name, content)
            if not any(l.startswith(tag) for l in sink):
                failures.append(f'Spanish page: {tag} not caught')

        # an English quote smuggled onto a Spanish page has no es-packet match
        rc, sink = run_es('testland.es.md',
                          '"a complaint must be signed and filed in writing" '
                          '[[testland:docket:01]]\n')
        if not any(l.startswith('QUOTE') for l in sink):
            failures.append('Spanish page: English quote not caught against es packet')

        if failures:
            print('SELF-TEST FAILED:'); [print(' ', f) for f in failures]
            return 1
        print(f'SELF-TEST PASSED: clean page passes; all {len(expected)} fabrication modes caught; '
              'multi-packet evidence checked and enforced; Spanish pairing enforced '
              '(unpaired, unknown id, cross-state, wrong-language quote).')
        return 0


def main(argv):
    args = argv[1:]
    if args == ['--self-test']:
        return self_test()

    lang = 'en'
    index_path = None
    if '--lang' in args:
        i = args.index('--lang')
        try:
            lang = args[i + 1]
        except IndexError:
            print('--lang needs a language code', file=sys.stderr)
            return 2
        del args[i:i + 2]
    if '--index' in args:
        i = args.index('--index')
        try:
            index_path = args[i + 1]
        except IndexError:
            print('--index needs a path', file=sys.stderr)
            return 2
        del args[i:i + 2]

    if len(args) < 2:
        print(__doc__)
        return 2
    return check(args[0], args[1:], lang=lang, index_path=index_path)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
