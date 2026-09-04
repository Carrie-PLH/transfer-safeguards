#!/usr/bin/env python3
"""Fetch published pages as a browser would and fail on any third-party request.

Why this exists, and why it is not part of predeploy-check.sh: the deploy gate
reads the HTML on disk. It is sound about what this project wrote and silent
about what a reader receives, because anything the CDN adds is added after the
files leave the repository. On 2026-09-04 Cloudflare Web Analytics was
injecting a beacon into every page on two of the four sites while both their
gates passed every check. See "A gate reads files; the CDN serves pages" in the
standard's CLAUDE.md.

This runs AFTER a deploy, against the live site.

Two things matter about how it fetches. It sends a real browser's User-Agent
and Accept header, because the injection that prompted this is
header-dependent: curl's defaults did not trigger it, and curl therefore
reported both affected sites clean before and after the fix. And it reads
LOADED resources only — script, link, img, iframe, source, video, audio, embed,
object, and CSS @import/url() — never plain anchors. Links in prose to source
documents are the product; flagging them would make the check unusable and
train people to ignore it.

Usage:
    python3 tools/check-live.py                 # the default sample of pages
    python3 tools/check-live.py --all           # every published page (slow)
    python3 tools/check-live.py --url URL ...   # specific pages
    python3 tools/check-live.py --self-test     # offline; no network

Exit status is 1 on any finding, so it can gate a routine.

Stdlib only, on purpose: it must run anywhere, including a sandbox with no
packages installed, and it must not itself introduce a dependency.
"""

import argparse
import re
import ssl
import sys
import urllib.error
import urllib.request

# --------------------------------------------------------------------------
# per-site configuration - the only part that differs between repositories

SITE = "roomandrecourse.com"
OWN_HOSTS = {"roomandrecourse.com", "www.roomandrecourse.com",
             "fieldassembly.net", "www.fieldassembly.net"}
# A small, cheap sample: the homepage, the indexes, and a couple of content
# pages. --all reads every page the site publishes.
SAMPLE = ["/", "/states/", "/federal.html", "/about.html", "/states/ohio.html"]

# --------------------------------------------------------------------------

BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
}

# Elements whose src/href causes the browser to fetch something.
LOADED = re.compile(
    rb'<(script|link|img|iframe|source|video|audio|embed|object)\b[^>]*?'
    rb'\b(?:src|href|data)\s*=\s*"([^"]+)"', re.I)

# Stylesheet imports and url() references inside inline CSS.
CSS_REF = re.compile(rb'(?:@import\s+|url\()\s*["\']?(https?://[^"\')\s]+)', re.I)

# rel values on <link> that navigate rather than load.
NAV_RELS = re.compile(rb'\brel\s*=\s*"(alternate|canonical|prev|next|me)"', re.I)

HOST_RE = re.compile(r'^[a-z]+://([^/]+)', re.I)


def host_of(url):
    m = HOST_RE.match(url)
    if not m:
        return None            # relative or data: - not a third-party fetch
    return m.group(1).lower().split("@")[-1].split(":")[0]


def findings(body, own_hosts):
    """Return [(element, url, host)] for every third-party loaded resource."""
    out = []
    for tag, ref in LOADED.findall(body):
        raw = ref.decode("utf-8", "replace")
        if raw.startswith("data:"):
            continue
        h = host_of(raw)
        if h and h not in own_hosts:
            out.append((tag.decode().lower(), raw, h))
    for ref in CSS_REF.findall(body):
        raw = ref.decode("utf-8", "replace")
        h = host_of(raw)
        if h and h not in own_hosts:
            out.append(("css", raw, h))
    return out


def strip_nav_links(body):
    """Drop <link rel="canonical"> and friends before scanning."""
    def keep(m):
        return b"" if NAV_RELS.search(m.group(0)) else m.group(0)
    return re.sub(rb'<link\b[^>]*>', keep, body, flags=re.I)


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=BROWSER_HEADERS)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def all_pages():
    """Every page the live states/institutions index links, plus the sample."""
    seen = list(SAMPLE)
    try:
        body = fetch(f"https://{SITE}/").decode("utf-8", "replace")
    except Exception:
        return seen
    for m in re.finditer(r'href="(/[^"#?]*\.html|/[a-z0-9/-]*)"', body):
        p = m.group(1)
        if p not in seen:
            seen.append(p)
    return seen


def run(paths, urls):
    targets = list(urls) + [f"https://{SITE}{p}" for p in paths]
    bad = 0
    for url in targets:
        try:
            body = fetch(url)
        except Exception as e:
            print(f"ERROR  {url}\n         could not fetch: {e}")
            bad += 1
            continue
        hits = findings(strip_nav_links(body), OWN_HOSTS)
        if hits:
            bad += 1
            print(f"FAIL   {url}")
            for tag, ref, h in hits:
                print(f"         <{tag}> -> {h}")
                print(f"           {ref}")
        else:
            print(f"ok     {url}")

    print()
    if bad:
        print(f"{bad} page(s) load something from a host this site does not own,")
        print("or could not be read. A third-party request on a published page is")
        print("a finding whether or not this repository put it there: the CDN can")
        print("inject one after the files leave. Read the host before assuming a")
        print("mistake in the pages - the 2026-09-04 case was Cloudflare Web")
        print("Analytics, disabled per zone in the dashboard, with nothing to fix")
        print("in the repository at all.")
        return 1
    print(f"{len(targets)} page(s) checked; nothing loaded from any other host.")
    return 0


def self_test():
    own = {"example.com", "www.example.com"}
    cases = [
        (b'<link rel="stylesheet" href="/assets/style.css">', 0, "own stylesheet"),
        (b'<a href="https://codes.ohio.gov/x">the rule</a>', 0,
         "anchor to a source document is the product, not a finding"),
        (b'<link rel="canonical" href="https://example.com/x">', 0, "canonical"),
        (b'<img src="data:image/png;base64,AAAA">', 0, "data uri"),
        (b'<script type="module" src="https://static.cloudflareinsights.com/'
         b'beacon.min.js/v1"></script>', 1, "the RUM beacon"),
        (b'<link rel="stylesheet" href="https://fonts.googleapis.com/css">', 1,
         "third-party font stylesheet"),
        (b'<img src="https://tracker.test/pixel.gif">', 1, "tracking pixel"),
        (b'<style>@import url(https://cdn.test/a.css);</style>', 1, "css import"),
        (b'<iframe src="https://player.test/embed"></iframe>', 1, "iframe"),
        (b'<img src="/assets/a.png"><script src="/assets/b.js"></script>', 0,
         "relative assets"),
    ]
    bad = 0
    for body, want, label in cases:
        got = len(findings(strip_nav_links(body), own))
        ok = (got > 0) == (want > 0)
        if not ok:
            bad += 1
        print(f"{'ok  ' if ok else 'FAIL'}  {label}: expected "
              f"{'a finding' if want else 'none'}, got {got}")
    print()
    print("self-test: PASS" if not bad else f"self-test: {bad} FAILURE(S)")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="every published page")
    ap.add_argument("--url", action="append", default=[], help="check this URL")
    ap.add_argument("--self-test", action="store_true", help="offline checks")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.url:
        return run([], args.url)
    return run(all_pages() if args.all else SAMPLE, [])


if __name__ == "__main__":
    sys.exit(main())
