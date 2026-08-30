#!/usr/bin/env python3
"""Redraw the Room & Recourse raster icons from the door glyph.

The glyph is the same geometry carried by site/assets/favicon.svg and the door
half of site/assets/roomandrecourse-wordmark.svg, expressed in the coordinates
of the original lockup art. Nothing here traces a bitmap: the icons are drawn,
so they can be regenerated at any size by anyone with Pillow and no other tool.

Writes, into site/assets/:
    favicon-16.png, favicon-32.png, favicon.ico,
    apple-touch-icon.png (180px), icon-512.png

Usage:  python3 tools/make-icons.py
"""

from pathlib import Path
from PIL import Image, ImageDraw

BG = (23, 16, 19)        # --bg      #171013
INK = (224, 170, 181)    # --accent  #e0aab5

# Source-coordinate geometry (see site/assets/favicon.svg for the same paths).
DOOR_BOX = (112, 313, 287, 594)          # x0, y0, x1, y1 of the glyph's ink
STROKE = 20                              # widened from the lockup's 9.5 so the
                                         # glyph survives a 16px rendering
PATHS = [
    [(184.5, 313), (184.5, 594)],                                  # hinge jamb
    [(184.5, 349.5), (117.5, 349.5), (117.5, 565)],                # doorway frame
    [(184.5, 315), (281, 349), (281, 559), (184.5, 593)],          # swung panel
]
KNOB = (252, 456, 14)                    # cx, cy, r

SUPERSAMPLE = 4
GLYPH_FILL = 0.75                        # glyph height as a share of the icon


def render(size: int) -> Image.Image:
    n = size * SUPERSAMPLE
    img = Image.new("RGB", (n, n), BG)
    d = ImageDraw.Draw(img)

    x0, y0, x1, y1 = DOOR_BOX
    s = GLYPH_FILL * n / (y1 - y0)
    tx = n / 2 - s * (x0 + x1) / 2
    ty = n / 2 - s * (y0 + y1) / 2
    def pt(p):
        return (tx + s * p[0], ty + s * p[1])

    w = max(1, round(STROKE * s))
    for path in PATHS:
        d.line([pt(p) for p in path], fill=INK, width=w, joint="curve")
        for p in path:                   # square off the ends and corners
            cx, cy = pt(p)
            d.rectangle([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2], fill=INK)

    kx, ky = pt((KNOB[0], KNOB[1]))
    kr = KNOB[2] * s
    d.ellipse([kx - kr, ky - kr, kx + kr, ky + kr], fill=INK)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    assets = Path(__file__).resolve().parent.parent / "site" / "assets"
    render(512).save(assets / "icon-512.png")
    render(180).save(assets / "apple-touch-icon.png")
    render(32).save(assets / "favicon-32.png")
    render(16).save(assets / "favicon-16.png")
    render(64).save(
        assets / "favicon.ico",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )
    print("wrote icon-512.png, apple-touch-icon.png, favicon-32.png, "
          "favicon-16.png, favicon.ico to", assets)


if __name__ == "__main__":
    main()
