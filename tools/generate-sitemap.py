#!/usr/bin/env python3
"""Generate sitemap.xml, robots.txt and _redirects for the published site.

Why this exists. Until 2026-09-05 every sitemap in the portfolio was written
by hand or by a third-party crawler, and every one of them had drifted:
this site published 58 pages and offered 42, Rules & Record published 111 and
offered exactly 100 (the free tier's cap, silently applied), Board & Border
offered 99 URLs against 58 real pages. A sitemap maintained by memory is
maintained intermittently, and nothing in any repo would have said so. So the
file tree is the one source of truth here, and this tool derives the map from
it on every deploy.

What it writes, all three into the deploy root:

  sitemap.xml   every indexable page, canonical form, git-dated
  robots.txt    a crawl allowance and a pointer to the sitemap
  _redirects    a 301 from every non-canonical URL form to the canonical one

Canonical URL form. wrangler.toml sets html_handling = "force-trailing-slash",
so every HTML page is served at a path ending in "/": states/ohio.html at
/states/ohio/ and states/index.html at /states/. That setting was chosen over
the "auto-trailing-slash" default on 2026-09-05 because auto is not one rule
but two — files served bare, folder indexes served with a slash — and a
sitemap encoding two rules is a sitemap that encodes them wrongly eventually.

Why _redirects when Cloudflare already redirects. Under any html_handling
setting Cloudflare redirects the non-canonical forms itself, but it does so
with a 307, which is temporary: the .html URL stays a live candidate for
indexing, which is the split-signal problem workers_dev = false already
exists to avoid. The rules written here are 301s and take the question off
the table permanently. They matter most for the .html URLs, which are what
the old hand-written sitemaps spent a year feeding crawlers.

What is left out of the sitemap, by rule rather than by list:

  404.html          served in place of pages that do not exist
  noindex pages     a page telling crawlers not to index it, and a sitemap
                    offering it for indexing, are contradictory signals; the
                    one written into the page wins
  drifted states    a state whose latest recorded pass is drift is a page
                    whose quotations no longer match their source and which
                    is waiting on a rebuild. Offering it to crawlers invites
                    indexing of a page this project has itself recorded as
                    unverified. The list comes from check-all.py, which reads
                    the retention manifests, so a page cannot be exempted by
                    anyone editing a list here.

  States recorded as `accepted` are NOT excluded. Accepted is not drift: it
  is a page that has had every rebuild it can have, whose residual mismatch
  is permanent, documented in the recipe notes, and disclosed on the page.
  Excluding it would hide a finished page from search forever for a condition
  that will never clear.

lastmod is the git commit date of the file, not its mtime. A review pass
rewrites checked dates across pages it did not otherwise change, and mtime
would report every one of those as freshly modified content. An untracked or
uncommitted file falls back to mtime and says so under --verbose.

Usage:
    python3 tools/generate-sitemap.py           write the three files
    python3 tools/generate-sitemap.py --check   exit 1 if they are stale
    python3 tools/generate-sitemap.py --verbose report per-page decisions
    python3 tools/generate-sitemap.py --self-test

Exit codes: 0 written or current, 1 stale (--check) or self-test failure.
"""

import argparse
import importlib.util
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')

BASE = 'https://roomandrecourse.com'

# Directories never walked. Deploy debris and version control, not pages.
EXCLUDE_DIRS = {'.wrangler', 'node_modules', '.git', 'anchors'}

# Site-relative paths kept out of the sitemap by name. Deliberately short:
# every other exclusion is a rule a page declares about itself, or a status
# the retention manifests record. A path belongs here only when the page
# cannot state the case itself.
EXCLUDE_FROM_SITEMAP = {'404.html'}

# Kept out of _redirects as well: /404/ is not an address anyone should be
# sent to, and the not_found_handling setting serves the page directly.
EXCLUDE_FROM_REDIRECTS = {'404.html'}

PRIORITY_HOME = '1.0'
PRIORITY_INDEX = '0.8'
PRIORITY_LEGAL = '0.3'
PRIORITY_PAGE = '0.6'


# --- the file tree ----------------------------------------------------------

def html_files(site=SITE):
    """Every .html file under the deploy root, site-relative, sorted."""
    out = []
    for dirpath, dirnames, filenames in os.walk(site):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            if name.endswith('.html'):
                full = os.path.join(dirpath, name)
                out.append(os.path.relpath(full, site).replace(os.sep, '/'))
    return sorted(out)


# --- canonical URLs ---------------------------------------------------------

def canonical_path(rel):
    """The path a page is served at, under force-trailing-slash.

    Every HTML page ends in a slash. index.html is the directory it sits in;
    every other file is a directory of its own name.
    """
    if rel == 'index.html':
        return '/'
    if rel.endswith('/index.html'):
        return '/' + rel[:-len('index.html')]
    return '/' + rel[:-len('.html')] + '/'


