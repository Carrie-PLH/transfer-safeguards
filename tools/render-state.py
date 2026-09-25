#!/usr/bin/env python3
"""Render the repository's constrained jurisdiction Markdown into its static HTML shell."""
from pathlib import Path
import html, re, sys

ROOT = Path(__file__).resolve().parents[1]

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def display_date(s):
    """Format an ISO checked date as the house display form, e.g. 'Aug 30, 2026'.

    Anything that is not a bare ISO date is returned untouched, so a docket line
    already carrying the display form (or any other wording) passes through.
    """
    m = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})\.?', s.strip())
    if not m:
        return s
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not 1 <= month <= 12:
        return s
    return f"{_MONTHS[month - 1]} {day}, {year}"


def inline(s):
    s = html.escape(s, quote=False)
    # An address may carry one level of parentheses (westlaw's contextData=(sc.Default),
    # a PDF named "Brochure(2).pdf"); [^)]+ cut such links at the first ")" (2026-09-25).
    s = re.sub(r'\[([^]]+)\]\((https?://(?:[^()\s]|\([^()\s]*\))+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    # Same-site and mailto targets. Before this, only http(s) markdown links
    # were converted and every other form fell through to the page as literal
    # "[text](target)" — 66 of them were published that way. Internal targets
    # are canonicalised to the root-absolute trailing-slash URL the site
    # actually serves, since a relative one breaks under the redirects.
    s = re.sub(r'\[([^]]+)\]\((mailto:[^)]+)\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r'\[([^]]+)\]\((/[^)]*)\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r'\[([^]]+)\]\((?:\.\./)?([a-z0-9\-]+(?:/[a-z0-9\-]+)*)\.html\)',
               lambda m: '<a href="/%s/">%s</a>' % (m.group(2), m.group(1)), s)
    # Strict boundaries, adopted from the Board & Border sibling 2026-09-06:
    # an opening marker must be followed by a non-space and a closing one
    # preceded by a non-space. This is what keeps a quoted source's own
    # trailing asterisks literal — California's fee schedule on the sibling
    # prints "$225.00**" as footnote markers, and the looser pattern pairs
    # them across table cells and falsifies the quotation. No source here
    # trips it yet; the guard exists so the first one that does cannot.
    s = re.sub(r'\*\*(?=\S)([^*]+?)(?<=\S)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*(?=\S)([^*]+?)(?<=\S)\*(?!\*)', r'<em>\1</em>', s)
    # Backtick spans. Without this a source that uses backticks publishes them
    # as literal characters, the same way markdown links did until 2026-09-05.
    # No quoted passage in any source contains a backtick, so this cannot
    # reach inside quoted material and disturb quotation fidelity.
    s = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', s)
    return s

def paras(lines):
    out=[]; buf=[]; i=0
    def flush():
        if buf:
            txt=' '.join(x.strip() for x in buf); buf.clear()
            cls='standing' if txt.startswith('*The three rows') else 'mw'
            out.append(f'<p class="{cls}">{inline(txt)}</p>')
    while i < len(lines):
        line=lines[i]
        if line.startswith('### '):
            flush(); out.append(f'<h3>{inline(line[4:])}</h3>'); i+=1; continue
        if line.startswith('| '):
            flush(); rows=[]
            while i<len(lines) and lines[i].startswith('| '):
                rows.append([x.strip() for x in lines[i].strip('|').split('|')]); i+=1
            heads=rows[0]; body=rows[2:]
            out.append('<div class="table-scroll"><table><thead><tr>'+''.join(f'<th>{inline(x)}</th>' for x in heads)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{inline(x)}</td>' for x in row)+'</tr>' for row in body)+'</tbody></table></div>'); continue
        if not line.strip(): flush()
        else: buf.append(line)
        i+=1
    flush(); return ''.join(out)

def describe(sections, fallback):
    """Meta description from the page's own Lede: its opening, plain text,
    cut at a word boundary near 160 characters (FA-D-20260922-05). The Lede
    is the page's summary in the page's words; the fallback is used only
    when a page has no Lede."""
    body = [l for t, b in sections if t.split(' {')[0] == 'Lede' for l in b if l.strip()]
    t = ' '.join(x.strip() for x in body)
    t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)   # [text](url) -> text
    t = re.sub(r'(\*\*|\*|__|_|`)(.+?)\1', r'\2', t)    # emphasis and code
    t = re.sub(r'\s+', ' ', t).strip()
    if not t:
        return fallback
    # Every Lede opens 'This page assembles ...'; the snippet reads better
    # starting at what it assembles, and the 160 characters go further.
    if t.startswith('This page assembles '):
        t = t[len('This page assembles '):]
        t = t[0].upper() + t[1:]
    if len(t) > 160:
        t = t[:157].rsplit(' ', 1)[0].rstrip(' ,;:(') + '\u2026'
    return html.escape(html.unescape(t), quote=True)

