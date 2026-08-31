#!/usr/bin/env python3
"""One-off: British 'licence' to American 'license', outside quotations only.

House style is American: *license* as both noun and verb. The pages had drifted
to the British noun throughout — 408 occurrences across 31 state pages, plus
recipe notes and queue prose — because that is how the author of those passages
spells it.

What must not change is a quotation. A board that writes "licence" wrote it, and
altering a quoted span to match house style would be falsifying a source to suit
a style rule; the fidelity checker would catch it, but the rule is prior to the
tool. So the substitution runs only outside quoted spans.

Two different jobs, because the two file types hide their quotes differently:

  markdown  - quotations are straight double quotes in running prose. Parity
              counting works directly: an even number of quotes before an
              occurrence means it sits outside one.

  html      - the rendered page uses straight double quotes for quotations AND
              for every HTML attribute, so naive parity counting pairs a
              quotation's opening mark with an attribute delimiter and the whole
              document goes wrong from the first tag. Tags are therefore masked
              out first and parity is tracked across the text segments only.

Not re-rendered from markdown, per the standing rule in CLAUDE.md: some
published HTML carries hand-applied corrections that a re-render silently
undoes. The same substitution is applied to both files instead.

Run tools/check-fidelity.py against every page afterwards. That is what proves
no quotation moved.
"""
import re
import sys

WORD = re.compile(r'\b([Ll])icenc(e|es|ed|ing)?\b')
TAG = re.compile(r'<[^>]*>')


def sub_outside_quotes(text, quote_chars='"'):
    """Rewrite matches that sit outside quoted spans, leaving quoted text alone."""
    out, changed = [], 0
    depth = 0          # 0 = outside a quotation, 1 = inside
    last = 0
    for i, ch in enumerate(text):
        if ch in quote_chars:
            out.append(text[last:i + 1])
            last = i + 1
            depth ^= 1
    out.append(text[last:])
    # out is now alternating segments split on quote marks: even indices are
    # outside a quotation, odd indices inside.
    result = []
    for idx, seg in enumerate(out):
        if idx % 2 == 0:
            seg, n = WORD.subn(lambda m: m.group(1) + 'licens'[1:]
                               + (m.group(2) or ''), seg)
            changed += n
        result.append(seg)
    return ''.join(result), changed


def fix_markdown(path):
    src = open(path, encoding='utf-8').read()
    new, n = sub_outside_quotes(src)
    if n:
        open(path, 'w', encoding='utf-8').write(new)
    return n


def fix_html(path):
    """Same rule, but quote parity is tracked across text segments only.

    Tags are removed from consideration entirely: an href or a class attribute
    is not prose, cannot contain a quotation, and its delimiters would otherwise
    corrupt the parity of every span after it.
    """
    src = open(path, encoding='utf-8').read()
    parts, pos = [], 0
    for m in TAG.finditer(src):
        parts.append(('text', src[pos:m.start()]))
        parts.append(('tag', m.group(0)))
        pos = m.end()
    parts.append(('text', src[pos:]))

    # Concatenate the text segments, transform once so quote parity carries
    # across segment boundaries, then put the pieces back at their own lengths.
    joined = ''.join(p for kind, p in parts if kind == 'text')
    new_joined, n = sub_outside_quotes(joined)
    if not n:
        return 0
    # Lengths are preserved per replacement only if 'licence'->'license' keeps
    # the same length, which it does; assert rather than assume.
    assert len(new_joined) == len(joined), 'substitution changed text length'
    out, cur = [], 0
    for kind, p in parts:
        if kind == 'tag':
            out.append(p)
        else:
            out.append(new_joined[cur:cur + len(p)])
            cur += len(p)
    open(path, 'w', encoding='utf-8').write(''.join(out))
    return n


def main(paths):
    total = 0
    for p in paths:
        n = fix_html(p) if p.endswith('.html') else fix_markdown(p)
        if n:
            print(f'{n:4d}  {p}')
            total += n
    print(f'{total} replacement(s)')


def self_test():
    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print('FAIL:', msg)
            ok = False

    s = 'A licence is issued. The board says "your licence is active".'
    got, n = sub_outside_quotes(s)
    check(n == 1, f'expected one replacement outside the quotation, got {n}')
    check('A license is issued' in got, 'prose was not corrected')
    check('"your licence is active"' in got,
          'a quoted licence was altered; that is falsifying a source')

    # Plurals, verbs and capitals.
    got, n = sub_outside_quotes('Licences, licenced, licencing.')
    check(got == 'Licenses, licensed, licensing.', f'inflections: {got!r}')

    # Words that merely contain the letters must not move.
    got, n = sub_outside_quotes('licencee silence licences')
    check(n == 1 and 'silence' in got and 'licencee' in got,
          f'over-matched a non-word: {got!r}')

    print('self-test ok' if ok else 'self-test FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--self-test':
        raise SystemExit(self_test())
    main(sys.argv[1:])
