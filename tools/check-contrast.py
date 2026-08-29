#!/usr/bin/env python3
"""WCAG 2.1 AA contrast check for the site's colour tokens.

Reads the :root token block in site/assets/style.css and verifies:
  - every text token (--text, --text-dim, --accent, --accent-muted) is
    >= 4.5:1 against every ground painted on the site (--bg, --bg-raise,
    --bg-inset), per SC 1.4.3;
  - every interactive-edge token (--edge, --accent-dim) is >= 3:1 against
    every ground, per SC 1.4.11;
  - the selection pair (--bg text on --accent ground) is >= 4.5:1.
--accent-dim is never used as text (standing rule in the stylesheet); it is
checked only as an edge.

Run from anywhere: python3 tools/check-contrast.py
Exit 0 with a one-line summary, 1 with the failing pairs listed.
"""

import pathlib
import re
import sys

CSS = pathlib.Path(__file__).resolve().parent.parent / "site" / "assets" / "style.css"

TEXT_TOKENS = ["text", "text-dim", "accent", "accent-muted"]
EDGE_TOKENS = ["edge", "accent-dim"]
GROUNDS = ["bg", "bg-raise", "bg-inset"]


def tokens(css):
    m = re.search(r':root\s*{(.*?)}', css, re.S)
    if not m:
        raise SystemExit("no :root block found in " + str(CSS))
    return dict(re.findall(r'--([a-z-]+):\s*(#[0-9a-fA-F]{6})', m.group(1)))


def luminance(hexcolor):
    r, g, b = (int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def main():
    tok = tokens(CSS.read_text(encoding="utf-8"))
    missing = [t for t in TEXT_TOKENS + EDGE_TOKENS + GROUNDS if t not in tok]
    if missing:
        print("missing tokens: " + ", ".join(missing))
        return 1
    fails, checked = [], 0
    for t, floor in [(t, 4.5) for t in TEXT_TOKENS] + [(t, 3.0) for t in EDGE_TOKENS]:
        for g in GROUNDS:
            r = ratio(tok[t], tok[g])
            checked += 1
            if r < floor:
                fails.append(f"--{t} on --{g}: {r:.2f} < {floor}")
    r = ratio(tok["bg"], tok["accent"])
    checked += 1
    if r < 4.5:
        fails.append(f"selection (--bg on --accent): {r:.2f} < 4.5")
    if fails:
        print("\n".join(fails))
        return 1
    print(f"contrast: all {checked} token pairs pass AA "
          f"(text >=4.5:1, edges >=3:1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