def noncanonical_paths(rel):
    """The URL forms that should 301 to the canonical one.

    The .html form is the one that matters — it is what the hand-written
    sitemaps published — but the bare form is included too, so the redirect
    is a 301 rather than the platform's 307 in both cases.
    """
    canonical = canonical_path(rel)
    forms = ['/' + rel]                       # /states/ohio.html
    if not rel.endswith('/index.html') and rel != 'index.html':
        forms.append(canonical.rstrip('/'))   # /states/ohio
    return [f for f in forms if f != canonical]


def priority_for(rel):
    if rel == 'index.html':
        return PRIORITY_HOME
    if rel.startswith('legal/'):
        return PRIORITY_LEGAL
    if rel.endswith('/index.html'):
        return PRIORITY_INDEX
    if '/' not in rel:
        return PRIORITY_INDEX
    return PRIORITY_PAGE


# --- what is indexable ------------------------------------------------------

def declares_noindex(html):
    """True when a robots or googlebot meta tag lists noindex.

    Attribute order and quoting vary; content is a comma-separated token
    list. Parsed loosely on purpose — a page that half-declares noindex is
    treated as declaring it, because the safe reading of an ambiguous
    do-not-index signal is to honor it.
    """
    lowered = html.lower()
    at = 0
    while True:
        at = lowered.find('<meta', at)
        if at == -1:
            return False
        end = lowered.find('>', at)
        if end == -1:
            return False
        tag = lowered[at:end]
        at = end
        if 'name=' not in tag:
            continue
        if not ('robots' in tag or 'googlebot' in tag):
            continue
        content = tag.split('content=', 1)
        if len(content) < 2:
            continue
        value = content[1].strip().strip('"\'').split('"')[0].split("'")[0]
        if any(token.strip() == 'noindex' for token in value.split(',')):
            return True


