#!/usr/bin/env python3
"""Is the nightly actually running, and is the evidence trail still whole?

A scheduled pass that stops running looks exactly like a scheduled pass with
nothing to report: silence. Nothing in this repo would have said so. The review
cursor would sit where it was, the checked dates would age quietly, and the
first sign would be someone noticing months later that a page said it was
verified in August.

So this is a heartbeat, and it is deliberately run by a *different* task than
the one it watches — the recipe backfill at 00:15 checks on the review pass at
02:03. A watchdog inside the process it monitors reports nothing when the
process is dead.

What it checks:
  1. Rotation freshness — the newest manifest entry anywhere. Three states a
     night means this should never be more than about a day old.
  2. Cursor sanity — tools/review-cursor.txt names a state that exists. An
     absent cursor is read two ways, because it means two opposite things: in a
     collection whose rotation has run, the position was lost and that is
     severe; in one whose rotation has never started, there was no position to
     lose and the first pass begins where it would have begun anyway. A
     REVIEW-LOG.md, or git having ever tracked the cursor, distinguishes them.
     Reported as severe on 2026-09-03 in a repository that had never had a
     cursor at all, which cost an evening establishing that nothing was wrong.
  3. Coverage — the oldest state, and how many have not been reviewed within a
     full lap (17 nights at three a night, so 25 days allows slack).
  4. External anchoring — whether the newest anchor run got its OpenTimestamps
     proof. The sandbox has no `ots` client unless one is installed per run, and
     six runs on 2026-08-29 were anchored by RFC 3161 alone before anyone
     noticed. TSA tokens still date those runs; the Bitcoin path was simply
     absent, and absent silently.
  5. Supplements — their age, and whether each one can be re-captured at all.
     A supplement with a recipe at tools/recipes/<slug>-<kind>.json is
     re-fetched by the rotation like any other source. One without a recipe
     cannot be refreshed by any pass, which is a stronger finding than mere
     age: the page rests on evidence nobody can renew without redoing by hand
     whatever was done the first time.

     Unless it is archival. Some captures are point-in-time observations —
     what a page showed on a date — and re-fetching one does not refresh it,
     it records a different observation that belongs beside the first rather
     than over it. Arizona's parent-resources capture is the case: its whole
     content is that on 2026-08-29 the page linked the current notice in its
     body and an older one in its sidebar. Such a capture declares
     "CLASS: archival" in its header, and this tool reports it as archival
     rather than as a gap. The distinction is the honest one: a live source
     that cannot be re-read is a weakness, and an observation that has already
     happened is not.

Nothing here edits anything. It prints findings and exits non-zero if any are
severe, so a caller can surface them without deciding what they mean.

Usage:
    python3 tools/pass-health.py [--max-age-days N] [--quiet]
    python3 tools/pass-health.py --self-test

Exit codes: 0 healthy, 1 findings, 2 usage error.
"""

import argparse
import datetime
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.path.join(ROOT, 'tools', 'packets', 'history')
CURSOR = os.path.join(ROOT, 'tools', 'review-cursor.txt')
REVIEW_LOG = os.path.join(ROOT, 'REVIEW-LOG.md')
ANCHOR_CHAIN = os.path.join(ROOT, 'anchors', 'chain.jsonl')
ANCHOR_OTS = os.path.join(ROOT, 'anchors', 'ots')
PACKETS = os.path.join(ROOT, 'tools', 'packets')

LAP_DAYS = 25          # 17 nights at three a night, plus slack
SUPPLEMENT_STALE = 120  # a supplement older than this is worth a look


