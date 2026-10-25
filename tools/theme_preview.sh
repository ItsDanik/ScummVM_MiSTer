#!/bin/sh
# Look at a ScummVM GUI theme on the PC, with the ScummVM installed here
# (flatpak org.scummvm.ScummVM, or a scummvm on the PATH), at the sizes the
# MiSTer shows ScummVM's GUI in: the GUI is drawn at the game's resolution,
# 1x, as the MiSTer backend does (SurfaceSdl, scale 1).
#
# usage: tools/theme_preview.sh <theme folder or .zip> [low|400|480] [--start <id>] [--shot <out.png> [action ...]]
#   low   320x200: the launcher, and the menus of every 320x200 game
#         (ScummVM's lowres layout, below 400 lines)
#   400   640x400: the menus of a 640x400 game
#   480   640x480: the menus of a 640x480 game (the default)
#   --start  start that game of the list (Ctrl+F5 then opens ScummVM's
#           menu over it); a game's files go in build/theme_preview/games/<id>/
#           (free ones: downloads.scummvm.org), the list's others are not there
#   --shot  no window: run it on a hidden X server (Xvfb), do the actions,
#           save the picture and quit. Actions, in window pixels:
#             click:X,Y  right:X,Y  move:X,Y  key:<X keysym>[+<keysym>...]  wait:<seconds>
#           e.g. click:560,302 wait:1 (Global Options... at 480)
#
# The configuration is its own (build/theme_preview/run/), with a few games
# listed that are not there, so the list has something in it; nothing of
# the ScummVM installed here is changed. A folder anywhere under $HOME:
# the flatpak sees no /tmp.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
# a zip in a folder of its own: ScummVM would not know it from a folder of
# the same name next to it
if [ -f "$1" ]; then
    ID=$(basename "$1" .zip)
    THEMEPATH=$ROOT/build/theme_preview/zip
    rm -rf "$THEMEPATH"; mkdir -p "$THEMEPATH"; cp "$1" "$THEMEPATH/"
else
    ID=$(basename "$(cd "$1" && pwd)")
    THEMEPATH=$(dirname "$(cd "$1" && pwd)")
fi
shift
SIZE=480
case "$1" in low|400|480) SIZE=$1; shift ;; esac
START=
if [ "$1" = --start ]; then START=$2; shift 2; fi
SHOT=
if [ "$1" = --shot ]; then SHOT=$(realpath -m "$2"); mkdir -p "$(dirname "$SHOT")"; shift 2; fi

RUN=$ROOT/build/theme_preview/run
GAMES=$ROOT/build/theme_preview/games
mkdir -p "$RUN"
INI=$RUN/$ID-$SIZE.ini
case $SIZE in
    low) GFX="gfx_mode=surfacesdl
scaler=normal
scale_factor=1"; W=320; H=200 ;;
    400) GFX="gfx_mode=surfacesdl
scaler=normal
scale_factor=2"; W=640; H=400 ;;
    480) GFX="gfx_mode=opengl"; W=640; H=480 ;;
esac
cat > "$INI" <<EOF
[scummvm]
$GFX
fullscreen=false
aspect_ratio=false
filtering=false
gui_theme=$ID
themepath=$THEMEPATH
gui_browser_native=false
lastselectedgame=atlantis
confirm_exit=false
# the MiSTer's GUI is 1x: bitmap fonts at their own size (and ScummVM's
# scaler crashes on Cozette)
gui_disable_fixed_font_scaling=true

[monkey]
engineid=scumm
gameid=monkey
description=The Secret of Monkey Island (CD/DOS/English)
path=$GAMES/monkey

[atlantis]
engineid=scumm
gameid=atlantis
description=Indiana Jones and the Fate of Atlantis (CD/DOS/English)
path=$GAMES/atlantis

[tentacle]
engineid=scumm
gameid=tentacle
description=Day of the Tentacle (CD/DOS/English)
path=$GAMES/tentacle

[lure]
engineid=lure
gameid=lure
description=Lure of the Temptress (DOS/English)
path=$GAMES/lure

[sky]
engineid=sky
gameid=sky
description=Beneath a Steel Sky (CD/DOS/English)
path=$GAMES/sky

[queen]
engineid=queen
gameid=queen
description=Flight of the Amazon Queen (Talkie/DOS/English)
path=$GAMES/queen

[grim]
engineid=grim
gameid=grim
description=Grim Fandango (Windows/English)
path=$GAMES/grim

[sq3]
engineid=sci
gameid=sq3
description=Space Quest III: The Pirates of Pestulon (DOS/English)
path=$GAMES/sq3
EOF

if command -v scummvm >/dev/null; then SCUMMVM=scummvm
else SCUMMVM="flatpak run org.scummvm.ScummVM"; fi

if [ -z "$SHOT" ]; then
    exec $SCUMMVM --config="$INI" $START
fi

# a hidden X server, the window in its middle (SDL centres it)
SW=1280; SH=1024; X0=$(( (SW - W) / 2 )); Y0=$(( (SH - H) / 2 ))
DPY=:$(( 90 + $$ % 100 ))
Xvfb $DPY -screen 0 ${SW}x${SH}x24 -nolisten tcp >/dev/null 2>&1 &
XVFB=$!
trap 'kill $XVFB $SVM 2>/dev/null' EXIT
sleep 1
env -u WAYLAND_DISPLAY DISPLAY=$DPY SDL_VIDEODRIVER=x11 $SCUMMVM --config="$INI" $START >"$RUN/last.log" 2>&1 &
SVM=$!
sleep 5
DISPLAY=$DPY X0=$X0 Y0=$Y0 python3 -I - "$@" <<'EOF'
# the actions, through the XTEST extension
import ctypes, os, sys, time
x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
xt = ctypes.cdll.LoadLibrary("libXtst.so.6")
x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XStringToKeysym.restype = ctypes.c_ulong
d = ctypes.c_void_p(x11.XOpenDisplay(None))
x0, y0 = int(os.environ["X0"]), int(os.environ["Y0"])
def flush(): x11.XFlush(d); time.sleep(0.15)
for a in sys.argv[1:]:
    kind, _, arg = a.partition(":")
    if kind in ("click", "right", "move"):
        px, py = (int(n) for n in arg.split(","))
        xt.XTestFakeMotionEvent(d, -1, x0 + px, y0 + py, 0); flush()
        if kind != "move":
            b = 1 if kind == "click" else 3
            xt.XTestFakeButtonEvent(d, b, 1, 0); flush()
            xt.XTestFakeButtonEvent(d, b, 0, 0); flush()
    elif kind == "key":
        kcs = [x11.XKeysymToKeycode(d, x11.XStringToKeysym(k.encode())) for k in arg.split("+")]
        for kc in kcs:
            xt.XTestFakeKeyEvent(d, kc, 1, 0); flush()
        for kc in reversed(kcs):
            xt.XTestFakeKeyEvent(d, kc, 0, 0); flush()
    elif kind == "wait":
        time.sleep(float(arg))
time.sleep(0.8)
EOF
DISPLAY=$DPY import -window root -crop ${W}x${H}+$X0+$Y0 +repage "$SHOT"
echo "$SHOT"
