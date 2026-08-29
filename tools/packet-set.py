#!/usr/bin/env python3
"""The evidence set for a page: which packets it must be checked against.

The problem this closes. A page is checked against "every packet that page
has", and until now that phrase lived only in prose — in the reviewer skill, in
PROVENANCE.md, in whoever was running the pass. Prose cannot be executed, and
the nightly's own instructions tell it to check a page against the fresh review
capture alone. That was harmless while every page's evidence sat in one file.
It stopped being harmless on 2026-08-26, when Vermont's language survey became
the only packet holding two quotations on its page, and again on 2026-08-29,
when Nevada and New Mexico were repaired by supplemental capture. Any of those
three checked against one packet reports failures that are not drift — and the
reviewer is told, correctly, to treat a failure as real. A false drift entry
freezes a page that is fine and spends the owner's attention on nothing, which
is exactly the noise the punctuation decision was made to avoid.

So the evidence set is computed here, from the filesystem, and the pass asks
rather than remembers.

What belongs to a page:
    tools/packets/<slug>-packet.txt              the main capture
    tools/packets/<slug>-packet-<kind>.txt       every supplement
and, during a review, the fresh capture stands in for the main packet while
the supplements come along unchanged — a review re-fetches a state's main
sources, not its supplements, so the supplements are still the current evidence
for the spans that rest on them.

Spanish pages are a separate set, not an addition: a translated page quotes the
state's Spanish notice and is checked against <slug>-packet-es.txt, so --lang es
returns that packet alone. The English supplements would only add English text
a Spanish quotation can never match.

Supplements. A review re-fetches a state's main sources; whether it also
re-fetches that state's supplements is up to the pass, and until 2026-08-29
none did, so a page could keep verifying against a capture nobody had looked at
since the day it was taken. A supplement with a recipe at
tools/recipes/<slug>-<kind>.json can now be re-captured exactly like a main
source, and the nightly does so when the rotation reaches that state. --ages
reports each supplement's age and whether it has a recipe; a supplement without
one cannot be refreshed by any pass, which is the finding worth acting on.

Usage:
    python3 tools/packet-set.py <slug>                     packets, one per line
    python3 tools/packet-set.py <slug> --review <capture>  capture replaces main
    python3 tools/packet-set.py <slug> --lang es           the Spanish set
    python3 tools/packet-set.py <slug> --args              one space-joined line
    python3 tools/packet-set.py --all                      every slug, one per line
    python3 tools/packet-set.py --ages [--older-than N]    supplement ages
    python3 tools/packet-set.py <slug> --kinds               supplement kinds
    python3 tools/packet-set.py --self-test

Exit codes: 0 clean, 1 a named packet is missing, 2 usage error.
"""

import argparse
import datetime
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKETS = os.path.join(ROOT, 'tools', 'packets')

# TEMPLATE-packet-languages.txt is the blank form new language surveys are
# copied from, not evidence for any page.
NOT_A_STATE = {'TEMPLATE'}


def main_packet(slug):
    return os.path.join(PACKETS, f'{slug}-packet.txt')


def supplements(slug):
    """Every <slug>-packet-<kind>.txt except the Spanish packet, sorted by kind.

    Spanish is excluded because it is a different set rather than a supplement:
    it holds the same document in another language, and mixing it in would let
    an English quotation verify against Spanish evidence or the reverse.
    """
    out = []
    for p in sorted(glob.glob(os.path.join(PACKETS, f'{slug}-packet-*.txt'))):
        kind = os.path.basename(p)[len(slug) + len('-packet-'):-len('.txt')]
        if kind == 'es':
            continue
        out.append(p)
    return out


def es_packet(slug):
    return os.path.join(PACKETS, f'{slug}-packet-es.txt')


class ReviewCaptureError(ValueError):
    """--review was pointed at something that is not a fresh main-source capture."""