def _date(s):
    try:
        return datetime.date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def cursor_ever_existed(cursor=CURSOR, log=REVIEW_LOG):
    """Has this repository's rotation ever had a position to lose?

    An absent cursor means two opposite things. In a collection whose rotation
    has run, the file was lost, and the rotation's place with it — severe. In a
    collection whose rotation has never started, there is nothing to lose and
    the first pass will begin at the alphabetically first slug, which is what
    it would have done anyway.

    Two independent witnesses, either of which settles it: a REVIEW-LOG.md, the
    append-only record a pass writes, and git having ever tracked the cursor.
    The git question is asked of the file's own repository and answered False
    if there is no repository or no git, so a temporary directory — or a clone
    without history — reads as never-initialized rather than raising.
    """
    if os.path.exists(log):
        return True
    try:
        import subprocess
        out = subprocess.run(
            ['git', 'log', '--oneline', '-1', '--', os.path.basename(cursor)],
            cwd=os.path.dirname(os.path.abspath(cursor)),
            capture_output=True, text=True, timeout=10)
        return out.returncode == 0 and bool(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def latest_pass_by_state(history=HISTORY):
    out = {}
    for man in sorted(glob.glob(os.path.join(history, '*', 'manifest.jsonl'))):
        slug = os.path.basename(os.path.dirname(man))
        last = None
        with open(man, encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    last = json.loads(line)
        if last and _date(last.get('date')):
            out[slug] = _date(last['date'])
    return out


def check(today=None, max_age_days=2, history=HISTORY, cursor=CURSOR,
          chain=ANCHOR_CHAIN, ots_dir=ANCHOR_OTS, packets=PACKETS,
          log=REVIEW_LOG):
    today = today or datetime.date.today()
    findings = []   # (severity, text) — 'severe' counts against the exit code
    notes = []

    passes = latest_pass_by_state(history)
    if not passes:
        findings.append(('severe', 'no manifest entries at all: the retention '
                                   'history is empty or unreadable'))
    else:
        newest = max(passes.values())
        age = (today - newest).days
        if age > max_age_days:
            findings.append(('severe',
                             f'no review pass recorded for {age} days '
                             f'(newest entry {newest}); the nightly may not be '
                             f'running'))
        else:
            notes.append(f'newest pass {newest} ({age} day(s) old)')

        stale = sorted((d, s) for s, d in passes.items()
                       if (today - d).days > LAP_DAYS)
        if stale:
            findings.append(('note',
                             f'{len(stale)} state(s) not reviewed within a full '
                             f'lap of {LAP_DAYS} days, oldest '
                             f'{stale[0][1]} at {stale[0][0]}'))
        notes.append(f'{len(passes)} state(s) carry a manifest; oldest pass '
                     f'{min(passes.values())}')

    if not os.path.exists(cursor):
        if cursor_ever_existed(cursor, log):
            findings.append(('severe',
                             'tools/review-cursor.txt is missing and this '
                             'rotation has run before: the position was lost, '
                             'not merely unset. Do not let a pass restart the '
                             'rotation silently — reconstruct the position '
                             'from REVIEW-LOG.md in a session with the owner'))
        else:
            findings.append(('note',
                             'tools/review-cursor.txt does not exist and never '
                             'has: this rotation has not started. The first '
                             'pass begins at the alphabetically first '
                             'published slug, which is where it would have '
                             'begun anyway. Nothing was lost'))
    else:
        slug = open(cursor, encoding='utf-8').read().strip()
        if not os.path.exists(os.path.join(packets, f'{slug}-packet.txt')):
            findings.append(('severe', f'review cursor names {slug!r}, which is '
                                       f'not a state in the rotation'))
        else:
            notes.append(f'cursor at {slug}')

    if os.path.exists(chain):
        entries = [json.loads(l)['entry'] for l in open(chain, encoding='utf-8')
                   if l.strip()]
        if entries:
            last = entries[-1]['id']
            proof = os.path.join(ots_dir, f'{last}.json.ots')
            if not os.path.exists(proof):
                findings.append(('severe',
                                 f'newest anchor run {last} has no '
                                 f'OpenTimestamps proof: the ots client was '
                                 f'probably missing when it ran. RFC 3161 '
                                 f'tokens still date it; the Bitcoin path does '
                                 f'not exist for that run'))
            else:
                notes.append(f'newest anchor {last} carries an OTS proof')
    else:
        findings.append(('note', 'no anchor chain found'))

    recipes = os.path.join(ROOT, 'tools', 'recipes')
    for p in sorted(glob.glob(os.path.join(packets, '*-packet-*.txt'))):
        if p.endswith('-es.txt') or os.path.basename(p).startswith('TEMPLATE'):
            continue
        stem = os.path.basename(p)[:-len('.txt')].replace('-packet-', '-')
        with open(p, encoding='utf-8') as fh:
            head = fh.read(4000)
        archival = re.search(r'^CLASS:\s*archival\b', head,
                             re.MULTILINE | re.IGNORECASE) is not None
        if archival:
            notes.append(f'supplement {os.path.basename(p)} is archival: a '
                         f'point-in-time observation, not on the rotation')
        elif not os.path.exists(os.path.join(recipes, f'{stem}.json')):
            findings.append(('note',
                             f'supplement {os.path.basename(p)} has no capture '
                             f'recipe (expected tools/recipes/{stem}.json), so '
                             f'no pass can re-fetch it. If it is a point-in-time '
                             f'observation rather than a live source, declare '
                             f'CLASS: archival in its header instead'))
        m = re.search(r'^\s*(?:ASSEMBLY DATE|ASSEMBLED)\s*:?\s*(\d{4}-\d{2}-\d{2})',
                      head, re.MULTILINE | re.IGNORECASE)
        d = _date(m.group(1)) if m else None
        if d and not archival and (today - d).days > SUPPLEMENT_STALE:
            findings.append(('note',
                             f'supplement {os.path.basename(p)} is '
                             f'{(today - d).days} days old and is never '
                             f're-fetched by a review'))
    return findings, notes


def self_test():
    import tempfile, shutil
    failures = []
    d = tempfile.mkdtemp()
    try:
        hist = os.path.join(d, 'history'); os.makedirs(os.path.join(hist, 'iowa'))
        pk = os.path.join(d, 'packets'); os.makedirs(pk)
        open(os.path.join(pk, 'iowa-packet.txt'), 'w').write('x')
        cur = os.path.join(d, 'cursor.txt'); open(cur, 'w').write('iowa\n')
        man = os.path.join(hist, 'iowa', 'manifest.jsonl')

        def write_pass(day):
            with open(man, 'w') as fh:
                fh.write(json.dumps({'date': day, 'kind': 'main',
                                     'result': 'confirmed'}) + '\n')

        today = datetime.date(2026, 9, 1)
        write_pass('2026-08-31')
        f, _ = check(today=today, history=hist, cursor=cur, packets=pk,
                     chain=os.path.join(d, 'none.jsonl'))
        if any(s == 'severe' and 'not be running' in t for s, t in f):
            failures.append('a fresh pass was reported as stalled')

        write_pass('2026-08-20')
        f, _ = check(today=today, history=hist, cursor=cur, packets=pk,
                     chain=os.path.join(d, 'none.jsonl'))
        if not any(s == 'severe' and 'may not be running' in t for s, t in f):
            failures.append('a twelve-day-old pass was not reported as stalled')

        open(cur, 'w').write('atlantis\n')
        f, _ = check(today=today, history=hist, cursor=cur, packets=pk,
                     chain=os.path.join(d, 'none.jsonl'))
        if not any('not a state' in t for _, t in f):
            failures.append('a bogus cursor was not caught')

        # an absent cursor is a note where the rotation never started and a
        # severe finding where it ran and lost its place. The tmpdir is not a
        # git repository, so the REVIEW-LOG.md is the only witness here.
        os.remove(cur)
        log = os.path.join(d, 'REVIEW-LOG.md')
        f, _ = check(today=today, history=hist, cursor=cur, packets=pk,
                     chain=os.path.join(d, 'none.jsonl'), log=log)
        if any(s == 'severe' for s, t in f if 'review-cursor' in t):
            failures.append('an uninitialized rotation was reported as severe')
        if not any('never' in t for _, t in f if 'review-cursor' in t):
            failures.append('an uninitialized rotation was not reported at all')
        open(log, 'w').write('# Review log\n')
        f, _ = check(today=today, history=hist, cursor=cur, packets=pk,
                     chain=os.path.join(d, 'none.jsonl'), log=log)
        if not any(s == 'severe' for s, t in f if 'review-cursor' in t):
            failures.append('a lost cursor was not reported as severe')
        open(cur, 'w').write('iowa\n')

        # an anchor run with no OTS proof beside it is a severe finding
        chain = os.path.join(d, 'chain.jsonl')
        with open(chain, 'w') as fh:
            fh.write(json.dumps({'entry': {'id': '2026-08-29T131740Z'}}) + '\n')
        ots = os.path.join(d, 'ots'); os.makedirs(ots)
        open(cur, 'w').write('iowa\n')
        f, _ = check(today=today, history=hist, cursor=cur, packets=pk,
                     chain=chain, ots_dir=ots)
        if not any('OpenTimestamps' in t for _, t in f):
            failures.append('a missing OTS proof was not caught')
        open(os.path.join(ots, '2026-08-29T131740Z.json.ots'), 'w').write('x')
        f, _ = check(today=today, history=hist, cursor=cur, packets=pk,
                     chain=chain, ots_dir=ots)
        if any('OpenTimestamps' in t for _, t in f):
            failures.append('an OTS proof that exists was reported missing')

        # a supplement with no recipe is a finding; the same supplement declared
        # archival is not, because a point-in-time observation cannot be refreshed
        sup = os.path.join(pk, 'iowa-packet-parents.txt')
        open(sup, 'w').write('STATE: Iowa\nASSEMBLY DATE: 2026-08-01\n')
        f, _ = check(today=today, history=hist, cursor=cur, packets=pk,
                     chain=chain, ots_dir=ots)
        if not any('no capture recipe' in t for _, t in f):
            failures.append('a recipe-less supplement was not reported')
        open(sup, 'w').write('STATE: Iowa\nCLASS: archival — point-in-time\n'
                             'ASSEMBLY DATE: 2026-08-01\n')
        f, n = check(today=today, history=hist, cursor=cur, packets=pk,
                     chain=chain, ots_dir=ots)
        if any('no capture recipe' in t for _, t in f):
            failures.append('an archival supplement was still reported as a gap')
        if not any('is archival' in x for x in n):
            failures.append('an archival supplement was not reported as archival')
    finally:
        shutil.rmtree(d, ignore_errors=True)

    if failures:
        print('SELF-TEST FAILED')
        for f in failures:
            print('  ' + f)
        return 1
    print('SELF-TEST PASSED: a fresh pass is healthy, a stalled one is caught, '
          'a bogus cursor is caught, an uninitialized rotation is a note while '
          'a lost one is severe, a missing OpenTimestamps proof is caught '
          'and a present one is not, a recipe-less supplement is reported and '
          'an archival one is not.')
    return 0


def main(argv):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--max-age-days', type=int, default=2)
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('-h', '--help', action='store_true')
    a = ap.parse_args(argv[1:])
    if a.help:
        print(__doc__)
        return 0
    if a.self_test:
        return self_test()

    findings, notes = check(max_age_days=a.max_age_days)
    if not a.quiet:
        for n in notes:
            print(f'ok    {n}')
    for sev, text in findings:
        print(('FINDING  ' if sev == 'severe' else 'note     ') + text)
    severe = [f for f in findings if f[0] == 'severe']
    print(f'{len(severe)} severe finding(s), {len(findings) - len(severe)} note(s)')
    return 1 if severe else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
