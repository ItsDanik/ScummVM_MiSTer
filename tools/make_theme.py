#!/usr/bin/env python3
# Make ScummVM's GUI theme for the MiSTer, "MiSTer Hybrid": the colours and the
# font of the Hybrid Core Framework's purple screen (Danik, 2026-10-25).
#   the palette   the purple screen's (hybrid_host.sv's WALL_BG, WALL_INK, the
#                 message bar) and the MiSTer logo's (rtl/hybrid_wall_pal.hex)
#   the font      Cozette 6x13 (hybrid/assets/cozette.bdf) at every size, for
#                 English; ScummVM's TTFs for its translations
#   the shapes    flat, corners of 1 pixel at 320x200 and 2 at 640x400 /
#                 640x480, shadows and borders of two lines only there (a
#                 detail one line high flickers in 480i)
#   the logo      ScummVM's in the dots' pink and pale lavender, the MiSTer
#                 logo beside it
#   the pointer   white with a dark outline, every pixel drawn, 11x16 at
#                 every resolution (Danik: 22x32 at 640x480 was too big)
#   the layouts   ScummVM's common ones, from the submodule, the in-game menu
#                 with the game behind it in grey (shading 'luminance'), and
#                 the launcher's artwork view at 640x400 / 640x480
#                 (LauncherArt, MISTER_HYBRID in gui/launcher.cpp): the list,
#                 the selected game's artwork (ART_SIZE, tools/make_icons.py
#                 makes the icons for it) and its details
# into build/theme/misterhybrid/ and build/theme/zip/misterhybrid.zip (package.sh
# puts it in data/; tools/theme_preview.sh takes either; the MiSTer
# backend makes it the default, with gui_disable_fixed_font_scaling: ScummVM's
# scaler of bitmap fonts crashes on Cozette, and the GUI is 1x anyway).
#
# usage: tools/make_theme.py
# needs Pillow and rsvg-convert (librsvg), for the logos
import io
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEMES = os.path.join(ROOT, "scummvm/gui/themes")
ASSETS = os.path.join(ROOT, "hybrid/assets")
OUT = os.path.join(ROOT, "build/theme")
ID, NAME = "misterhybrid", "MiSTer Hybrid"
DIR = os.path.join(OUT, ID)

# the colours (the theme's palette names)
PAL = {
    "bg":        "7F30A0",  # WALL_BG: the launcher and the in-game menu
    "panel":     "2B1438",  # the list, dialogs
    "panel2":    "3A1C4A",  # inactive tabs
    "field":     "1E0E28",  # text fields, popups, scrollbars, sliders
    "btn":       "4F1E63",  # the logo's dark purple
    "btn_hover": "B0409A",
    "btn_press": "DF51AF",
    "btn_dis":   "4A3A54",
    "sel":       "DF51AF",  # the message bar: the selected line of the game list
    "sel_off":   "5A3270",  # the selection while the list has no focus
    "ink":       "EFEFEF",  # WALL_INK
    "dim":       "B790C8",  # the logo's lavender: games whose files are missing, labels
    "dis":       "7E6C8A",  # disabled text
    "dark":      "201624",  # the logo's near black
    "line":      "5A3270",  # borders, separators
    "handle":    "6B3A86",  # scrollbar handle
    "slider":    "9B60B4",  # the logo's light purple
    "lit":       "FF5CB4",  # WALL_LIT: settings a game overrides
}

def rgb(name):
    h = PAL.get(name, name)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

# the artwork view's picture, square (make_icons.py makes the icons in this
# size, on the background "bg")
ART_SIZE = 236

# the two sizes of ScummVM's layouts: below 400 lines (320x200) and from 400
# (pop: a popup's arrows, width, height, the lower one's top, the upper
# one's, their distance from the edge; clip: a menu button's arrow part)
LOW = dict(res="y<H", r=1, line=1, shadow=0, tri=5, sfx="_small", pop=(7, 4, 9, 4, 3), clip=7)
HIGH = dict(res="y>=H", r=2, line=2, shadow=2, tri=8, sfx="", pop=(10, 5, 10, 4, 6), clip=13)

# --- the graphics: render_info ---------------------------------------------

def step(func, **a):
    return "\t\t<drawstep func = '%s' %s/>\n" % (func, " ".join("%s = '%s'" % (k, v) for k, v in a.items()))