def check_review_capture(slug, review):
    """A review capture replaces the main packet, so it must be one.

    Pointing --review at a supplement is a quiet disaster rather than a loud
    one: the supplement replaces the main packet and is then re-added as a
    supplement, so the page is checked against a fraction of its evidence and
    reports a page-full of failures that look like catastrophic drift. It is an
    easy mistake to make at 2am with tab completion — it was made once while
    this tool was being written — and the shapes are distinguishable, so it is
    worth refusing rather than trusting care.
    """
    base = os.path.basename(review)
    if os.path.dirname(os.path.abspath(review)) == os.path.abspath(PACKETS):
        raise ReviewCaptureError(
            f'--review points at a standing packet ({base}). A review capture '
            f'is a fresh capture, normally under tools/packets/review/; the '
            f'standing packets are what it replaces.')
    if base.startswith(f'{slug}-packet-'):
        raise ReviewCaptureError(
            f'--review points at a supplement ({base}). A supplement adds to a '
            f'page\'s evidence; it cannot stand in for the main capture, and '
            f'passing it here would drop the main sources from the check.')
    return review


def packet_set(slug, review=None, lang='en'):
    """The packets a page of this state and language must be checked against."""
    if lang != 'en':
        return [os.path.join(PACKETS, f'{slug}-packet-{lang}.txt')]
    first = check_review_capture(slug, review) if review else main_packet(slug)
    return [first] + supplements(slug)


def all_slugs():
    out = []
    for p in sorted(glob.glob(os.path.join(PACKETS, '*-packet.txt'))):
        slug = os.path.basename(p)[:-len('-packet.txt')]
        if slug not in NOT_A_STATE:
            out.append(slug)
    return out


DATE_RE = re.compile(r'^\s*(?:ASSEMBLY DATE|ASSEMBLED)\s*:?\s*(\d{4}-\d{2}-\d{2})',
                     re.MULTILINE | re.IGNORECASE)


def assembly_date(path):
    """The capture's own assembly date, or None if it does not carry one."""
    try:
        with open(path, encoding='utf-8') as fh:
            head = fh.read(4000)
    except OSError:
        return None
    m = DATE_RE.search(head)
    if not m:
        return None
    try:
        return datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def ages(today=None):
    """(slug, path, date, days) for every supplement, oldest first."""
    today = today or datetime.date.today()
    rows = []
    for slug in all_slugs():
        for p in supplements(slug):
            d = assembly_date(p)
            rows.append((slug, p, d, (today - d).days if d else None))
    rows.sort(key=lambda r: (-1 if r[3] is None else -r[3]))
    return rows


