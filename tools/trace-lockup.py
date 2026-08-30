#!/usr/bin/env python3
"""Trace the Room & Recourse lockup art into the site's wordmark SVG.

Reads site/assets/roomandrecourse.png — the owner's original lockup — and writes
site/assets/roomandrecourse-wordmark.svg as filled outlines in the art's own
pixel coordinates. Outlines rather than live text: the mark then carries no font
dependency and renders identically wherever it is opened, which is the point of
a lockup and the rule the rest of this corpus keeps.

Colour is not traced. Each shape is classified by where it sits and what colour
the art paints it, then filled from the site's own tokens in assets/style.css so
the mark reads on the dark ground:

    door glyph      accent to accent-dim gradient   (the art carries one too)
    threshold dash  accent-dim   #a26f7c
    ROOM            text         #efe8ea            (near-black in the art)
    ampersand       accent-muted #d097a3            (pale rose in the art)
    RECOURSE        accent       #e0aab5            (deep rose in the art)

Run in a throwaway environment so the host stays clean; potracer is a pure-Python
port of potrace and is needed only to retrace, never to serve the site:

    python3 -m venv /tmp/rrtrace
    /tmp/rrtrace/bin/pip install pillow numpy potracer
    /tmp/rrtrace/bin/python tools/trace-lockup.py

tools/make-icons.py draws the icon carving separately and does not use this.
"""

from pathlib import Path

import numpy as np
import potrace
from PIL import Image

UPSAMPLE = 4          # trace at 4x, emit at 1x, so the curves come out smooth
INK_MAX = 600         # RGB sum below this is ink, not paper
DOOR_MAX_X = 320      # shapes left of here are the door
DASH_MAX_X = 420      # and between there and here, the threshold dash
PALE_MIN = 430        # an inked pixel this bright is the pale-rose ampersand
DARK_MAX = 200        # this dark is the near-black ROOM

GRADIENT = "url(#rr-door)"
DASH = "#a26f7c"
TEXT = "#efe8ea"
MUTED = "#d097a3"
ACCENT = "#e0aab5"


def classify(cx, mean_sum):
    """Which token fills the shape whose centre is cx and mean ink is mean_sum."""
    if cx < DOOR_MAX_X:
        return GRADIENT
    if cx < DASH_MAX_X:
        return DASH
    if mean_sum < DARK_MAX:
        return TEXT
    if mean_sum > PALE_MIN:
        return MUTED
    return ACCENT


def path_d(curves, scale):
    """One SVG path from an outer curve and the counters cut out of it."""
    def xy(p):
        return p.x / scale, p.y / scale

    out = []
    for curve in curves:
        x, y = xy(curve.start_point)
        out.append(f"M{x:.1f} {y:.1f}")
        for seg in curve:
            ex, ey = xy(seg.end_point)
            if seg.is_corner:
                cx, cy = xy(seg.c)
                out.append(f"L{cx:.1f} {cy:.1f}L{ex:.1f} {ey:.1f}")
            else:
                ax, ay = xy(seg.c1)
                bx, by = xy(seg.c2)
                out.append(f"C{ax:.1f} {ay:.1f} {bx:.1f} {by:.1f} {ex:.1f} {ey:.1f}")
        out.append("Z")
    return "".join(out)


def main():
    root = Path(__file__).resolve().parent.parent
    src = root / "site" / "assets" / "roomandrecourse.png"
    dst = root / "site" / "assets" / "roomandrecourse-wordmark.svg"

    rgb = np.asarray(Image.open(src).convert("RGB")).astype(int)
    ink = rgb.sum(2) < INK_MAX
    ys, xs = np.nonzero(ink)
    box = (xs.min(), ys.min(), xs.max(), ys.max())
    print("ink bbox", box)

    big = Image.fromarray((ink * 255).astype("uint8")).resize(
        (ink.shape[1] * UPSAMPLE, ink.shape[0] * UPSAMPLE), Image.LANCZOS)
    bitmap = potrace.Bitmap(np.asarray(big) > 127)
    path = bitmap.trace(turdsize=8, alphamax=1.0)

    # potracer hands back a flat list of boundaries — a shape's outline and the
    # counters cut out of it are siblings, not parent and child, and the first
    # is the page border itself. Drop the border, sort the rest into colour
    # groups, and let fill-rule="evenodd" subtract each counter from the letter
    # or stroke that encloses it.
    shapes = {}
    for curve in path:
        pts = np.array([(p.x, p.y) for p in
                        [curve.start_point] + [s.end_point for s in curve]]
                       ) / UPSAMPLE
        x0, y0 = pts.min(0)
        x1, y1 = pts.max(0)
        if x0 <= 0 and y0 <= 0:                  # the page border potrace adds
            continue
        region = rgb[int(y0):int(y1) + 1, int(x0):int(x1) + 1].reshape(-1, 3)
        inked = region[region.sum(1) < INK_MAX]
        mean_sum = float(inked.sum(1).mean()) if len(inked) else 255 * 3
        fill = classify((x0 + x1) / 2, mean_sum)
        shapes.setdefault(fill, []).append(path_d([curve], UPSAMPLE))

    order = [GRADIENT, DASH, TEXT, MUTED, ACCENT]
    label = {GRADIENT: "door", DASH: "threshold", TEXT: "ROOM",
             MUTED: "ampersand", ACCENT: "RECOURSE"}
    for fill in order:
        print(f"  {label[fill]:10s} {len(shapes.get(fill, []))} boundaries")

    x0, y0, x1, y1 = box
    pad = 4
    vb = (x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vb[2]}" height="{vb[3]}"'
        f' viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" role="img"'
        ' aria-labelledby="title desc">',
        "  <title id=\"title\">Room &amp; Recourse</title>",
        "  <desc id=\"desc\">An open door beside a dashed threshold line and the"
        " joined Room and Recourse wordmark.</desc>",
        "  <!-- Generated by tools/trace-lockup.py from assets/roomandrecourse.png;"
        " do not hand-edit.",
        "       Outlines, not live text, so the lockup carries no font dependency."
        " Colours are",
        "       the site tokens, not the art's: see the script for the mapping. -->",
        '  <defs>',
        '    <linearGradient id="rr-door" x1="0" y1="0" x2="1" y2="1">',
        '      <stop offset="0" stop-color="#e0aab5"/>',
        '      <stop offset="1" stop-color="#a26f7c"/>',
        '    </linearGradient>',
        '  </defs>',
    ]
    for fill in order:
        ds = shapes.get(fill)
        if not ds:
            continue
        # One path per group: evenodd needs the counters in the same path as the
        # shape they punch through.
        lines.append(f'  <path fill="{fill}" fill-rule="evenodd" d="{"".join(ds)}"/>')
    lines.append("</svg>")

    dst.write_text("\n".join(lines) + "\n")
    print("wrote", dst, dst.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
