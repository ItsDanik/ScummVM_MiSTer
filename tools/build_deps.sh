#!/bin/sh
# Build the libraries ScummVM needs besides SDL2, as static libraries.
# Runs inside the toolchain container (see hybrid/docker.sh), after
# hybrid/sdl2/build.sh.
# usage: build_deps.sh <mister|host> <work directory>
#   libraries and headers end up in <work directory>/<target>/prefix
#
# zlib (compressed saves and data), libpng and libjpeg (images of several
# engines, screenshots), FreeType (TrueType fonts of some engines and of the
# GUI), Ogg Vorbis, FLAC and libmad (compressed speech and CD audio tracks).
# Not built, as only engines this port leaves out need them: Theora, libmpeg2,
# giflib, FluidSynth (the music goes to the core's synthesizer), libcurl.
set -e
TARGET=$1
WORK=$(mkdir -p "$2" && cd "$2" && pwd)
HYBRID=$(cd "$(dirname "$0")/../hybrid" && pwd)

ZLIB=zlib-1.3.1
PNG=libpng-1.6.47
JPEG=libjpeg-turbo-3.0.4
FREETYPE=freetype-2.13.3
OGG=libogg-1.3.5
VORBIS=libvorbis-1.3.7
FLAC=flac-1.4.3
MAD=libmad-0.16.4

fetch() { # <file> <url> <sha256>
    [ -f "$WORK/dl/$1" ] || curl -fsSL -o "$WORK/dl/$1" "$2"
    echo "$3  $WORK/dl/$1" | sha256sum -c - > /dev/null
}
mkdir -p "$WORK/dl" "$WORK/src"
fetch $ZLIB.tar.gz https://github.com/madler/zlib/releases/download/v1.3.1/$ZLIB.tar.gz \
    9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23
fetch $PNG.tar.gz https://github.com/pnggroup/libpng/archive/refs/tags/v1.6.47.tar.gz \
    631a4c58ea6c10c81f160c4b21fa8495b715d251698ebc2552077e8450f30454
fetch $JPEG.tar.gz https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/3.0.4/$JPEG.tar.gz \
    99130559e7d62e8d695f2c0eaeef912c5828d5b84a0537dcb24c9678c9d5b76b
fetch $FREETYPE.tar.xz https://download.savannah.gnu.org/releases/freetype/$FREETYPE.tar.xz \
    0550350666d427c74daeb85d5ac7bb353acba5f76956395995311a9c6f063289
fetch $OGG.tar.gz https://downloads.xiph.org/releases/ogg/$OGG.tar.gz \
    0eb4b4b9420a0f51db142ba3f9c64b333f826532dc0f48c6410ae51f4799b664
fetch $VORBIS.tar.gz https://downloads.xiph.org/releases/vorbis/$VORBIS.tar.gz \
    0e982409a9c3fc82ee06e08205b1355e5c6aa4c36bca58146ef399621b0ce5ab
fetch $FLAC.tar.xz https://downloads.xiph.org/releases/flac/$FLAC.tar.xz \
    6c58e69cd22348f441b861092b825e591d0b822e106de6eb0ee4d05d27205b70
fetch $MAD.tar.gz https://codeberg.org/tenacityteam/libmad/archive/0.16.4.tar.gz \
    f4eb229452252600ce48f3c2704c9e6d97b789f81e31c37b0c67dd66f445ea35
for p in $ZLIB $PNG $JPEG $OGG $VORBIS; do
    [ -d "$WORK/src/$p" ] || tar -xzf "$WORK/dl/$p.tar.gz" -C "$WORK/src"
done
# the toolchain has no xz: Python unpacks these
for p in $FREETYPE $FLAC; do
    [ -d "$WORK/src/$p" ] || python3 -c 'import sys, tarfile; tarfile.open(sys.argv[1]).extractall(sys.argv[2])' \
        "$WORK/dl/$p.tar.xz" "$WORK/src"