def self_test():
    import tempfile, shutil
    global PACKETS
    keep = PACKETS
    failures = []
    d = tempfile.mkdtemp()
    try:
        PACKETS = d
        def touch(name, body="STATE: x\nASSEMBLY DATE: 2026-08-01\n"):
            with open(os.path.join(d, name), 'w', encoding='utf-8') as fh:
                fh.write(body)
        touch('testland-packet.txt')
        touch('testland-packet-languages.txt')
        touch('testland-packet-notice.txt')
        touch('testland-packet-es.txt')
        touch('TEMPLATE-packet-languages.txt')
        touch('plainland-packet.txt')

        got = [os.path.basename(p) for p in packet_set('testland')]
        want = ['testland-packet.txt', 'testland-packet-languages.txt',
                'testland-packet-notice.txt']
        if got != want:
            failures.append(f'english set wrong: {got} != {want}')

        # a supplement must never be mistaken for the Spanish packet
        if any(p.endswith('-packet-es.txt') for p in packet_set('testland')):
            failures.append('Spanish packet leaked into the English set')

        # the Spanish set is that packet alone, not an addition to the English one
        got = [os.path.basename(p) for p in packet_set('testland', lang='es')]
        if got != ['testland-packet-es.txt']:
            failures.append(f'spanish set wrong: {got}')

        # a review capture stands in for the main packet; supplements survive it,
        # because a review re-fetches main sources and leaves supplements alone
        got = [os.path.basename(p) for p in
               packet_set('testland', review='/r/testland-2026-08-29.txt')]
        if got[0] != 'testland-2026-08-29.txt' or len(got) != 3:
            failures.append(f'review set wrong: {got}')

        # a state with no supplements still resolves to its one packet
        if len(packet_set('plainland')) != 1:
            failures.append('plain state did not resolve to one packet')

        # --review pointed at a supplement, or at a standing packet, is refused:
        # either would silently drop the main sources from the check
        for bad, why in ((os.path.join(d, 'testland-packet-notice.txt'), 'supplement'),
                         (os.path.join(d, 'testland-packet.txt'), 'standing packet')):
            try:
                packet_set('testland', review=bad)
            except ReviewCaptureError:
                pass
            else:
                failures.append(f'--review accepted a {why}')
        # a genuine review capture, living outside tools/packets/, is accepted
        try:
            packet_set('testland', review='/tmp/review/testland-2026-08-29.txt')
        except ReviewCaptureError as e:
            failures.append(f'--review refused a real review capture: {e}')

        # the blank template is not a state
        if 'TEMPLATE' in all_slugs():
            failures.append('TEMPLATE counted as a state')
        if all_slugs() != ['plainland', 'testland']:
            failures.append(f'slug list wrong: {all_slugs()}')

        # ages read the capture's own assembly date, not the file mtime, so a
        # touched file does not look freshly captured
        rows = {os.path.basename(p): days for slug, p, dt, days in
                ages(today=datetime.date(2026, 8, 31))}
        if rows.get('testland-packet-notice.txt') != 30:
            failures.append(f'age wrong: {rows}')
        touch('testland-packet-undated.txt', "STATE: x\nno date here\n")
        undated = [r for r in ages() if r[1].endswith('undated.txt')]
        if not undated or undated[0][3] is not None:
            failures.append('undated supplement not reported as undated')
    finally:
        PACKETS = keep
        shutil.rmtree(d, ignore_errors=True)

    if failures:
        print('SELF-TEST FAILED')
        for f in failures:
            print('  ' + f)
        return 1
    print('SELF-TEST PASSED: English set includes supplements and excludes the '
          'Spanish packet and the template; the Spanish set stands alone; a '
          'review capture replaces the main packet without dropping supplements; '
          'ages come from the capture, not the file.')
    return 0


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('slug', nargs='?')
    ap.add_argument('--review')
    ap.add_argument('--lang', default='en')
    ap.add_argument('--args', action='store_true')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--ages', action='store_true')
    ap.add_argument('--kinds', action='store_true')
    ap.add_argument('--older-than', type=int, default=0)
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('-h', '--help', action='store_true')
    a = ap.parse_args(argv[1:])

    if a.help:
        print(__doc__)
        return 0
    if a.self_test:
        return self_test()
    if a.all:
        for s in all_slugs():
            print(s)
        return 0
    if a.ages:
        rows = [r for r in ages()
                if r[3] is None or r[3] >= a.older_than]
        if not rows:
            print('no supplements')
            return 0
        for slug, path, dt, days in rows:
            age = 'no assembly date in capture' if days is None else f'{days} days'
            base = os.path.basename(path)
            stem = base[:-len('.txt')].replace('-packet-', '-')
            has = os.path.exists(os.path.join(ROOT, 'tools', 'recipes',
                                              f'{stem}.json'))
            with open(path, encoding='utf-8') as fh:
                archival = re.search(r'^CLASS:\s*archival\b', fh.read(4000),
                                     re.MULTILINE | re.IGNORECASE) is not None
            state = ('archival — point-in-time, not on the rotation' if archival
                     else 'recipe' if has
                     else 'NO RECIPE — cannot be re-fetched')
            print(f'{slug:20} {base:40} {age:12} {state}')
        print(f'\n{len(rows)} supplement(s). A supplement with a recipe is '
              're-captured when the rotation reaches its state; one without a '
              'recipe cannot be refreshed by any pass and its age will only '
              'grow.')
        return 0
    if a.kinds:
        if not a.slug:
            print('--kinds needs a slug', file=sys.stderr)
            return 2
        for p in supplements(a.slug):
            kind = os.path.basename(p)[len(a.slug) + len('-packet-'):-len('.txt')]
            recipe = os.path.join(ROOT, 'tools', 'recipes',
                                  f'{a.slug}-{kind}.json')
            print(f'{kind}\t{"recipe" if os.path.exists(recipe) else "NO-RECIPE"}')
        return 0
    if not a.slug:
        print(__doc__, file=sys.stderr)
        return 2

    try:
        paths = packet_set(a.slug, review=a.review, lang=a.lang)
    except ReviewCaptureError as e:
        print(f'refusing: {e}', file=sys.stderr)
        return 2
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        for p in missing:
            print(f'missing packet: {p}', file=sys.stderr)
        return 1
    print(' '.join(paths) if a.args else '\n'.join(paths))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