def text(font, color, v="center", h="center"):
    return ("\t\t<text font = '%s' text_color = '%s' vertical_align = '%s' horizontal_align = '%s'/>\n"
            % (font, color, v, h))

def dd(id, body, res=None):
    r = " resolution = '%s'" % res if res else ""
    return "\t<drawdata id = '%s' cache = 'false'%s>\n%s\t</drawdata>\n" % (id, r, body)

def both(id, make):
    """one drawdata for each size"""
    return dd(id, make(LOW), LOW["res"]) + dd(id, make(HIGH), HIGH["res"])

def drawdata():
    s = []
    s.append(dd("mainmenu_bg", step("fill", fill="background", bg_color="bg")))
    s.append(dd("text_selection", step("square", fill="foreground", fg_color="sel_off")))
    s.append(dd("text_selection_focus", step("square", fill="foreground", fg_color="sel")))
    s.append(dd("caret", step("square", fill="foreground", fg_color="ink")))
    # the in-game menu (special), dialogs, browsers
    s.append(both("special_bg", lambda z: step("roundedsq", radius=z["r"], fill="background", stroke=0, bg_color="bg", shadow=z["shadow"] * 2)))
    s.append(both("default_bg", lambda z: step("roundedsq", radius=z["r"], fill="background", stroke=0, bg_color="panel", shadow=z["shadow"] * 2)))
    s.append(both("plain_bg", lambda z: step("roundedsq", radius=z["r"], fill="background", stroke=0, bg_color="panel", shadow=z["shadow"] * 2)))
    s.append(both("tooltip_bg", lambda z: step("square", fill="background", bg_color="field", fg_color="line", stroke=z["line"], shadow=z["shadow"])))
    s.append(both("separator", lambda z: step("square", fill="foreground", height=z["line"], ypos="center", fg_color="line")))
    # the list and other framed widgets
    s.append(both("widget_default", lambda z: step("roundedsq", radius=z["r"], fill="background", stroke=0, bg_color="panel", shadow=z["shadow"])))
    s.append(both("widget_small", lambda z: step("square", fill="background", stroke=0, bg_color="panel", shadow=z["shadow"])))
    s.append(both("widget_textedit", lambda z: step("roundedsq", radius=z["r"], fill="background", stroke=0, bg_color="field")))
    s.append(both("thumb_bg", lambda z: step("roundedsq", radius=z["r"], fill="background", bg_color="dark")))
    s.append(both("griditem_bg", lambda z: step("roundedsq", radius=z["r"], fill="background", bg_color="panel")))
    s.append(both("griditem_hover_bg", lambda z: step("roundedsq", radius=z["r"], stroke=2, fill="background", fg_color="sel", bg_color="panel")))
    # scrollbars
    s.append(both("scrollbar_base", lambda z: step("roundedsq", radius=z["r"], stroke=0, fill="background", bg_color="field")))
    s.append(both("scrollbar_handle_idle", lambda z: step("roundedsq", radius=z["r"], stroke=0, fill="background", bg_color="handle")))
    s.append(both("scrollbar_handle_hover", lambda z: step("roundedsq", radius=z["r"], stroke=0, fill="background", bg_color="btn_hover")))
    for id, c in (("scrollbar_button_idle", "dim"), ("scrollbar_button_hover", "sel")):
        s.append(both(id, lambda z, c=c: step("triangle", fg_color=c, fill="foreground", width=z["tri"], height=z["tri"],
                                              xpos="center", ypos="center", orientation="top")))
    # tabs
    s.append(both("tab_active", lambda z: text("text_default", "color_normal")
                  + step("tab", radius=z["r"], stroke=0, fill="background", bg_color="panel")))
    s.append(both("tab_inactive", lambda z: text("text_default", "color_alternative")
                  + step("tab", radius=z["r"], stroke=0, fill="background", bg_color="panel2")))
    s.append(both("tab_background", lambda z: step("tab", radius=z["r"], stroke=0, fill="foreground", fg_color="field")))
    # sliders
    s.append(both("widget_slider", lambda z: step("roundedsq", radius=z["r"], stroke=0, fill="background", bg_color="field")))
    for id, c in (("slider_full", "slider"), ("slider_hover", "sel"), ("slider_disabled", "btn_dis")):
        s.append(both(id, lambda z, c=c: step("roundedsq", radius=z["r"], stroke=0, fill="background", bg_color=c)))
    # buttons
    for id, c, t in (("button_idle", "btn", "color_button"), ("button_hover", "btn_hover", "color_button"),
                     ("button_pressed", "btn_press", "color_button"), ("button_disabled", "btn_dis", "color_button_disabled")):
        s.append(both(id, lambda z, c=c, t=t: text("text_button", t)
                      + step("roundedsq", radius=z["r"], stroke=0, fill="background", bg_color=c)))
    # buttons with a menu (Add Game...): the arrow's part on the right
    def dropdown(c, t, clip, rtl):
        def make(z):
            w = z["tri"]
            a = dict(radius=z["r"], stroke=0, fill="background", bg_color=c)
            if clip:
                n = -z["clip"]
                left = clip == "left"
                if rtl:
                    left = not left
                a["clip"] = "0,0,%d,0" % n if left else "%d,0,0,0" % n
            arrow = step("triangle", fg_color="ink" if c != "btn_dis" else "dis", fill="foreground", width=w, height=w * 3 // 4,
                         xpos="left" if rtl else "right", ypos="center",
                         padding=("%d,0,0,0" if rtl else "0,0,%d,0") % (z["line"] + 1), orientation="bottom")
            return text("text_button", t) + step("roundedsq", **a) + arrow
        return make
    for base, c, t, clip in (("dropdown_button_idle", "btn", "color_button", None),
                             ("dropdown_button_disabled", "btn_dis", "color_button_disabled", None),
                             ("dropdown_button_hover_left", "btn_hover", "color_button", "left"),
                             ("dropdown_button_hover_right", "btn_hover", "color_button", "right"),
                             ("dropdown_button_pressed_left", "btn_press", "color_button", "left"),
                             ("dropdown_button_pressed_right", "btn_press", "color_button", "right")):
        for rtl in (False, True):
            if clip:   # the other part of the button stays as when idle
                def make(z, c=c, t=t, clip=clip, rtl=rtl):
                    return (step("roundedsq", radius=z["r"], stroke=0, fill="background", bg_color="btn")
                            + dropdown(c, t, clip, rtl)(z))
            else:
                make = dropdown(c, t, None, rtl)
            s.append(both(base + ("_rtl" if rtl else ""), make))
    # popups (a choice of several: Graphics mode, Group)
    for id, t in (("popup_idle", "color_normal"), ("popup_hover", "color_normal_hover"), ("popup_disabled", "color_normal_disabled")):
        for rtl in (False, True):
            def make(z, t=t, rtl=rtl):
                w, h, down, up, edge = z["pop"]
                side = "left" if rtl else "right"
                pad = ("%d, 0, 0, 0" if rtl else "0, 0, %d, 0") % edge
                return (step("roundedsq", radius=z["r"], stroke=z["line"], fill="background", fg_color="line", bg_color="field")
                        + step("triangle", fg_color="dim", fill="foreground", width=w, height=h, xpos=side,
                               ypos=down, padding=pad, orientation="bottom")
                        + step("triangle", fg_color="dim", fill="foreground", width=w, height=h, xpos=side,
                               ypos=up, padding=pad, orientation="top")
                        + text("text_default", t, h="start"))
            s.append(both(id + ("_rtl" if rtl else ""), make))
    # checkboxes and radio buttons: our bitmaps, a size for each layout
    for id, f, t, v in (("checkbox_default", "checkbox_empty", "color_normal", "top"),
                        ("checkbox_selected", "checkbox", "color_normal", "top"),
                        ("checkbox_disabled", "checkbox_disabled", "color_normal_disabled", "top"),
                        ("checkbox_disabled_selected", "checkbox_disabled_selected", "color_normal_disabled", "top"),
                        ("radiobutton_default", "radiobutton_empty", "color_normal", "center"),
                        ("radiobutton_selected", "radiobutton", "color_normal", "center"),
                        ("radiobutton_disabled", "radiobutton_disabled", "color_normal_disabled", "center")):
        s.append(both(id, lambda z, f=f, t=t, v=v: text("text_default", t, v=v, h="start")
                      + step("bitmap", file=f + z["sfx"] + ".bmp")))
    return "".join(s)