def drifted_pages():
    """Site-relative paths of pages whose latest recorded pass is drift.

    Delegates to check-all.py rather than re-reading the manifests, so the
    two cannot disagree about what drift means or about which entry counts
    as the latest. `accepted` states are not returned: drifted_states()
    filters to drift alone, which is the distinction this wants.
    """
    path = os.path.join(ROOT, 'tools', 'check-all.py')
    if not os.path.isfile(path):
        return set()
    spec = importlib.util.spec_from_file_location('check_all', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    out = set()
    for slug in module.drifted_states():
        for page in module.pages_of(slug):
            rel = os.path.relpath(page, SITE).replace(os.sep, '/')
            if not rel.startswith('..') and rel.endswith('.html'):
                out.add(rel)
    return out


def indexable(site=SITE, verbose=False):
    """The pages the sitemap offers, with the reason for each omission."""
    drifted = drifted_pages()
    kept, dropped = [], []
    for rel in html_files(site):
        if rel in EXCLUDE_FROM_SITEMAP:
            dropped.append((rel, 'excluded by name'))
            continue
        if rel in drifted:
            dropped.append((rel, 'recorded as drift, awaiting rebuild'))
            continue
        with open(os.path.join(site, rel), encoding='utf-8') as fh:
            if declares_noindex(fh.read()):
                dropped.append((rel, 'declares noindex'))
                continue
        kept.append(rel)
    if verbose:
        for rel, why in dropped:
            print(f'  omitted {rel}: {why}', file=sys.stderr)
    # Home first, then section indexes, then everything alphabetically. Order
    # means nothing to a crawler; it means a readable diff to whoever reviews
    # the commit, which is the only reader who acts on this file.
    kept.sort(key=lambda rel: (rel != 'index.html',
                               not rel.endswith('/index.html'), rel))
    return kept, dropped


# --- dates ------------------------------------------------------------------

def git_date(rel, site=SITE):
    """The file's last commit date as YYYY-MM-DD, or None if git has none."""
    try:
        result = subprocess.run(
            ['git', '-C', ROOT, 'log', '-1', '--format=%cs', '--',
             os.path.join('site', rel)],
            capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    date = result.stdout.strip()
    return date or None


def lastmod_for(rel, site=SITE, verbose=False):
    date = git_date(rel, site)
    if date:
        return date
    if verbose:
        print(f'  {rel}: not committed, falling back to mtime', file=sys.stderr)
    import datetime
    stamp = os.stat(os.path.join(site, rel)).st_mtime
    return datetime.date.fromtimestamp(stamp).isoformat()


# --- rendering --------------------------------------------------------------

def render_sitemap(pages, site=SITE, verbose=False):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for rel in pages:
        lines += ['  <url>',
                  f'    <loc>{BASE}{canonical_path(rel)}</loc>',
                  f'    <lastmod>{lastmod_for(rel, site, verbose)}</lastmod>',
                  f'    <priority>{priority_for(rel)}</priority>',
                  '  </url>']
    lines += ['</urlset>', '']
    return '\n'.join(lines)


def render_robots():
    return (f'User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n')


def render_redirects(site=SITE):
    """A 301 for every non-canonical form of every published page.

    Written for all published pages, drifted ones included: a redirect is
    about which address a page has, not about whether it is offered to
    crawlers, and a drifted page is still served.
    """
    lines = ['# Generated by tools/generate-sitemap.py — do not edit by hand.',
             '# Cloudflare redirects these forms itself, but with a 307. These',
             '# rules make the same redirects permanent, so the .html URLs the',
             '# earlier hand-written sitemaps published pass their signal on',
             '# rather than staying live indexing candidates.',
             '']
    for rel in html_files(site):
        if rel in EXCLUDE_FROM_REDIRECTS:
            continue
        target = canonical_path(rel)
        for source in noncanonical_paths(rel):
            lines.append(f'{source} {target} 301')
    lines.append('')
    return '\n'.join(lines)


# --- write / check ----------------------------------------------------------

OUTPUTS = ('sitemap.xml', 'robots.txt', '_redirects')


def build(site=SITE, verbose=False):
    pages, dropped = indexable(site, verbose)
    return {
        'sitemap.xml': render_sitemap(pages, site, verbose),
        'robots.txt': render_robots(),
        '_redirects': render_redirects(site),
    }, pages, dropped


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true',
                        help='exit 1 if any output is stale; write nothing')
    parser.add_argument('--verbose', action='store_true',
                        help='report per-page omissions and date fallbacks')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    files, pages, dropped = build(SITE, args.verbose)

    if args.check:
        stale = []
        for name, content in files.items():
            path = os.path.join(SITE, name)
            current = None
            if os.path.isfile(path):
                with open(path, encoding='utf-8') as fh:
                    current = fh.read()
            if current != content:
                stale.append(name)
        if stale:
            print('stale, regenerate with tools/generate-sitemap.py: '
                  + ', '.join(sorted(stale)))
            return 1
        print(f'sitemap current: {len(pages)} URL(s), '
              f'{len(dropped)} page(s) omitted')
        return 0

    for name, content in files.items():
        with open(os.path.join(SITE, name), 'w', encoding='utf-8') as fh:
            fh.write(content)
    print(f'Wrote sitemap.xml ({len(pages)} URLs), robots.txt and _redirects '
          f'for {BASE}')
    if dropped:
        print(f'{len(dropped)} page(s) omitted from the sitemap:')
        for rel, why in dropped:
            print(f'  {rel}: {why}')
    return 0


# --- self-test --------------------------------------------------------------

def self_test():
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f'{label}: got {got!r}, wanted {want!r}')

    check('home', canonical_path('index.html'), '/')
    check('section index', canonical_path('states/index.html'), '/states/')
    check('state page', canonical_path('states/ohio.html'), '/states/ohio/')
    check('top-level page', canonical_path('about.html'), '/about/')
    check('nested page', canonical_path('legal/privacy.html'), '/legal/privacy/')

    check('state page forms', noncanonical_paths('states/ohio.html'),
          ['/states/ohio.html', '/states/ohio'])
    check('section index forms', noncanonical_paths('states/index.html'),
          ['/states/index.html'])
    check('home forms', noncanonical_paths('index.html'), ['/index.html'])

    check('priority home', priority_for('index.html'), PRIORITY_HOME)
    check('priority section', priority_for('states/index.html'), PRIORITY_INDEX)
    check('priority top-level', priority_for('about.html'), PRIORITY_INDEX)
    check('priority state', priority_for('states/ohio.html'), PRIORITY_PAGE)
    check('priority legal', priority_for('legal/terms.html'), PRIORITY_LEGAL)

    check('noindex plain', declares_noindex(
        '<meta name="robots" content="noindex, nofollow">'), True)
    check('noindex googlebot', declares_noindex(
        "<meta content='noindex' name='googlebot'>"), True)
    check('noindex absent', declares_noindex(
        '<meta name="robots" content="index, follow">'), False)
    check('noindex unrelated meta', declares_noindex(
        '<meta name="description" content="noindex is discussed here">'), False)
    check('no meta at all', declares_noindex('<p>noindex</p>'), False)

    # The generated sitemap must be well-formed XML and must not offer a page
    # that is not there. Both are cheap to assert and neither has ever been
    # asserted about the files this replaces.
    if os.path.isdir(SITE):
        xml = render_sitemap(html_files()[:3])
        try:
            ET.fromstring(xml)
        except ET.ParseError as err:
            failures.append(f'generated sitemap is not well-formed: {err}')

        pages, _ = indexable()
        for rel in pages:
            if not os.path.isfile(os.path.join(SITE, rel)):
                failures.append(f'sitemap offers a missing page: {rel}')

    if failures:
        print('SELF-TEST FAILED')
        for line in failures:
            print(f'  {line}')
        return 1
    print('self-test passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
