"""Merge a glow mask PNG into a texture PNG.

Mask pixels, layered exactly over the texture:
    FF0000 (red)   -> texture alpha becomes 253 (weak glow)
    0000FF (blue)  -> texture alpha becomes 252 (full glow)
    000000 (black) -> texture alpha resets to 255 (removes glow mark)
Any other mask color -> that pixel is untouched.

Glow marks only apply to pixels whose texture alpha is 255, so existing
transparency is preserved. Black only resets pixels previously marked
(252/253), never transparent ones. The texture is overwritten in place -
keep a backup of the original.
"""
from pathlib import Path

import ui

try:
    from PIL import Image
except ImportError:
    Image = None

RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
GLOW_ALPHA = {RED: 253, BLUE: 252}  # red = weak glow, blue = full glow
RESET_ALPHA = BLACK  # resets previously marked pixels back to 255
GLOW_MARKS = (252, 253)


def _resolve_path(label):
    raw = ui.prompt(label)
    if not raw:
        ui.error("No path given.")
        return None
    p = Path(raw).expanduser()
    if not p.is_file():
        ui.error(f"File not found: {p}")
        return None
    return p


def _open_png(path):
    try:
        img = Image.open(path)
    except Exception:
        ui.error(f"Not a PNG file: {path.name} (unreadable image)")
        return None
    if img.format != "PNG":
        ui.error(f"Not a PNG file: {path.name} (format: {img.format or 'unknown'})")
        return None
    return img.convert("RGBA")


def run():
    if Image is None:
        ui.error("Pillow not found! (pip install -r requirements.txt)")
        return
    ui.header("Glow Merge")
    tex_path = _resolve_path("Path to the PNG that should glow")
    if tex_path is None:
        return
    mask_path = _resolve_path("Path to the glow mask (FF0000=253, 0000FF=252, 000000=reset)")
    if mask_path is None:
        return

    tex = _open_png(tex_path)
    if tex is None:
        return
    mask = _open_png(mask_path)
    if mask is None:
        return
    if tex.size != mask.size:
        ui.error(f"Size mismatch: texture {tex.size} vs mask {mask.size}")
        return

    t = tex.load()
    m = mask.load()
    n = reset = skipped = 0
    for y in range(tex.height):
        for x in range(tex.width):
            c = m[x, y][:3]
            ta = t[x, y][3]
            if c == RESET_ALPHA:
                if ta in GLOW_MARKS:
                    t[x, y] = t[x, y][:3] + (255,)
                    reset += 1
            else:
                a = GLOW_ALPHA.get(c)
                if a is None or ta != 255:
                    if a is not None and ta != 255:
                        skipped += 1
                    continue
                t[x, y] = t[x, y][:3] + (a,)
                n += 1

    tex.save(tex_path)
    ui.success(f"{n} pixels marked, {reset} reset, "
               f"{skipped} skipped (non-opaque) -> {tex_path}")
    ui.warn("Texture overwritten in place - keep a backup of the original.")
    print()