# ScummVM's languages with fonts of their own, as Remastered has them
LANGS = [("ja", "NotoSansJP"), ("ko", "NotoSansKR"), ("zh_Hans", "NotoSansSC"), ("zh_Hant", "NotoSansTC"),
         ("hi", "NotoSans"), ("ar", "NotoNaskhArabic"), ("he", "NotoSansHebrew"), ("ka", "NotoSansGeorgian")]

def font(id, res, bold, size):
    """Cozette for English (ScummVM's own language, the only one it allows a
    bitmap font for), the TTFs of Remastered for the others"""
    w = "Bold" if bold else "Regular"
    r = "resolution = '%s'\n\t\t\t\t" % res if res else ""
    s = "\t\t<font\t%sid = '%s'\n\t\t\t\tfile = 'cozette.bdf'\n\t\t\t\tpoint_size = '13'>\n" % (r, id)
    s += "\t\t\t\t<language id = 'en'/>\n"
    for lang, face in LANGS:
        ext = "otf" if face.endswith(("JP", "KR", "SC", "TC")) else "ttf"
        s += "\t\t\t\t<language id = '%s' scalable_file = '%s-%s.%s' point_size = '%d'/>\n" % (lang, face, w, ext, size)
    s += "\t\t\t\t<language id = '*' scalable_file = 'LiberationSans-%s.ttf' point_size = '%d'/>\n" % (w, size)
    return s + "\t\t</font>\n"

