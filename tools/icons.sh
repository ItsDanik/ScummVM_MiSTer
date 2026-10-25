#!/bin/sh
# ScummVM's game icons, which its launcher shows in the grid and artwork
# views (the *Launcher* option at 640x480: ScummVM's 320x200 layout has
# neither): every pack of downloads.scummvm.org/frs/icons/ as of the date
# below, merged into one and scaled to the views' sizes by
# tools/make_icons.py (gui-icons-mister.dat), with the licence (GPL-2.0) and
# authors of github.com/scummvm/scummvm-icons, into <folder> (the zip's
# games/dnk/ScummVM/icons/, the backend's iconspath).
#
# Never committed: package.sh fetches the packs, checks them against the
# SHA-256 sums below and keeps them in build/icons/, with the merged pack
# (made again when this script, make_icons.py or make_theme.py, which has the
# artwork's size and background, changes). A new pack on the server (its
# LIST): its line below, and the commit for the licence.
#
# usage: tools/icons.sh <folder>
set -e
cd "$(dirname "$0")/.."
OUT=$1
[ -n "$OUT" ] || { echo "usage: tools/icons.sh <folder>" >&2; exit 1; }
PACKS=https://downloads.scummvm.org/frs/icons
# scummvm-icons as of 2026-10-10
REPO=https://raw.githubusercontent.com/scummvm/scummvm-icons/1ef876f6ea88a20bccc70be6d12ae0ee0d8594e7
CACHE=build/icons
MERGED=$CACHE/merged/gui-icons-mister.dat
PACKLIST=
mkdir -p "$CACHE" "$OUT"

# <URL> <file in the cache> <sum>
fetch() {
    if ! echo "$3  $CACHE/$2" | sha256sum -c --status 2> /dev/null; then
        rm -f "$CACHE/$2.part"
        curl -fsSL --retry 3 -o "$CACHE/$2.part" "$1"
        echo "$3  $CACHE/$2.part" | sha256sum -c --status ||
            { echo "$1: not the file pinned in $0 (its SHA-256 differs)" >&2; rm -f "$CACHE/$2.part"; exit 1; }
        mv "$CACHE/$2.part" "$CACHE/$2"
    fi
}
while read -r name sum; do
    fetch "$PACKS/$name" "$name" "$sum"
    PACKLIST="$PACKLIST $CACHE/$name"
done <<EOF
gui-icons-20211112.dat 1152a200382cbf40e41c29ffac678fa5aa6b050f4b0b6d1bbc36d0ae75d98cdb
gui-icons-20220602.dat 5d7f32bebe35e9016d6611bb4ccc61a9914200fee74e1e4a45c8229d954ada47
gui-icons-20220802.dat 945636964e587712fcd0a19ffde6032964080b225e7f4578bf5fe33cb6eb01ad
gui-icons-20221010.dat 502b814ca2c26c07d3b0cab29024dedbb93536cd150c62d87eb36ea71c175cd4
gui-icons-20230317.dat a2cc156df0ffc4e9c7ce7d47c4395e911a1b249802376cded021b589d922c93f
gui-icons-20230807.dat 2758428b92f4fedcceb8c46fa4461b89a818fa85e0b63c01fd37224369867461
gui-icons-20231110.dat 5f8fe2acdb74b270b34a9a5d4e25d4ca6639c7fb6e9af9ddce36deebf3eed000
gui-icons-20231231.dat db684f46e6ac07f1ffbd74195c1b313b593237eb8ef16da6f8e4a8031c3d2831
gui-icons-20241222.dat 0b3b7fdc3891e400557a5c1b642257f4d66938a0bb9037f7eb233e0abe10c161
gui-icons-20260117.dat fa5b403c22bd1381c2c4f2c9dd702b9f5bca706a9646a05f8fdcd5789cfd4e2b
gui-icons-20260328.dat 806ddc94b8a4cb2e0b1700b64b2a2f3dc71c83333845ccc4c91775a7192919bf
gui-icons-20261010.dat e5c0c7085fe66d3e2fc8486efe020c5e26a9b457ababbf5fad12cef30642905d
EOF
fetch "$REPO/LICENSE" LICENSE 8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643
fetch "$REPO/AUTHORS" AUTHORS 502b2f8b0de5bfbac22ba2f365501c1ca4e28e50b7af1c659745ecddd690e838
# the packs oldest first, as the list above has them
if [ ! "$MERGED" -nt tools/make_icons.py ] || [ ! "$MERGED" -nt tools/icons.sh ] ||
   [ ! "$MERGED" -nt tools/make_theme.py ]; then
    mkdir -p "$(dirname "$MERGED")"
    python3 tools/make_icons.py "$MERGED" $PACKLIST > /dev/null
fi
cp "$MERGED" "$OUT/"
cp "$CACHE/LICENSE" "$OUT/LICENSE-icons.txt"
cp "$CACHE/AUTHORS" "$OUT/AUTHORS-icons.txt"
