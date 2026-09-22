#!/usr/bin/env python3
"""Regenerate the extension's icons.

    python3 tools/rudder-helper/icons/make-icons.py

A rounded square holding two columns with a tick between them: the two responses
this extension rates, and the preference it records. Drawn at 8x and downsampled
so the 16px icon stays clean.

Needs Pillow. Any interpreter that has it will do.
"""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SIZES = (16, 32, 48, 128)
BG = (43, 95, 158, 255)  # the popup's accent blue
FG = (255, 255, 255, 255)
DIM = (255, 255, 255, 110)
SS = 8


def draw(px: int) -> Image.Image:
    n = px * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, n - 1, n - 1], radius=int(n * 0.22), fill=BG)

    pad = n * 0.22
    gap = n * 0.08
    col_w = (n - 2 * pad - gap) / 2
    top = pad
    bot = n - pad

    # Two response columns. The left one is filled solid: the preferred side.
    d.rounded_rectangle([pad, top, pad + col_w, bot], radius=n * 0.06, fill=FG)
    d.rounded_rectangle(
        [pad + col_w + gap, top, pad + 2 * col_w + gap, bot],
        radius=n * 0.06,
        outline=DIM,
        width=max(1, int(n * 0.035)),
    )
    return img.resize((px, px), Image.LANCZOS)


def main() -> int:
    for px in SIZES:
        path = HERE / f"icon{px}.png"
        draw(px).save(path)
        print(f"wrote {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