def render(slug):
    # The federal layer page lives at the repo root (federal.md) and renders
    # to site/federal.html; state pages live in states/ and render to
    # site/states/. Asset and nav paths differ by one directory level.
    federal = (slug == 'federal')
    src = (ROOT/'federal.md') if federal else (ROOT/'states'/f'{slug}.md')
    md=src.read_text(); lines=md.splitlines(); state=lines[0][2:]
    sections=[]; current=None
    for line in lines[1:]:
        if line.startswith('## '):
            if current: sections.append(current)
            current=[line[3:],[]]
        elif current is not None: current[1].append(line)
    if current: sections.append(current)
    chunks=[]
    for title, body in sections:
        if title=='Docket':
            entries=[]; note=[]
            for line in body:
                m=re.match(r'\*\*(.+?)\.\*\*\s*(.*)',line)
                if m: entries.append((m.group(1),m.group(2)))
                elif line.strip(): note.append(line)
            checked_attr=' class="docket-checked"'
            # House display format for checked dates is "Aug 30, 2026" across all four
            # sites. The markdown docket keeps ISO; only the rendered value is formatted.
            entries=[(k, display_date(v) if k=="Sources last checked" else v) for k,v in entries]
            dl=''.join(f'<div><dt>{inline(k)}</dt><dd{(checked_attr if k=="Sources last checked" else "")}>{inline(v)}</dd></div>' for k,v in entries)
            chunks.append(f'<section class="section reveal"><div class="section-no"></div><div><h1>{state}</h1><dl class="docket">{dl}</dl><p class="docket-note">{inline(" ".join(note))}</p></div></section>')
        else:
            if title=='Lede': no='Lede<small>What this page holds</small>'; cls='section reveal'; heading='Lede'
            else:
                m=re.match(r'(\d+) — (.*)',title); no=f'{m.group(1)}<small>{m.group(2)}</small>'; cls='section'; heading=m.group(2)
            chunks.append(f'<section class="{cls}"><div class="section-no">{no}</div><div><h2>{heading}</h2>{paras(body)}</div></section>')
    # Root-absolute canonical URLs. _redirects 301s every page to a
    # trailing-slash URL, which shifts the base path a level deeper and breaks
    # any relative ref. Absolute paths are correct under either URL shape.
    states_href = '/states/'
    # <title> pattern and <link rel="canonical"> are owned by
    # field-assembly-standard/tools/apply-seo-head.py (FA-D-20260922-05); the
    # predeploy gate runs its --check, so keep the two in step. The DC page
    # records a hearing route, not one described as an appeal.
    if federal:
        title = f'{state} — nursing-home transfer and discharge safeguards — Room &amp; Recourse'
        canonical = 'https://roomandrecourse.com/federal/'
    else:
        route = 'hearing' if slug == 'district-of-columbia' else 'appeal'
        title = f'{state} nursing home discharge and transfer rules: notice, {route}, ombudsman — Room &amp; Recourse'
        canonical = f'https://roomandrecourse.com/states/{slug}/'
    federal_href = '/federal/'
    if federal:
        desc = 'The federal floor for nursing-home involuntary transfer and discharge — 42 CFR 483.15(c), 42 CFR part 431 subpart E, and CMS guidance — quoted and linked to first-party sources.'
        limits = 'Reference information, not legal or medical advice. Independent of every facility and operator, of CMS and every state agency, and of the ombudsman programs.'
    else:
        desc = describe(sections, f'{state} nursing-home involuntary transfer and discharge procedure, quoted and linked to first-party sources.')
        limits = f'Reference information, not legal or medical advice. Independent of every facility and operator, of CMS and every {state} state agency, and of the ombudsman programs.'
    doc=f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title><link rel="canonical" href="{canonical}"><meta name="description" content="{desc}"><link rel="icon" href="/assets/favicon.ico" sizes="any"><link rel="icon" href="/assets/favicon-32.png" type="image/png" sizes="32x32"><link rel="icon" href="/assets/favicon-16.png" type="image/png" sizes="16x16"><link rel="apple-touch-icon" href="/assets/apple-touch-icon.png"><link rel="stylesheet" href="/assets/style.css"></head><body><a class="skip-link" href="#main">Skip to content</a><header class="topline"><a class="wordmark" href="/">ROOM &amp; RECOURSE</a><input class="nav-toggle" type="checkbox" id="nav-toggle" aria-label="Menu"><label class="nav-button" for="nav-toggle"><span class="nav-bars"></span>Menu</label><nav><a href="{states_href}">States</a><a href="{federal_href}">The federal floor</a><a href="/about/">About</a></nav></header><main id="main">{''.join(chunks)}</main><footer class="colophon"><div class="rows"><div><p class="mark">ROOM &amp; RECOURSE</p><p style="margin-top:0.85rem;">A project of <a href="https://fieldassembly.net" target="_blank" rel="noopener">Field Assembly LLC</a>. Kept to <a href="https://fieldassembly.net/standard.html" target="_blank" rel="noopener">the published record standard</a>.</p><p>Free permanently &mdash; no accounts, no ads, no analytics. Every quotation above carries a capture date that can be verified independently &mdash; <a href="https://fieldassembly.net/permanence" target="_blank" rel="noopener">how we've bound ourselves</a>.</p><p><a href="mailto:hello@fieldassembly.net">hello@fieldassembly.net</a></p><p><a href="/legal/privacy/">Privacy</a> &middot; <a href="/legal/terms/">Terms</a></p></div><div><p class="foot-label">The limits</p><p>{limits}</p></div></div></footer></body></html>'''
    out = (ROOT/'site'/'federal.html') if federal else (ROOT/'site'/'states'/f'{slug}.html')
    out.write_text(doc)
    apply_search_head(out.relative_to(ROOT/'site').as_posix(), out)


# The search block (Open Graph, Twitter, JSON-LD) is owned by the shared
# tool field-assembly-standard/tools/apply-seo-head.py, which the deploy gate
# also runs on a fresh render before comparing. Applied here when the
# sibling checkout is present so a re-render leaves the page deploy-ready;
# absent (the gate's scratch tree), the gate applies it itself.
SEO_TOOL = ROOT.parent / 'field-assembly-standard' / 'tools' / 'apply-seo-head.py'
def apply_search_head(rel, path):
    if SEO_TOOL.exists():
        import subprocess
        subprocess.run([sys.executable, str(SEO_TOOL), '--site', 'transfer-safeguards', '--rel', rel, '--file', str(path)],
                       check=True, capture_output=True)

if __name__=='__main__':
    for arg in sys.argv[1:]: render(arg)