TEXT_COLORS = [
    ("color_normal", "ink"), ("color_normal_inverted", "ink"), ("color_normal_hover", "sel"),
    ("color_normal_disabled", "dis"), ("color_alternative", "dim"), ("color_alternative_inverted", "ink"),
    ("color_alternative_hover", "sel"), ("color_alternative_disabled", "dis"),
    ("color_override", "lit"), ("color_override_inverted", "dark"), ("color_override_hover", "FF8CCB"),
    ("color_override_disabled", "8E5A7A"),
    ("color_button", "ink"), ("color_button_hover", "ink"), ("color_button_disabled", "dis"),
]

# ScummVM's icons (common-svg), as Remastered declares them
ICONS = [("search", 16, 16), ("eraser", 16, 16), ("delbtn", 16, 16), ("list", 16, 16), ("grid", 16, 16),
         ("stopbtn", 32, 32), ("editbtn", 32, 32), ("switchbtn", 32, 32), ("fastreplay", 32, 32),
         ("stopbtn_small", 16, 16), ("editbtn_small", 16, 16), ("switchbtn_small", 16, 16),
         ("fastreplay_small", 16, 16), ("button_play", 15, 15), ("button_load", 15, 15),
         ("button_options", 15, 15), ("groupbtn", 16, 16), ("art", 16, 16)]

# the artwork view's button, beside ScummVM's list and grid: the list's lines
# and a picture
ART_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
           '<path style="fill:#fff" d="M2 6h12v2H2zm0 6h12v2H2zm0 6h12v2H2zm0 6h12v2H2z'
           'M17 5h13v13H17zm0 16h13v2H17zm0 4h9v2h-9z"/></svg>')

def gfx(bitmaps):
    s = "<?xml version = '1.0'?>\n<!-- MiSTer Hybrid: made by tools/make_theme.py of ScummVM_MiSTer, edit that -->\n<render_info>\n\t<palette>\n"
    for k, v in PAL.items():
        s += "\t\t<color name = '%s' rgb = '%d, %d, %d'/>\n" % ((k,) + rgb(k))
    s += "\t</palette>\n\n\t<bitmaps>\n"
    for f in bitmaps:
        s += "\t\t<bitmap filename = '%s'/>\n" % f
    for name, w, h in ICONS:
        svg = name.replace("_small", "")
        s += "\t\t<bitmap filename = '%s.bmp' scalable_file = '%s.svg' width = '%d' height = '%d'/>\n" % (name, svg, w, h)
    s += "\t</bitmaps>\n\n\t<fonts>\n"
    for id, bold in (("text_default", True), ("text_button", True), ("text_normal", False)):
        s += font(id, HIGH["res"], bold, 12) + font(id, None, False, 11)
    s += font("tooltip_normal", None, False, 11)
    for res, pt in (("y>799", 12), ("y>=H", 10), (None, 8)):
        r = "resolution = '%s' " % res if res else ""
        s += ("\t\t<font %sid = 'console' file = 'builtinConsole' point_size = '%d'>\n"
              "\t\t\t\t<language id = '*' scalable_file = 'SourceCodeVariable-Roman.ttf'/>\n\t\t</font>\n" % (r, pt))
    for id, c in TEXT_COLORS:
        c = c if c in PAL else "%d, %d, %d" % rgb(c)
        s += "\t\t<text_color id = '%s' color = '%s'/>\n" % (id, c)
    s += "\t</fonts>\n\n"
    s += ("\t<cursor file = 'cursor.bmp' hotspot = '0, 0'/>\n"
          "\t<cursor file = 'cursor.bmp' hotspot = '0, 0' type = 'index'/>\n\n")
    return s + drawdata() + "</render_info>\n"

