"""
Generate app icons for DisplayPresets.

Usage:
    python scripts/generate_icons.py

Outputs:
    electron-app/public/icon.ico      (multi-size, for window / taskbar)
    electron-app/public/icon.png      (256x256, general use)
    electron-app/public/tray-icon.png (32x32, system tray)

Requires Pillow:
    pip install pillow
"""

import math
import struct
import io
import os
from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Accent color matching the app theme
# ---------------------------------------------------------------------------

BG_COLOR    = (0, 118, 210, 255)   # blue accent
FG_COLOR    = (255, 255, 255, 255) # white
FG_DIM      = (255, 255, 255, 180) # white, slightly transparent


# ---------------------------------------------------------------------------
# Icon drawing
# ---------------------------------------------------------------------------

def draw_icon(size: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded background
    radius = max(2, int(size * 0.18))
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=BG_COLOR)

    # --- Two monitor outlines ---
    lw      = max(1, int(size * 0.055))  # border thickness
    pad     = size * 0.09
    gap     = size * 0.05
    mid     = size / 2
    mw      = (mid - pad - gap / 2)
    mh      = mw * 0.62
    mt      = size * 0.16

    # Monitors share a bottom line (no stand at small sizes)
    for mx in (pad, mid + gap / 2):
        draw.rounded_rectangle(
            [mx, mt, mx + mw, mt + mh],
            radius=max(1, int(size * 0.04)),
            outline=FG_COLOR,
            width=lw,
        )

    # --- Horizontal preset lines inside each monitor ---
    n_lines  = 3 if size >= 32 else 2
    line_pad = mw * 0.18
    line_lh  = max(1, int(size * 0.04))
    spacing  = (mh - 2 * mw * 0.2) / (n_lines + 1)

    for mx in (pad, mid + gap / 2):
        lx0 = mx + line_pad
        lx1 = mx + mw - line_pad
        for j in range(n_lines):
            ly = mt + mw * 0.18 + spacing * (j + 1)
            draw.rectangle(
                [lx0, ly - line_lh // 2, lx1, ly + line_lh // 2],
                fill=FG_DIM,
            )

    # --- Small stand below each monitor (only at >= 48px) ---
    if size >= 48:
        stand_w  = max(lw, int(size * 0.04))
        stand_t  = mt + mh
        stand_b  = size * 0.82
        base_hw  = mw * 0.28
        base_h   = max(lw, int(size * 0.04))

        for mx in (pad, mid + gap / 2):
            cx = mx + mw / 2
            # vertical stem
            draw.rectangle(
                [cx - stand_w // 2, stand_t, cx + stand_w // 2, stand_b],
                fill=FG_DIM,
            )
            # horizontal base
            draw.rectangle(
                [cx - base_hw, stand_b, cx + base_hw, stand_b + base_h],
                fill=FG_DIM,
            )

    return img


# ---------------------------------------------------------------------------
# ICO writer (multi-size, no extra deps)
# ---------------------------------------------------------------------------

def images_to_ico(images: list[Image.Image]) -> bytes:
    """Pack a list of RGBA images into an ICO binary."""
    entries = []
    data_chunks = []
    offset = 6 + 16 * len(images)  # header + directory

    for img in images:
        png_buf = io.BytesIO()
        img.save(png_buf, format='PNG')
        data = png_buf.getvalue()

        w, h = img.size
        entries.append((w, h, len(data), offset))
        data_chunks.append(data)
        offset += len(data)

    buf = io.BytesIO()
    # ICONDIR header
    buf.write(struct.pack('<HHH', 0, 1, len(images)))
    # ICONDIRENTRY array
    for (w, h, size, off) in entries:
        buf.write(struct.pack('<BBBBHHII',
            w & 0xFF, h & 0xFF,  # 0 means 256
            0, 0,                # color count, reserved
            1, 32,               # planes, bit count
            size, off,
        ))
    for chunk in data_chunks:
        buf.write(chunk)

    return buf.getvalue()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    root = os.path.join(os.path.dirname(__file__), '..')
    out_dir = os.path.join(root, 'electron-app', 'public')
    os.makedirs(out_dir, exist_ok=True)

    sizes = [16, 24, 32, 48, 64, 128, 256]

    # icon.ico — all sizes embedded
    ico_images = [draw_icon(s) for s in sizes]
    ico_bytes  = images_to_ico(ico_images)
    ico_path   = os.path.join(out_dir, 'icon.ico')
    with open(ico_path, 'wb') as f:
        f.write(ico_bytes)
    print(f'Written: {ico_path}')

    # icon.png — 256x256
    png_path = os.path.join(out_dir, 'icon.png')
    draw_icon(256).save(png_path, 'PNG')
    print(f'Written: {png_path}')

    # tray-icon.png — 32x32
    tray_path = os.path.join(out_dir, 'tray-icon.png')
    draw_icon(32).save(tray_path, 'PNG')
    print(f'Written: {tray_path}')


if __name__ == '__main__':
    main()
