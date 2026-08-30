#!/usr/bin/env python3
"""Redraw the Room & Recourse raster icons from the door glyph.

The glyph is the icon carving of the door in site/assets/roomandrecourse-wordmark.svg,
and is identical to what site/assets/favicon.svg draws: the swung panel filled
solid with the knob knocked out of it, and the doorway frame left as a stroke in
the dimmer rose. The lockup's own linework does not survive a 16px rendering,
which is why the icon fills rather than strokes the panel. Nothing here traces a
bitmap: the icons are drawn, in the lockup's own coordinates, so they can be
regenerated at any size by anyone with Pillow and no other tool.

Writes, into site/assets/:
    favicon-16.png, favicon-32.png, favicon.ico,
    apple-touch-icon.png (180px), icon-512.png

Usage:  python3 tools/make-icons.py
"""

from pathlib import Path
from PIL import Image, ImageDraw

BG = (23, 16, 19)        # site ground   #171013
INK = (224, 170, 181)    # accent        #e0aab5
DIM = (162, 111, 124)    # accent-dim    #a26f7c

# Source-coordinate geometry; site/assets/favicon.svg draws the same three.
FRAME = [(184.5, 349.5), (117.5, 349.5), (117.5, 565)]   # doorway, stroked
FRAME_STROKE = 24
PANEL = [(184.5, 315), (281, 349), (281, 559), (184.5, 593)]  # swung, filled
KNOB = (252, 456, 16)                                     # cx, cy, r, knocked out

# Glyph extent including the frame's stroke, and how much of the box it fills.
GLYPH_BOX = (105.5, 303, 293, 605)
GLYPH_FILL = 0.84

SUPERSAMPLE = 4


def render(size: int) -> Image.Image:
    n = size * SUPERSAMPLE
    img = Image.new("RGB", (n, n), BG)
    d = ImageDraw.Draw(img)

    x0, y0, x1, y1 = GLYPH_BOX
    s = GLYPH_FILL * n / (y1 - y0)
    tx = n / 2 - s * (x0 + x1) / 2
    ty = n / 2 - s * (y0 + y1) / 2
    def pt(p):
        return (tx + s * p[0], ty + s * p[1])

    w = max(1, round(FRAME_STROKE * s))
    d.line([pt(p) for p in FRAME], fill=DIM, width=w, joint="curve")
    for p in FRAME:                      # square off the ends and the corner
        cx, cy = pt(p)
        d.rectangle([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2], fill=DIM)

    d.polygon([pt(p) for p in PANEL], fill=INK)

    kx, ky = pt((KNOB[0], KNOB[1]))
    kr = KNOB[2] * s
    d.ellipse([kx - kr, ky - kr, kx + kr, ky + kr], fill=BG)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    assets = Path(__file__).resolve().parent.parent / "site" / "assets"
    render(512).save(assets / "icon-512.png")
    render(180).save(assets / "apple-touch-icon.png")
    render(32).save(assets / "favicon-32.png")
    render(16).save(assets / "favicon-16.png")
    render(64).save(assets / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("wrote icon-512.png, apple-touch-icon.png, favicon-32.png, "
          "favicon-16.png, favicon.ico to", assets)


if __name__ == "__main__":
    main()
