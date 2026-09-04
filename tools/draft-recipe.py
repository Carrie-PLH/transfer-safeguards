"""Draft a recipe from a standing packet's own SOURCE headers.

This writes the mechanical half of a recipe — the source list, the URLs, the
dates the packet already records, and an extractor guessed from the URL — so a
person's attention goes to the parts that need judgment: the slice anchors, the
scope, and the notes that say why each choice is right.

A draft is not a recipe. It carries "DRAFT" in every note, and capture.py's
own lint plus check-fidelity.py against both forms of the page remain the test.
Never promote a packet built from an unreviewed draft.

Usage: python3 tools/draft-recipe.py <slug> [<slug> ...]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def parse(slug):
    p = os.path.join(HERE, 'packets', f'{slug}-packet.txt')
    t = open(p, encoding='utf-8', errors='replace').read()
    out = []
    for m in re.finditer(r'^SOURCE (\d+): (.*?) \| (\S+) \| source.s own date: (.*?) \| retrieved:',
                         t, flags=re.M):
        out.append({'n': int(m.group(1)), 'title': m.group(2).strip(),
                    'url': m.group(3).strip(), 'source_date': m.group(4).strip()})
    return out


def draft(slug):
    srcs = parse(slug)
    if not srcs:
        raise SystemExit(f'{slug}: no SOURCE headers parsed')
    for s in srcs:
        pdf = s['url'].lower().endswith('.pdf') or 'pdf' in s['url'].lower()
        s['transport'] = 'curl'
        s['user_agent'] = 'browser'
        s['extractor'] = 'pdftotext-layout' if pdf else 'html-text'
        if s['extractor'] == 'html-text':
            s['scope'] = 'body'
        s['notes'] = 'DRAFT — replace before promoting.'
    return {'recipe_version': 1, 'state': slug, 'sources': srcs}


def main(argv):
    for slug in argv:
        p = os.path.join(HERE, 'recipes', f'{slug}.json')
        if os.path.exists(p):
            print(f'{slug}: recipe already exists, left alone')
            continue
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(draft(slug), fh, indent=2, ensure_ascii=False)
            fh.write('\n')
        print(f'{slug}: draft written with {len(draft(slug)["sources"])} source(s)')


if __name__ == '__main__':
    main(sys.argv[1:])
