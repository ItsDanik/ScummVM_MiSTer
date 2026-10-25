#!/usr/bin/env python3
# The one icon pack the port ships (tools/icons.sh): ScummVM's packs merged,
# the newest pack's icon of a game winning as in ScummVM (gui/gui-manager.cpp
# searches them newest first), each icon scaled to the sizes the launcher
# draws it at, so that ScummVM only decodes it: 512x512 icons took the
# MiSTer's ARM seconds to start the launcher and stopped the grid's scrolling
# at every new row.
#   icons/      the grid at 4 a row in 640x480 (gui/widgets/grid.cpp), and
#               what ScummVM scales for 5 and more a row
#   icons143/   the grid at 3 a row; the launcher allows no fewer
#               (gui/launcher.cpp, MISTER_HYBRID)
#   icons236/   the artwork view (LauncherArt), JPEG on the theme's
#               background (the view and its size are the port's theme's,
#               tools/make_theme.py): a third of PNG's size
# The grid takes icons<size>/ where it has its size, else icons/.
#
# Opaque icons become RGB, the others RGBA: palette and grey ones, which the
# grid skips (it draws no 8-bit surface), are converted too. Stored, not
# compressed again: a PNG is compressed already. The packs' XML files (the
# games' names, publishers, years and series, which the launcher groups by:
# gui/launcher.cpp) are the newest pack's, as they are: each pack has them all.
#
# usage: tools/make_icons.py <out.dat> <pack.dat> ...   (oldest pack first)
import io
import os
import sys
import zipfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True  # no tools/__pycache__/
from make_theme import ART_SIZE, rgb  # noqa: E402

# the grid's thumbnails in 640x480, ScummVM's layouts inside the backend's
# margin for CRTs (mister-graphics.cpp; measured in
# GridWidget::reloadThumbnails()): 99x99 at 4 a row, 143x143 at 3
GRID = {"icons": 99, "icons143": 143}


def scaled(im, size):
    w, h = im.size
    # the largest size that fits size x size, rounded as scaleGfx() does
    r = min(size / w, size / h)
    nw, nh = (size, int(h * r)) if size / w < size / h else (int(w * r), size)
    # resampled with premultiplied alpha, so transparent pixels bleed no colour
    return im.convert("RGBa").resize((nw, nh), Image.LANCZOS).convert("RGBA")


def png(im, size):
    im = scaled(im, size)
    if im.getchannel("A").getextrema() == (255, 255):
        im = im.convert("RGB")
    out = io.BytesIO()
    im.save(out, "PNG", compress_level=9)
    return out.getvalue()


def jpeg(im, size):
    im = scaled(im, size)
    bg = Image.new("RGBA", (size, size), rgb("bg") + (255,))
    bg.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    out = io.BytesIO()
    # no chroma subsampling: the purple's edges stay sharp
    bg.convert("RGB").save(out, "JPEG", quality=90, subsampling=0, optimize=True)
    return out.getvalue()


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: tools/make_icons.py <out.dat> <pack.dat> ...")
    out, packs = sys.argv[1], sys.argv[2:]
    icons = {}
    xml = {}
    for pack in packs:
        with zipfile.ZipFile(pack) as z:
            for name in z.namelist():
                if name.startswith("icons/") and name.endswith(".png"):
                    icons[name] = z.read(name)
                elif "/" not in name and name.endswith(".xml"):
                    xml[name] = z.read(name)
    def add(z, name, data):
        z.writestr(zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)), data)

    with zipfile.ZipFile(out + ".part", "w", zipfile.ZIP_STORED) as z:
        for name in sorted(xml):
            add(z, name, xml[name])
        for name in sorted(icons):
            im = Image.open(io.BytesIO(icons[name]))
            im.load()
            im = im.convert("RGBA")
            base = name[len("icons/"):]
            for folder, size in GRID.items():
                add(z, "%s/%s" % (folder, base), png(im, size))
            add(z, "icons%d/%s.jpg" % (ART_SIZE, base[:-4]), jpeg(im, ART_SIZE))
    os.replace(out + ".part", out)
    print("%s: %d icons, %s, %d bytes" % (out, len(icons), " ".join(sorted(xml)), os.path.getsize(out)))


main()
