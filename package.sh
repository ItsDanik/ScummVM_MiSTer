#!/bin/sh
# Assemble the MiSTer release in dist/ScummVM_<date>/ from the build outputs,
# in the layout of the hybrid ports (hybrid/README.md, "Naming and layout"):
#   _Other/dnk-<title>.mgl             a menu entry for each game (package/games.txt)
#   _Other/dnk/dnk-ScummVM_<date>.rbf    the core, not in the menu itself
#   games/dnk/ScummVM/                   the game, its logos in logos/
#   games/dnk/SoundFonts/               GeneralUser GS and its licence, if the
#                                       games play MIDI (MIDI_SYNTH 1)
#   Scripts/danik_hybrid_ports.sh       the launcher, and its screen in
#   Scripts/.danik_hybrid_ports/        (copies of both with the game: the
#                                       newest one installed is the one used)
#   games/dnk/danik_hybrid_cores.sh     the last version of the launcher before,
#                                       which hands a running one over to it
#   downloader_danik_hybrid_ports.ini   the database for update_all, which
#                                       keeps the ports up to date from then on
set -e
cd "$(dirname "$0")"
DATE=$(date +%Y%m%d)
OUT=dist/ScummVM_$DATE
G=$OUT/games/dnk/ScummVM
rm -rf "$OUT"
mkdir -p "$OUT/_Other/dnk" "$G" "$OUT/Scripts/.danik_hybrid_ports"

# the launcher and its screen
sh hybrid/launcher/ui/build.sh > /dev/null
cp hybrid/launcher/danik_hybrid_ports.sh "$OUT/Scripts/danik_hybrid_ports.sh"
cp hybrid/launcher/ui/danik_hybrid_ports_ui "$OUT/Scripts/.danik_hybrid_ports/danik_hybrid_ports_ui"
cp hybrid/launcher/danik_hybrid_ports.sh hybrid/launcher/ui/danik_hybrid_ports_ui "$G/"
cp hybrid/launcher/danik_hybrid_cores.sh "$OUT/games/dnk/danik_hybrid_cores.sh"
cp hybrid/launcher/downloader_danik_hybrid_ports.ini "$OUT/"

# the core, and a menu entry for each game: package/games.txt, a line each,
# <id>|<title>. With several games each entry loads the core with the set
# name ScummVM_<id> (the game's settings and button mappings are its own);
# one game has no set name. The title is the entry's name in the menu,
# without what a file name cannot have.
cp core/output_files/ScummVM.rbf "$OUT/_Other/dnk/dnk-ScummVM_$DATE.rbf"
GAMES=$(grep -v '^#' package/games.txt | grep -c '|')
grep -v '^#' package/games.txt | grep '|' | while IFS='|' read -r id title; do
    set_name=ScummVM_$id
    [ ${#set_name} -lt 32 ] || { echo "the set name $set_name is too long (31 at most)" >&2; exit 1; }
    file=$(printf %s "$title" | tr -d ':*?"<>|/\\' | tr -s ' ')
    if [ "$GAMES" -gt 1 ]; then
        set_line="<setname same_dir=\"1\">$set_name</setname>"
    else
        set_line=
    fi
    printf '<mistergamedescription><rbf>_Other/dnk/dnk-ScummVM</rbf>%s</mistergamedescription>\n' "$set_line" \
        > "$OUT/_Other/dnk-$file.mgl"
done

# the game, and its games for the database's catalogue (the launcher's
# screen offers what that has) and for the launcher without one
cp -r package/games/ScummVM/. "$G/"
grep -v '^#' package/games.txt | grep '|' > "$G/games.txt"
# each game's logo, shown at its start (host version 17, hybrid/docs/game_logo.md):
# package/logos/<id>.png, 440x200, as logos/<id>.mhl next to the program
mkdir "$G/logos"
grep -v '^#' package/games.txt | grep '|' | while IFS='|' read -r id title; do
    [ -f "package/logos/$id.png" ] || { echo "package/logos/$id.png is missing: every game of package/games.txt has its logo, 440x200 (hybrid/docs/game_logo.md)" >&2; exit 1; }
    python3 hybrid/tools/make_logo.py "package/logos/$id.png" "$G/logos/$id.mhl" > /dev/null
done
# the SoundFont of the core's MIDI synthesizer, for a core that has it
# (MIDI_SYNTH 1): fetched at its pinned version, never committed
if grep -q '^localparam MIDI_SYNTH = 1;' core/ScummVM.sv; then
    sh hybrid/tools/soundfont.sh "$OUT/games/dnk/SoundFonts"
fi
cp build/mister/scummvm "$G/ScummVM"
cp build/mister/mh_message "$G/mh_message"
# GAME: files the binary needs next to it (never game data): ScummVM's
# themes, the engines' data files and the virtual keyboard, in data/
# (the lists of ScummVM's make, for the engines built in)
mkdir "$G/data"
hybrid/docker.sh make -s -C build/mister --eval 'print-dist-files: ; @echo $(DIST_FILES_THEMES) $(DIST_FILES_VKEYBD) $(DIST_FILES_ENGINEDATA) $(DIST_FILES_ENGINEDATA_BIG)' print-dist-files \
    | tr ' ' '\n' | grep . | while read -r f; do cp "$f" "$G/data/"; done
# the port's theme, the default (tools/make_theme.py)
python3 tools/make_theme.py > /dev/null
cp build/theme/zip/misterhybrid.zip "$G/data/"
hybrid/docker.sh arm-linux-gnueabihf-strip "$G/ScummVM" "$G/mh_message"
chmod +x "$G/ScummVM" "$G/mh_message" "$G"/*.sh "$G/danik_hybrid_ports_ui" \
    "$OUT/Scripts/danik_hybrid_ports.sh" "$OUT/Scripts/.danik_hybrid_ports/danik_hybrid_ports_ui" \
    "$OUT/games/dnk/danik_hybrid_cores.sh"
# GAME: the game's license as LICENSE-scummvm.txt
cp scummvm/COPYING "$G/LICENSE-scummvm.txt"
cp scummvm/COPYRIGHT "$G/COPYRIGHT-scummvm.txt"
mkdir "$G/LICENSES-scummvm"
cp scummvm/LICENSES/* "$G/LICENSES-scummvm/"
cp build/sdl/src/SDL2-*/LICENSE.txt "$G/LICENSE-sdl.txt"
cp LICENSE "$G/LICENSE-gpl3.txt"
rm -f "dist/ScummVM_$DATE.zip"
(cd "$OUT" && python3 -m zipfile -c "../ScummVM_$DATE.zip" _Other games Scripts downloader_danik_hybrid_ports.ini)
find "$OUT" -type f | sort
ls -la "dist/ScummVM_$DATE.zip"
