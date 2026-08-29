#!/usr/bin/env python3
"""Every published page against its full evidence set, in one run.

The invariant this holds: no page asserts what its packets do not hold. That
has been true only as often as someone remembered to sweep the index by hand,
which on 2026-08-29 was three times in one session and before that, as far as
the log shows, never. A rule enforced by memory is enforced intermittently.

Why it is not simply a hard gate. Drift is normal here and is supposed to be:
an agency edits a notice, the fidelity check fails, the page is frozen until a
person rebuilds it. A gate that refused to publish while any state was drifted
would block unrelated work behind someone else's edit to a PDF, and would be
disabled within the month. So a state whose latest pass is recorded as drift in
its manifest is expected to fail and is reported without failing the run. Every
other failure stops the run, because nobody has seen it yet.

That distinction is the whole design: known drift is visible but inert, an
unrecorded failure is loud. A state cannot be quietly exempted, because the
exemption comes from the retention manifest — written by retain-packet.py when
a drift capture was stored — and not from a list anyone can edit by hand.

Pages are checked against the set tools/packet-set.py resolves, so a page whose
evidence lives partly in a supplement is checked against the supplement too.
Checking such a page against its main packet alone reports failures that are
not drift; Vermont, Nevada and New Mexico are in that position today.

Usage:
    python3 tools/check-all.py                 every state, md and html
    python3 tools/check-all.py <slug> [...]    named states only
    python3 tools/check-all.py --quiet         summary lines only
    python3 tools/check-all.py --strict        drifted states fail too
    python3 tools/check-all.py --self-test

Exit codes: 0 clean (or only known drift), 1 failures, 2 usage error.
"""

import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.path.join(ROOT, 'tools', 'packets', 'history')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CF = _load('check_fidelity', os.path.join(ROOT, 'tools', 'check-fidelity.py'))
PS = _load('packet_set', os.path.join(ROOT, 'tools', 'packet-set.py'))