done
# the archive's folder is "libmad"
[ -d "$WORK/src/$MAD" ] || { tar -xzf "$WORK/dl/$MAD.tar.gz" -C "$WORK/src" && mv "$WORK/src/libmad" "$WORK/src/$MAD"; }

PREFIX=$WORK/$TARGET/prefix
BUILD=$WORK/$TARGET
mkdir -p "$PREFIX/lib" "$PREFIX/include" "$BUILD"
JOBS=$(nproc)
COMMON="-DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$PREFIX -DCMAKE_PREFIX_PATH=$PREFIX -DCMAKE_INSTALL_LIBDIR=lib -DBUILD_SHARED_LIBS=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5"
if [ "$TARGET" = mister ]; then
    COMMON="$COMMON -DCMAKE_TOOLCHAIN_FILE=$HYBRID/toolchain/mister.cmake -DCMAKE_FIND_ROOT_PATH=$PREFIX"
fi

cmake_lib() { # <library file> <source> <cmake options>
    [ -f "$PREFIX/lib/$1" ] && return
    name=$(basename "$2")
    src=$2; shift 2
    cmake -S "$src" -B "$BUILD/$name" $COMMON "$@" > "$BUILD/$name.log"
    cmake --build "$BUILD/$name" -j"$JOBS" >> "$BUILD/$name.log"
    cmake --install "$BUILD/$name" >> "$BUILD/$name.log"
}

cmake_lib libz.a "$WORK/src/$ZLIB" -DZLIB_BUILD_EXAMPLES=OFF
# zlib installs its shared library as well: the static one alone is linked
rm -f "$PREFIX"/lib/libz.so*
cmake_lib libpng16.a "$WORK/src/$PNG" -DPNG_SHARED=OFF -DPNG_STATIC=ON -DPNG_TESTS=OFF -DPNG_TOOLS=OFF \
    -DPNG_ARM_NEON=on -DZLIB_ROOT="$PREFIX"
cmake_lib libjpeg.a "$WORK/src/$JPEG" -DENABLE_SHARED=OFF -DENABLE_STATIC=ON -DWITH_TURBOJPEG=OFF \
    -DWITH_JAVA=OFF -DWITH_TOOLS=OFF -DWITH_TESTS=OFF
cmake_lib libfreetype.a "$WORK/src/$FREETYPE" -DFT_DISABLE_BZIP2=ON -DFT_DISABLE_HARFBUZZ=ON \
    -DFT_DISABLE_BROTLI=ON -DFT_DISABLE_PNG=ON -DFT_REQUIRE_ZLIB=ON -DZLIB_ROOT="$PREFIX"
cmake_lib libogg.a "$WORK/src/$OGG" -DINSTALL_DOCS=OFF -DBUILD_TESTING=OFF
cmake_lib libvorbis.a "$WORK/src/$VORBIS" -DOGG_ROOT="$PREFIX"
# -O2: GCC 10 for ARM fails on libFLAC's window.c at -O3 (internal compiler error)
cmake_lib libFLAC.a "$WORK/src/$FLAC" -DBUILD_CXXLIBS=OFF -DBUILD_PROGRAMS=OFF -DBUILD_EXAMPLES=OFF \
    -DBUILD_TESTING=OFF -DBUILD_DOCS=OFF -DINSTALL_MANPAGES=OFF -DWITH_OGG=OFF -DWITH_STACK_PROTECTOR=OFF \
    -DCMAKE_C_FLAGS_RELEASE="-O2 -DNDEBUG"
if [ "$TARGET" = mister ]; then
    MADFPM="-DFPM_ARM=ON"
else
    MADFPM="-DFPM_64BIT=ON"
fi
cmake_lib libmad.a "$WORK/src/$MAD" -DEXAMPLE=OFF $MADFPM

echo "ScummVM libraries for $TARGET installed in $PREFIX"
