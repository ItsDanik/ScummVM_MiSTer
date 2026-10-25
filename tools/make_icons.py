#!/usr/bin/env python3
# The one icon pack the port ships (tools/icons.sh): ScummVM's packs merged,
# the newest pack's icon of a game winning as in ScummVM (gui/gui-manager.cpp
# searches them newest first), each icon scaled to the size the launcher's
# grid draws it at 4 a row in 640x480 (gui/widgets/grid.cpp), so that
# ScummVM only decodes it: 512x512 icons took the MiSTer's ARM seconds to
# start the launcher and stopped the grid's scrolling at every new row.
# The launcher allows no fewer than 4 a row (gui/launcher.cpp, MISTER_HYBRID);
# smaller ones (more a row) ScummVM scales down from these.
#
# Opaque icons become RGB, the others RGBA: palette and grey ones, which the
# grid skips (it draws no 8-bit surface), are converted too. Stored, not
# compressed again: a PNG is compressed already. The packs' XML files are
# left out: ScummVM reads none of them.
#
# usage: tools/make_icons.py <out.dat> <pack.dat> ...   (oldest pack first)
import io
import os
import sys
import zipfile

from PIL import Image

# the grid's thumbnail at 4 a row, 640x480, ScummVM's layouts (measured in
# GridWidget::reloadThumbnails(): 104x104)
SIZE = 104


def scaled(data):
    im = Image.open(io.BytesIO(data))
    im.load()
    im = im.convert("RGBA")
    w, h = im.size
    # the largest size that fits SIZE x SIZE, rounded as scaleGfx() does
    r = min(SIZE / w, SIZE / h)
    nw, nh = (SIZE, int(h * r)) if SIZE / w < SIZE / h else (int(w * r), SIZE)
    # resampled with premultiplied alpha, so transparent pixels bleed no colour
    im = im.convert("RGBa").resize((nw, nh), Image.LANCZOS).convert("RGBA")
    if im.getchannel("A").getextrema() == (255, 255):
        im = im.convert("RGB")
    out = io.BytesIO()
    im.save(out, "PNG", compress_level=9)
    return out.getvalue()


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: tools/make_icons.py <out.dat> <pack.dat> ...")
    out, packs = sys.argv[1], sys.argv[2:]
    icons = {}
    for pack in packs:
        with zipfile.ZipFile(pack) as z:
            for name in z.namelist():
                if name.startswith("icons/") and name.endswith(".png"):
                    icons[name] = z.read(name)
    with zipfile.ZipFile(out + ".part", "w", zipfile.ZIP_STORED) as z:
        for name in sorted(icons):
            z.writestr(zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)), scaled(icons[name]))
    os.replace(out + ".part", out)
    print("%s: %d icons, %d bytes" % (out, len(icons), os.path.getsize(out)))


main()
