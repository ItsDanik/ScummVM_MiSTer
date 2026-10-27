#!/bin/sh
# Build ScummVM for the MiSTer in the toolchain container: static SDL2 with the
# hybrid core drivers and the libraries ScummVM uses first (once), then the game.
# usage: ./build.sh [mister|host] [Release|Debug]
#   mister  ARM binary for the MiSTer     -> build/mister/scummvm
#   host    same code for this PC, to run against hybrid/tools/fakecore
set -e
cd "$(dirname "$0")"
TARGET=${1:-mister}
TYPE=${2:-Release}
ROOT=$PWD
PREFIX=$ROOT/build/sdl/$TARGET/prefix
DEPS=$ROOT/build/deps/$TARGET/prefix

hybrid/docker.sh hybrid/sdl2/build.sh "$TARGET" build/sdl
hybrid/docker.sh tools/build_deps.sh "$TARGET" build/deps

# GAME: ScummVM's configure. The "mister" host is the ARM build, the "mister"
# backend the same code on the PC (configure, "mister)").
if [ "$TARGET" = mister ]; then
    HOST="--host=mister"
else
    HOST="--backend=mister"
fi
if [ "$TYPE" = Release ]; then
    OPT="--enable-release --disable-debug"
else
    OPT="--enable-debug --disable-optimizations"
fi

# Engines (CLAUDE.md, "Decisions"): every 2D engine that is on by default,
# and Grim Fandango and Escape from Monkey Island with their software renderer
# (TinyGL); no OpenGL, so not the 3D ones, nor those with too much full-motion
# video or screens bigger than 640x480 for the ARM
ENGINES_OFF=alcachofa,colony,freescape,hpl1,myst3,playground3d,stark,tetraedge
ENGINES_OFF=$ENGINES_OFF,twp,watchmaker,wintermute,riven
ENGINES_OFF=$ENGINES_OFF,agds,bladerunner,buried,crab,cryomni3d,icb,mtropolis
ENGINES_OFF=$ENGINES_OFF,nancy,pegasus,phoenixvr,qdengine,sword25,titanic,vcruise
ENGINES_OFF=$ENGINES_OFF,zvision,testbed

mkdir -p "build/$TARGET"
hybrid/docker.sh sh -c "
  cd build/$TARGET &&
  if [ ! -f config.mk ] || [ $ROOT/build.sh -nt config.mk ] || [ $ROOT/scummvm/configure -nt config.mk ]; then
    PKG_CONFIG_LIBDIR=$DEPS/lib/pkgconfig:$DEPS/share/pkgconfig:$PREFIX/lib/pkgconfig \
    SDL_CONFIG=sdl2-config \
    $ROOT/scummvm/configure $HOST $OPT \
      --disable-scalers --disable-hq-scalers --opengl-mode=none \
      --enable-vkeybd \
      --disable-alsa --disable-seq-midi --disable-sndio --disable-timidity \
      --disable-fluidsynth --disable-fluidlite --disable-mt32emu \
      --disable-libcurl --disable-sdlnet --disable-cloud --disable-enet \
      --disable-imgui --disable-tts --disable-discord --disable-gtk \
      --disable-libunity --disable-readline --disable-eventrecorder \
      --disable-taskbar --disable-updates --disable-system-dialogs \
      --with-zlib-prefix=$DEPS --with-png-prefix=$DEPS --with-jpeg-prefix=$DEPS \
      --with-ogg-prefix=$DEPS --with-vorbis-prefix=$DEPS --with-flac-prefix=$DEPS \
      --with-mad-prefix=$DEPS --with-sdl-prefix=$PREFIX \
      --enable-engine=grim,monkey4 --disable-engine=$ENGINES_OFF
  fi &&
  make -j\$(nproc)"
ls -la "build/$TARGET/scummvm"

# The launch script's messages on the core's picture (hybrid/tools/mh_message.c)
if [ "$TARGET" = mister ]; then
    hybrid/docker.sh arm-linux-gnueabihf-gcc -O2 -static -Ihybrid/hps -o build/mister/mh_message \
        hybrid/tools/mh_message.c hybrid/hps/*.c -lpthread -lm
fi
