"""Propose slice anchors for a draft recipe, by finding the standing packet's
own span inside a fresh unsliced extraction.

Why this exists. Thirteen Room & Recourse states were captured by hand as line
ranges out of longer documents. Re-deriving each slice by eye is exactly the
work that put the wrong rule number in Oklahoma's header: a person reading a
long PDF and typing what they think they see. This does it mechanically —
the anchors come from the documents, and the recipe's own capture plus
check-fidelity.py remain the test of whether they are right.

How. For each source in the draft recipe, the source is fetched and extracted
with no slice, and the standing packet's body for that source is located inside
that extraction. The first line of the located span becomes the `from` anchor;
the first line after it becomes `to`. Each anchor is then extended, word by
word, until it is at least MIN_ANCHOR characters and matches exactly once — or
until it runs out of line, in which case the occurrence index is reported so
the recipe can say `from_occurrence` explicitly.

What it does not do. It does not write the recipe, and it never decides that a
proposal is good. A proposal that cannot be located, or that lands in a table
of contents, is reported as such and left to a person. Nothing here is
evidence; the packet the recipe produces is.

Usage:
    python3 tools/propose-slice.py <slug>            # every source
    python3 tools/propose-slice.py <slug> --source 2
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("cap", os.path.join(HERE, "capture.py"))
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

MIN_ANCHOR = cap.MIN_ANCHOR


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def packet_bodies(slug):
    """{n: body} from the standing packet."""
    p = os.path.join(HERE, 'packets', f'{slug}-packet.txt')
    t = open(p, encoding='utf-8', errors='replace').read()
    parts = re.split(r'^(SOURCE (\d+):.*)$', t, flags=re.M)
    out = {}
    for i in range(1, len(parts), 3):
        n = int(parts[i + 1])
        body = re.split(r'^END SOURCE \d+', parts[i + 2], flags=re.M)[0]
        out[n] = body
    return out


def locate(full, body):
    """Character span of `body` inside `full`, matched on collapsed whitespace."""
    fn, bn = norm(full), norm(body)
    if not bn:
        return None
    head = bn[:120]
    i = fn.find(head)
    if i < 0:
        return None
    return i, i + len(bn), fn


def grow(fn, start, want_unique=True):
    """An anchor beginning at `start` in the normalized text: at least
    MIN_ANCHOR characters, and grown until it matches once if it can."""
    # MIN_ANCHOR is the floor the linter enforces; PREFERRED is what this
    # proposes. A 13-character anchor that happens to be unique today ("7. Is
    # free from") is one revision away from matching somewhere else, and these
    # documents are revised. Longer costs nothing and survives more.
    PREFERRED = 45
    words = fn[start:start + 400].split(' ')
    anchor = ''
    for w in words:
        anchor = (anchor + ' ' + w).strip()
        if len(anchor) < max(MIN_ANCHOR, PREFERRED):
            continue
        n = len(re.findall(re.escape(anchor), fn))
        if n == 1 or not want_unique:
            return anchor, n
        if len(anchor) > 200:
            break
    return anchor, len(re.findall(re.escape(anchor), fn))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('slug')
    ap.add_argument('--source', type=int)
    a = ap.parse_args(argv)

    rec = cap.load_recipe(a.slug)
    bodies = packet_bodies(a.slug)
    for s in rec['sources']:
        n = s['n']
        if a.source and n != a.source:
            continue
        probe = dict(s)
        probe.pop('slice', None)
        try:
            full = cap.capture_source(probe)
        except Exception as e:                       # transport is the operator's problem
            print(f'source {n}: could not capture unsliced — {e}')
            continue
        body = bodies.get(n)
        if body is None:
            print(f'source {n}: no matching SOURCE in the standing packet')
            continue
        loc = locate(full, body)
        if not loc:
            print(f'source {n}: the standing packet body was not found in a fresh '
                  f'extraction. Either the source moved, or this source was captured '
                  f'by a different route than the draft recipe describes. Read it.')
            continue
        i, j, fn = loc
        frm, fn_hits = grow(fn, i)
        tail = fn[j:].lstrip()
        if not tail:
            print(f'source {n}: runs to the end of the document — no "to" anchor needed')
            print(json.dumps({'from': frm}, ensure_ascii=False, indent=2))
            continue
        to, to_hits = grow(fn, len(fn) - len(tail))
        sl = {'from': frm}
        if fn_hits > 1:
            occ = 1 + len(re.findall(re.escape(frm), fn[:i]))
            sl['from_occurrence'] = occ
            print(f'source {n}: NOTE from anchor matches {fn_hits} times; '
                  f'occurrence {occ} is the packet\'s span — check it is not the '
                  f'table of contents')
        sl['to'] = to
        if to_hits > 1:
            occ = 1 + len(re.findall(re.escape(to), fn[:j]))
            sl['to_occurrence'] = occ
        print(f'source {n}: proposed slice')
        print(json.dumps(sl, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