# --- bitmaps: ScummVM draws a theme's BMP with magenta as transparency -------

KEY = (255, 0, 255)

def bmp(im, name, bg=None):
    """an RGB(A) picture as a BMP; with bg, its edges mixed with that colour
    and what is left of the colour itself transparent"""
    if bg is not None:
        flat = Image.new("RGBA", im.size, rgb(bg) + (255,))
        flat.alpha_composite(im.convert("RGBA"))
        im = flat.convert("RGB")
        px = im.load()
        for y in range(im.height):
            for x in range(im.width):
                if px[x, y] == rgb(bg):
                    px[x, y] = KEY
    im.convert("RGB").save(os.path.join(DIR, name), "BMP")
    return name

# the pointer: 1 white, 2 its outline
ARROW = ["2", "22", "212", "2112", "21112", "211112", "2111112", "21111112", "211111112", "2111111112",
         "21111122222", "2112112", "212 2112", "22  2112", "2    2112", "     222"]

def pointer():
    im = Image.new("RGB", (11, 16), KEY)
    for y, row in enumerate(ARROW):
        for x, ch in enumerate(row):
            if ch != " ":
                im.putpixel((x, y), rgb("ink") if ch == "1" else rgb("dark"))
    return im

def box(size, line, round_, fill, edge, mark):
    """a checkbox or radio button, every pixel on or off"""
    im = Image.new("RGB", (size, size), KEY)
    d = ImageDraw.Draw(im)
    if round_:
        d.ellipse((0, 0, size - 1, size - 1), fill=rgb(edge))
        d.ellipse((line, line, size - 1 - line, size - 1 - line), fill=rgb(fill))
        if mark:
            m = size // 2 - (2 if size < 13 else 3)
            d.ellipse((m, m, size - 1 - m, size - 1 - m), fill=rgb(mark))
    else:
        d.rectangle((0, 0, size - 1, size - 1), fill=rgb(edge))
        d.rectangle((line, line, size - 1 - line, size - 1 - line), fill=rgb(fill))
        if mark:
            if size < 13:
                d.line([(2, 5), (4, 7), (8, 3)], fill=rgb(mark), width=1)
                d.line([(2, 6), (4, 8), (8, 4)], fill=rgb(mark), width=1)
            else:
                d.line([(3, 7), (6, 10), (11, 4)], fill=rgb(mark), width=2)
                d.line([(3, 8), (6, 11), (11, 5)], fill=rgb(mark), width=2)
    return im

def boxes():
    names = []
    for z, size in ((LOW, 11), (HIGH, 15)):
        l = z["line"]
        for name, rnd, fill, edge, mark in (("checkbox_empty", 0, "field", "slider", None),
                                            ("checkbox", 0, "sel", "sel", "ink"),
                                            ("checkbox_disabled", 0, "panel", "btn_dis", None),
                                            ("checkbox_disabled_selected", 0, "btn_dis", "btn_dis", "dis"),
                                            ("radiobutton_empty", 1, "field", "slider", None),
                                            ("radiobutton", 1, "sel", "sel", "ink"),
                                            ("radiobutton_disabled", 1, "panel", "btn_dis", None)):
            names.append(bmp(box(size, l, rnd, fill, edge, mark), name + z["sfx"] + ".bmp"))
    return names

# ScummVM's logo in the framework's colours: "Scumm" in the dots' pink, the
# stones of "VM" in pale lavender
LOGO = {"#00c832": "#FF5CB4", "#00701c": "#8E2667", "#006e1c": "#8E2667", "#006a1b": "#7A1F5C",
        "#00661a": "#6A1A50", "#b5b5b5": "#D3BFDB", "#333": "#3A2448"}