def drifted_states(history=None):
    """States whose latest pass of any kind is recorded as drift.

    Same rule as tools/build-status.py: a drift entry is cleared by a later
    rebuild or a later confirmation of that same kind, and by nothing else.
    """
    history = history or HISTORY
    out = {}
    if not os.path.isdir(history):
        return out
    for slug in sorted(os.listdir(history)):
        man = os.path.join(history, slug, 'manifest.jsonl')
        if not os.path.isfile(man):
            continue
        latest = {}
        with open(man, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                latest[r.get('kind', 'main')] = r
        kinds = [k for k, r in sorted(latest.items()) if r.get('result') == 'drift']
        if kinds:
            out[slug] = kinds
    return out


def pages_of(slug):
    """Pages a slug's packets vouch for.

    A slug ending in -discipline belongs to the discipline layer
    (MODULE-DISCIPLINE.md): its pages live in discipline/ and
    site/discipline/ under the bare state slug, while its packets keep the
    full layered slug (texas-discipline-packet.txt). Everything else is the
    original layer.
    """
    if slug.endswith('-discipline'):
        base = slug[:-len('-discipline')]
        candidates = (os.path.join(ROOT, 'discipline', f'{base}.md'),
                      os.path.join(ROOT, 'site', 'discipline', f'{base}.html'))
    else:
        candidates = (os.path.join(ROOT, 'states', f'{slug}.md'),
                      os.path.join(ROOT, 'site', 'states', f'{slug}.html'))
    for p in candidates:
        if os.path.exists(p):
            yield p


def run(slugs=None, quiet=False, strict=False, out=print):
    slugs = slugs or PS.all_slugs()
    drift = drifted_states()
    hard, soft, missing = [], [], []
    checked = 0
    for slug in slugs:
        packets = PS.packet_set(slug)
        absent = [p for p in packets if not os.path.exists(p)]
        if absent:
            missing.append((slug, absent))
            continue
        for page in pages_of(slug):
            checked += 1
            lines = []
            CF.check(page, packets, out=lines.append)
            fails = [l for l in lines if 'failure(s) —' not in l
                     and not l.startswith(('NOTE', 'COVERAGE'))]
            if not fails:
                continue
            (soft if slug in drift else hard).append((slug, page, fails))

    if not quiet:
        for slug, page, fails in soft:
            out(f'known drift — {os.path.relpath(page, ROOT)} '
                f'(recorded drift: {", ".join(drift[slug])})')
            for f in fails:
                out(f'    {f}')
        for slug, page, fails in hard:
            out(f'FAIL {os.path.relpath(page, ROOT)}')
            for f in fails:
                out(f'    {f}')
        for slug, absent in missing:
            out(f'FAIL {slug}: packet(s) named but not on disk: '
                + ', '.join(os.path.relpath(p, ROOT) for p in absent))

    n_states = len(slugs)
    out(f'{checked} page(s) across {n_states} state(s) checked against their '
        f'full packet sets')
    if soft:
        states = sorted({s for s, _, _ in soft})
        out(f'{len(soft)} page(s) failing in {len(states)} state(s) recorded as '
            f'open drift: {", ".join(states)}'
            + (' — counted as failures under --strict' if strict else
               ' — expected, not counted'))
    bad = len(hard) + len(missing) + (len(soft) if strict else 0)
    if bad:
        out(f'{bad} unexplained failure(s)')
    else:
        out('no unexplained failures')
    return 1 if bad else 0


def self_test():
    import tempfile, shutil
    failures = []
    d = tempfile.mkdtemp()
    try:
        packets = os.path.join(d, 'packets')
        hist = os.path.join(d, 'history')
        os.makedirs(packets)
        os.makedirs(os.path.join(hist, 'driftland'))
        keep_packets, keep_history = PS.PACKETS, HISTORY

        def wp(name, body):
            with open(os.path.join(packets, name), 'w', encoding='utf-8') as fh:
                fh.write(body)

        src = ("SOURCE 1: Agency | https://agency.example.gov/p | retrieved: 2026-01-01\n"
               "The agency states that a complaint must be filed in writing.\n")
        sup = ("SOURCE 1: Survey | https://agency.example.gov/s | retrieved: 2026-01-01\n"
               "The notice is available in English only at this time.\n")
        wp('splitland-packet.txt', src)
        wp('splitland-packet-languages.txt', sup)
        wp('driftland-packet.txt', src)
        with open(os.path.join(hist, 'driftland', 'manifest.jsonl'), 'w') as fh:
            fh.write(json.dumps({'date': '2026-08-29', 'kind': 'main',
                                 'result': 'drift', 'capture': 'x.txt'}) + '\n')

        os.makedirs(os.path.join(d, 'states'))
        with open(os.path.join(d, 'states', 'splitland.md'), 'w') as fh:
            fh.write('"a complaint must be filed in writing" and '
                     '"available in English only at this time"\n')
        with open(os.path.join(d, 'states', 'driftland.md'), 'w') as fh:
            fh.write('"complaints are resolved within ten days"\n')

        PS.PACKETS = packets
        globals()['HISTORY'] = hist
        global ROOT
        keep_root = ROOT
        ROOT = d

        sink = []
        rc = run(['splitland'], quiet=True, out=sink.append)
        if rc != 0:
            failures.append('a page whose evidence spans two packets failed: '
                            + '; '.join(sink))

        # the same page checked against its main packet alone must fail — this is
        # the mistake the tool exists to prevent, and the test must show it real
        lines = []
        CF.check(os.path.join(d, 'states', 'splitland.md'),
                 [os.path.join(packets, 'splitland-packet.txt')], out=lines.append)
        if not any(l.startswith('QUOTE') for l in lines):
            failures.append('main-packet-only check did not fail, so the '
                            'supplement is not actually load-bearing in this test')

        sink = []
        rc = run(['driftland'], quiet=True, out=sink.append)
        if rc != 0:
            failures.append('a state recorded as drift blocked the run: '
                            + '; '.join(sink))
        if not any('open drift' in l for l in sink):
            failures.append('drifted state was not reported at all')

        sink = []
        if run(['driftland'], quiet=True, strict=True, out=sink.append) == 0:
            failures.append('--strict did not fail on a drifted state')

        # a state with no drift record must still fail loudly
        wp('plainland-packet.txt', src)
        with open(os.path.join(d, 'states', 'plainland.md'), 'w') as fh:
            fh.write('"complaints are resolved within ten days"\n')
        sink = []
        if run(['plainland'], quiet=True, out=sink.append) == 0:
            failures.append('an unrecorded failure did not fail the run')

        # a packet named but absent is a failure, not a silent pass
        with open(os.path.join(d, 'states', 'ghostland.md'), 'w') as fh:
            fh.write('nothing quoted here\n')
        wp('ghostland-packet.txt', src)
        os.remove(os.path.join(packets, 'ghostland-packet.txt'))
        sink = []
        if run(['ghostland'], quiet=True, out=sink.append) == 0:
            failures.append('a missing packet passed silently')
    finally:
        PS.PACKETS = keep_packets
        globals()['HISTORY'] = keep_history
        ROOT = keep_root
        shutil.rmtree(d, ignore_errors=True)

    if failures:
        print('SELF-TEST FAILED')
        for f in failures:
            print('  ' + f)
        return 1
    print('SELF-TEST PASSED: multi-packet pages verify; a main-packet-only check '
          'of the same page still fails; recorded drift reports without blocking '
          'and blocks under --strict; unrecorded failures and missing packets '
          'fail the run.')
    return 0


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('slugs', nargs='*')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--strict', action='store_true')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('-h', '--help', action='store_true')
    a = ap.parse_args(argv[1:])
    if a.help:
        print(__doc__)
        return 0
    if a.self_test:
        return self_test()
    return run(a.slugs or None, quiet=a.quiet, strict=a.strict)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
