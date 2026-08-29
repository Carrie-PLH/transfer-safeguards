#!/usr/bin/env python3
"""Render the repository's constrained jurisdiction Markdown into its static HTML shell."""
from pathlib import Path
import html, re, sys

ROOT = Path(__file__).resolve().parents[1]

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\[([^]]+)\]\((https?://[^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*', r'<em>\1</em>', s)
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
            out.append('<div class="table-wrap"><table><thead><tr>'+''.join(f'<th>{inline(x)}</th>' for x in heads)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{inline(x)}</td>' for x in row)+'</tr>' for row in body)+'</tbody></table></div>'); continue
        if not line.strip(): flush()
        else: buf.append(line)
        i+=1
    flush(); return ''.join(out)

def render(slug):
    md=(ROOT/'states'/f'{slug}.md').read_text(); lines=md.splitlines(); state=lines[0][2:]
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
            dl=''.join(f'<div><dt>{inline(k)}</dt><dd{(" class=\"docket-checked\"" if k=="Sources last checked" else "")}>{inline(v)}</dd></div>' for k,v in entries)
            chunks.append(f'<section class="section reveal"><div class="section-no"></div><div><h1>{state}</h1><dl class="docket">{dl}</dl><p class="docket-note">{inline(" ".join(note))}</p></div></section>')
        else:
            if title=='Lede': no='Lede<small>What this page holds</small>'; cls='section reveal'; heading='Lede'
            else:
                m=re.match(r'(\d+) — (.*)',title); no=f'{m.group(1)}<small>{m.group(2)}</small>'; cls='section'; heading=m.group(2)
            chunks.append(f'<section class="{cls}"><div class="section-no">{no}</div><div><h2>{heading}</h2>{paras(body)}</div></section>')
    doc=f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{state} — nurse licensure endorsement and mobility — Board &amp; Border</title><meta name="description" content="{state} nurse licensure endorsement and mobility, quoted and linked to first-party sources."><link rel="icon" href="../assets/favicon.ico" sizes="any"><link rel="stylesheet" href="../assets/style.css"></head><body><a class="skip-link" href="#main">Skip to content</a><header class="topline"><a class="wordmark" href="../index.html"><img src="../assets/logo-lockup.png" alt="Board &amp; Border" width="653" height="132"></a><nav><a href="index.html">States</a><a href="../compact.html">The compact</a><a href="../about.html">About</a></nav></header><main id="main">{''.join(chunks)}</main><footer class="colophon"><div class="rows"><div><img class="mark" src="../assets/logo-lockup.png" alt="" width="653" height="132"><p>A project of <a href="https://fieldassembly.net" target="_blank" rel="noopener">Field Assembly LLC</a>.</p><p><a href="mailto:hello@fieldassembly.net">hello@fieldassembly.net</a></p><p><a href="../legal/privacy.html">Privacy</a> &middot; <a href="../legal/terms.html">Terms</a></p></div><div><p class="foot-label">The limits</p><p>Reference information, not legal or professional advice. Independent of the {state} nursing regulator, of the compact commission, of staffing agencies, and of employers.</p></div></div></footer></body></html>'''
    (ROOT/'site'/'states'/f'{slug}.html').write_text(doc)

if __name__=='__main__':
    for arg in sys.argv[1:]: render(arg)