def logos():
    svg = open(os.path.join(THEMES, "common-svg/logo.svg")).read()
    for a, b in LOGO.items():
        svg = re.sub(re.escape(a) + r"\b", b, svg, flags=re.I)
    png = subprocess.run(["rsvg-convert", "-h", "320"], input=svg.encode(), capture_output=True, check=True).stdout
    scumm = Image.open(io.BytesIO(png)).convert("RGBA")
    mister = Image.open(os.path.join(ASSETS, "MiSTer.png")).convert("RGBA")

    def height(im, h):
        return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)

    def side_by_side(sh, mh, gap, divider, H):
        s, m = height(scumm, sh), height(mister, mh)
        im = Image.new("RGBA", (s.width + 2 * gap + m.width, H), (0, 0, 0, 0))
        im.alpha_composite(s, (0, (H - sh) // 2))
        im.alpha_composite(m, (s.width + 2 * gap, (H - mh) // 2))
        x = s.width + gap - 1
        ImageDraw.Draw(im).rectangle((x, H // 2 - divider, x + 1, H // 2 + divider), fill=rgb("dim") + (255,))
        return im

    # the launcher (640x400, 640x480) on the background, in the list and grid
    # views and, smaller, the artwork view; the in-game menu (640x480 games)
    # on its own, which has the background's colour too, at most the 210
    # pixels of its slot
    return [bmp(side_by_side(70, 54, 14, 24, 80), "logo.bmp", "bg"),
            bmp(side_by_side(56, 43, 11, 19, 64), "logo_art.bmp", "bg"),
            bmp(side_by_side(33, 21, 7, 9, 40), "logo_small.bmp", "bg")]

# ScummVM's icons, their colours turned into the theme's by brightness
def icon_colour(m):
    h = m.group(0)[1:]
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    t = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    dark, light = rgb("dark"), rgb("ink")
    mid = rgb("dim")
    if t < 0.5:
        c = [round(dark[i] + (mid[i] - dark[i]) * t * 2) for i in range(3)]
    else:
        c = [round(mid[i] + (light[i] - mid[i]) * (t - 0.5) * 2) for i in range(3)]
    return "#%02X%02X%02X" % tuple(c)

def icons():
    for name, _, _ in ICONS:
        name = name.replace("_small", "")
        src = ART_SVG if name == "art" else open(os.path.join(THEMES, "common-svg", name + ".svg")).read()
        open(os.path.join(DIR, name + ".svg"), "w").write(re.sub(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", icon_colour, src))

# Cozette for ScummVM's loader: characters 32..255 (it keeps 256), each in its
# 6x13 cell as make_wall.py has it, and a default character that is there.
# With it the cache ScummVM makes of it (BdfFont::cacheFontData(), version 1;
# every glyph in the same box and advance): without one in the theme ScummVM
# reads the BDF at every start and writes the cache into the folder it runs in
def cozette():
    src = open(os.path.join(ASSETS, "cozette.bdf")).read()
    head, rest = src.split("STARTCHAR", 1)
    W, H, DESC = 6, 13, 3
    out, glyphs = [], {}
    for g in re.findall(r"STARTCHAR.*?ENDCHAR\n", "STARTCHAR" + rest, re.S):
        enc = int(re.search(r"ENCODING (-?\d+)", g).group(1))
        if not 32 <= enc <= 255:
            continue
        w, h, xo, yo = map(int, re.search(r"BBX (-?\d+) (-?\d+) (-?\d+) (-?\d+)", g).groups())
        rows = g.split("BITMAP\n")[1].split("ENDCHAR")[0].split()
        cell = [[0] * W for _ in range(H)]
        for r, hx in enumerate(rows):
            bits, nb = int(hx, 16), len(hx) * 4
            cr = (H - DESC - 1) - (yo + h - 1 - r)
            for c in range(w):
                x = xo + c
                if bits >> (nb - 1 - c) & 1 and 0 <= x < W and 0 <= cr < H:
                    cell[cr][x] = 1
        glyphs[enc] = bytes(int("".join(map(str, row)) + "00", 2) for row in cell)
        name = re.search(r"STARTCHAR (.*)", g).group(1)
        bm = "".join("%02X\n" % int("".join(map(str, row)) + "00", 2) for row in cell)
        out.append("STARTCHAR %s\nENCODING %d\nSWIDTH 500 0\nDWIDTH %d 0\nBBX %d %d 0 %d\nBITMAP\n%sENDCHAR\n"
                   % (name, enc, W, W, H, -DESC, bm))
    head = re.sub(r"FONTBOUNDINGBOX .*", "FONTBOUNDINGBOX %d %d 0 %d" % (W, H, -DESC), head)
    head = re.sub(r"CHARS \d+", "CHARS %d" % len(out), head)
    head = re.sub(r"DEFAULT_CHAR \d+", "DEFAULT_CHAR 32", head)
    open(os.path.join(DIR, "cozette.bdf"), "w").write(head + "".join(out) + "ENDFONT\n")
    shutil.copy(os.path.join(ASSETS, "cozette-LICENSE.txt"), DIR)
    first, last = min(glyphs), max(glyphs)
    fcc = struct.pack(">4sIHBBBbbBHhH", b"SVFC", 1, W, H, W, H, 0, -DESC, H - DESC, first, 32, last - first + 1)
    for enc in range(first, last + 1):
        fcc += struct.pack(">I", len(glyphs[enc])) + glyphs[enc] if enc in glyphs else struct.pack(">I", 0)
    # no table of advances, none of boxes
    open(os.path.join(DIR, "cozette.fcc"), "wb").write(fcc + b"\0\0")

# The artwork view (640x400 / 640x480): the logo, 64 lines high (Danik: the
# small one was too small), with the search over the grouping and the help
# beside it; the list, and beside it the artwork with the
# game's details under it; the list view's buttons in two rows, the version
# between the views' buttons and the last ones, which the
# bottom padding makes room for (ScummVM's launcher dialogs do it that way:
# its layout gives the list everything but the padding)
def art_dialog():
    # the width inside the backend's margin for CRTs (10 pixels at 640x480,
    # mister-graphics.cpp) and the dialog's padding; beside the logo the rest
    logo = Image.open(os.path.join(DIR, "logo_art.bmp")).width
    side = 640 - 2 * 10 - 2 * 16 - logo - 10
    line = "\t\t\t\t\t<widget name = '%s' width = '%d' height = '15'/>\n"
    button = "\t\t\t\t<widget name = '%s' height = 'Globals.Button.Height'/>\n"
    switch = "\t\t\t\t<widget name = '%s' height = 'Globals.Button.Height' width = 'Globals.Button.Height'/>\n"
    return ("\t<dialog name = 'LauncherArt' overlays = 'screen'>\n"
            "\t\t<layout type = 'vertical' align = 'center' padding = '16, 16, 8, 60'>\n"
            "\t\t\t<layout type = 'horizontal' spacing = '10' padding = '0, 0, 0, 0' align = 'center'>\n"
            "\t\t\t\t<widget name = 'Logo' width = '%d' height = '64' rtl = 'no'/>\n" % logo
            + "\t\t\t\t<layout type = 'vertical' spacing = '8' padding = '0, 0, 0, 0'>\n"
            "\t\t\t\t\t<layout type = 'horizontal' spacing = '5' padding = '0, 0, 0, 0' align = 'center'>\n"
            "\t\t\t\t\t\t<widget name = 'SearchPic' width = '16' height = '17' rtl = 'no'/>\n"
            "\t\t\t\t\t\t<widget name = 'Search' width = '%d' height = 'Globals.Line.Height'/>\n" % (side - 16 - 16 - 10)
            + "\t\t\t\t\t\t<widget name = 'SearchClearButton' height = 'Globals.Line.Height' width = 'Globals.Line.Height'/>\n"
            "\t\t\t\t\t</layout>\n"
            "\t\t\t\t\t<layout type = 'horizontal' spacing = '5' padding = '0, 0, 0, 0' align = 'center'>\n"
            "\t\t\t\t\t\t<widget name = 'GroupPic' width = '16' height = '17' rtl = 'no'/>\n"
            "\t\t\t\t\t\t<widget name = 'laGroupPopup' width = '%d' type = 'PopUp'/>\n" % (side - 16 - 24 - 10)
            + "\t\t\t\t\t\t<widget name = 'HelpButton' height = 'Globals.Button.Height' width = 'Globals.Launcher.HelpButton.Width'/>\n"
            "\t\t\t\t\t</layout>\n"
            "\t\t\t\t</layout>\n"
            "\t\t\t</layout>\n"
            "\t\t\t<layout type = 'horizontal' spacing = '10' padding = '0, 0, 0, 0'>\n"
            "\t\t\t\t<widget name = 'GameList'/>\n"
            "\t\t\t\t<layout type = 'vertical' spacing = '0' padding = '0, 0, 0, 0'>\n"
            "\t\t\t\t\t<widget name = 'Art' width = '%d' height = '%d'/>\n" % (ART_SIZE, ART_SIZE)
            + "\t\t\t\t\t<space size = '4'/>\n"
            + line % ("ArtTitle", ART_SIZE)
            + "".join(line % ("ArtDetail%d" % i, ART_SIZE) for i in range(1, 5))
            + "\t\t\t\t\t<space/>\n"
            "\t\t\t\t</layout>\n"
            "\t\t\t</layout>\n"
            "\t\t\t<layout type = 'horizontal' spacing = '2' padding = '0, 0, 4, 0'>\n"
            + "".join(button % w for w in ("StartButton", "LoadGameButton", "EditGameButton", "AddGameButton",
                                           "DownloadGamesButton", "RemoveGameButton"))
            + "\t\t\t</layout>\n"
            "\t\t\t<layout type = 'horizontal' spacing = '2' padding = '0, 0, 0, 0'>\n"
            + "".join(switch % w for w in ("ListSwitch", "GridSwitch", "ArtSwitch"))
            + "\t\t\t\t<widget name = 'Version' height = 'Globals.Button.Height' textalign = 'center'/>\n"
            + "".join("\t\t\t\t<widget name = '%s' width = '%d' height = 'Globals.Button.Height'/>\n" % w
                      for w in (("OptionsButton", 108), ("MainHelpButton", 70), ("AboutButton", 70), ("QuitButton", 70)))
            + "\t\t\t</layout>\n"
            "\t\t</layout>\n"
            "\t</dialog>\n\n")

def need(s, old, f, what):
    if s.count(old) != 1:
        sys.exit("%s: %s has changed, see layouts() of %s" % (f, what, __file__))

# ScummVM's layouts, the in-game menu with the game in grey behind it, and at
# 640x400 / 640x480 the artwork view, its button next to the list's and the
# grid's
def layouts():
    for f in ("lowres_layout.stx", "highres_layout.stx"):
        s = open(os.path.join(THEMES, "common", f)).read()
        old = "<dialog name = 'GlobalMenu' overlays = 'screen_center'>"
        need(s, old, f, "the in-game menu's dialog line")
        s = s.replace(old, old[:-1] + " shading = 'luminance'>")
        if f == "highres_layout.stx":
            old = "\t\t<def var = 'GridSupported' value = '1'/>\n"
            need(s, old, f, "the grid's variable")
            s = s.replace(old, old + "\t\t<def var = 'LauncherArtSupported' value = '1'/>\n")
            # the three launcher dialogs (list wide and tall, grid): each has the
            # grid's button once
            parts = re.split(r"(?=\t<dialog name = ')", s)
            n = 0
            for i, d in enumerate(parts):
                if re.match(r"\t<dialog name = '(Launcher|LauncherGrid)' ", d):
                    m = re.search(r"([ \t]*)<widget name = 'GridSwitch'[^>]*/>\n", d)
                    if not m:
                        sys.exit("%s: a launcher dialog without the grid's button, see layouts() of %s" % (f, __file__))
                    art = m.group(0).replace("GridSwitch", "ArtSwitch")
                    parts[i] = d[:m.end()] + art + d[m.end():]
                    n += 1
                elif d.startswith("\t<dialog name = 'EEDialog' "):
                    parts[i] = art_dialog() + d
            if n != 3 or "LauncherArt" not in "".join(parts):
                sys.exit("%s: not the three launcher dialogs, see layouts() of %s" % (f, __file__))
            s = "".join(parts)
        open(os.path.join(DIR, f), "w").write(s)

def main():
    version = re.search(r'SCUMMVM_THEME_VERSION_STR "([^"]+)"',
                        open(os.path.join(ROOT, "scummvm/gui/ThemeEngine.h")).read()).group(1)
    shutil.rmtree(DIR, ignore_errors=True)
    os.makedirs(DIR)
    open(os.path.join(DIR, "THEMERC"), "w").write("[%s:%s:Danik]\n" % (version, NAME))
    bitmaps = [bmp(pointer(), "cursor.bmp")] + boxes() + logos()
    icons()
    cozette()
    layouts()
    open(os.path.join(DIR, "hybrid_gfx.stx"), "w").write(gfx(bitmaps))
    os.makedirs(os.path.join(OUT, "zip"), exist_ok=True)
    z = os.path.join(OUT, "zip", ID + ".zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(os.path.join(DIR, "THEMERC"), "THEMERC")
        for f in sorted(os.listdir(DIR)):
            if f != "THEMERC":
                zf.write(os.path.join(DIR, f), f)
    print(z)

if __name__ == "__main__":
    main()
