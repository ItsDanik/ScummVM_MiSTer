# ScummVM for MiSTer: notes

How the port works and how it is built. For playing it, see the [README](README.md).

## How the port works

The game is ScummVM (`scummvm/`, [ItsDanik/scummvm](https://github.com/ItsDanik/scummvm) branch `mister`, from v2026.4.0) with a backend of its own, `backends/platform/sdl/mister/` (`--host=mister` for the ARM, `--backend=mister` for the same code on the PC; `MISTER_HYBRID`), on top of ScummVM's SDL/POSIX backend and the static SDL2 of `hybrid/sdl2`. Changes elsewhere in ScummVM are behind `#ifdef MISTER_HYBRID`. `package/games.txt` has one entry, ScummVM itself: the player's games are in ScummVM's launcher, added with *Add Game...* / *Mass Add...*, so there is no data to check at the start; ScummVM's settings and saved games are in the folder it runs in (`DATADIR`), what comes with the port in `data/` and `icons/` next to the program.

### Engines

Every 2D engine that is on by default and needs no OpenGL, built into the one binary (about 70 MB unstripped; Linux maps its pages as they are used), without the 3D ones and those with heavy full-motion video or pictures bigger than 640x480 (`ENGINES_OFF` in `build.sh`). Plus `grim` (Grim Fandango) with TinyGL, the software renderer, experimental and slow; its sub-engine `monkey4` (Escape from Monkey Island) is off, experimental and incomplete upstream as well (Danik, 2026-10-28), and its games are not detected either (`engines/grim/detection.cpp`), so the launcher never adds a game it cannot start. Libraries besides SDL2 (zlib, libpng, libjpeg, FreeType, Ogg Vorbis, FLAC, libmad) are built static by `tools/build_deps.sh`.

### Video

`MisterGraphicsManager` (`mister-graphics.cpp`) makes the SDL window the game's size, 1x, no scaler and no aspect correction (a 15kHz screen shows 200 lines as 4:3 by itself), and draws into the window's own surface, which is the library's frame buffer (`SDL_MISTER_DIRECT`): no renderer, no texture, and only what changed in the last two frames is copied. The window's size picks the core's mode (`hybrid/sdl2`): 320x200 games in 320x200, 640x480 in 640x480i, 640x400 in 640x400i, other sizes centred in the smallest mode they fit. Frames are paced by `SDL_MISTER_VSYNC=1`. ScummVM's GUI is drawn at the game's resolution (no mode switch when the Global Main Menu opens); the launcher, with no game running, is 320x200 or 640x480 by the OSD's *Launcher* line, live while it is shown (`initSize()`), and takes a frame at every field of 480i (`MH_SetFieldRate()`, host version 18), a game never. The *Flicker Filter* is the core's (`FLICKER` 1); nothing in ScummVM for it. No 240-line mode and no HUD lines: the games' backgrounds and verb bars are fixed 200- or 480-line art.

ScummVM's GUI keeps 10 pixels from the screen's edges at 640x400 / 640x480 and 5 at 320x200, with every theme: the backend's safe area (`getSafeOverlayArea()`), ScummVM's own mechanism for phone notches. The layouts are still picked by the whole size (`MISTER_HYBRID` in `gui/gui-manager.cpp`).

### The theme, the icons and the artwork view

- **Theme** "MiSTer Hybrid" (`misterhybrid.zip`), the default, made by `tools/make_theme.py` into `build/theme/`: the purple screen's palette, Cozette 6x13 at every size for English (translations get ScummVM's TTFs), flat shapes, ScummVM's logo with the MiSTer logo beside it at 640x400 / 640x480, an 11x16 pointer at every resolution, ScummVM's common layouts with the game in grey behind the in-game menu and the artwork view. ScummVM's bitmap-font scaler crashes on Cozette, so the backend defaults `gui_disable_fixed_font_scaling` to true; the zip carries ScummVM's cache of the font (`cozette.fcc`). Of ScummVM's own themes only Modern is shipped.
- **Game icons**: every pack of downloads.scummvm.org `frs/icons/`, fetched at pinned SHA-256 sums by `tools/icons.sh` and merged by `tools/make_icons.py` (the newest pack's icon of a game wins; its `games.xml`, `companies.xml`, `series.xml` and `engines.xml` too), each icon made in the sizes the launcher draws it at (99, 143 and 236 pixels), so that ScummVM only decodes it: the full-size icons made the launcher slow on the MiSTer. The grid loads nothing before its layout gives the size (`gui/widgets/grid.cpp`) and shows at least 3 icons a row (`gui/launcher.cpp`). The icons show only at 640x480: ScummVM's 320x200 layout has the list alone.
- **Artwork view** (`LauncherArt` in `gui/launcher.cpp`, `gui_launcher_chooser=art`, the default): the list with the selected game's icon at 236x236 and its details (title, publisher and year, series, engine, platform, language and variant). Only the port's theme has its layout, at 640x480; elsewhere it is the list.

### Options

The OSD's game options (`applyOSD()` in `mister.cpp`) go into ConfMan's transient domain, over the games' and the global settings: the three volumes, *Subtitles* (`subtitles`, `speech_mute`), *Text Speed* (`talkspeed`), *Pointer Speed* (`kbdmouse_speed`), *Stick Deadzone* (`joystick_deadzone`). ScummVM's tabbed options dialogs are replaced by `MisterOptionsDialog` (`gui/mister-options.cpp`): one list in categories with only what the OSD does not do (theme, language, autosave, Roland GS, a game's own options, render mode, hotspots); `mister_full_options=true` in `scummvm.ini` brings ScummVM's own dialogs back. The cheat (*Fast Mode*, SCUMM's Ctrl+F / Ctrl+G) is read in `engines/scumm/input.cpp` and greyed out with `MH_SetMenuMask()` while another engine runs.

### Music

`MIDI_SYNTH` 1. With *Music* on MIDI the music driver is `mister` (`mister-midi.cpp`, a `MidiDriver_Emulated` with exact `ahead`): General MIDI to the core's synthesizer or an MT32-pi (ScummVM's MT-32-to-GM mapping where a game has MT-32 music only), native MT-32 to a Pi in MT-32 mode. The driver keeps every channel's state to send again after `MH_MidiSynthChanged()` and holds a song's start back by `MH_MidiBacklog()`. With *Music* on FM chip: AdLib through an OPL type of its own (`mister-opl.cpp`) writing `MH_FMWrite()` from a silent mixer stream, at exact audio frames; OPL3 and dual OPL2 games fall back to DOSBox's OPL on the ARM. Engines pick their driver once, so the MIDI / FM switch takes effect at the next game start, and a change while a game runs says so in ScummVM's on-screen message (an exception to the framework's rule, Danik's choice); the Pi / synthesizer switch is live. No Munt and no FluidSynth.

### Controls

The core's buttons are SDL joystick 1, mapped as a game controller (`MisterEventSource::addControllerMapping()`), with ScummVM's keymapper defaults changed in `getKeymapperDefaultBindings()`: the stick and the d-pad are the virtual mouse, L slows it, X Skip, Y Skip Line, R the game's menu; A, B, Select and Start keep ScummVM's (left click, right click, virtual keyboard, Global Main Menu). An engine's own pad keymap (Grim's) wins while it runs. The virtual mouse (`backends/keymapper/virtual-mouse.cpp`, `MISTER_HYBRID`) has the stick and the d-pad apart, as `VMOUSE*` and `VMOUSEDPAD*`: the stick's speed goes with the square of its tilt, a tap of the d-pad is two pixels (one with Slow Pointer held) and held it speeds up over a second, and the pointer moves once before every frame shown (`MisterGraphicsManager::updateScreen()`), by the fields counted between the last two frames, not when the engine polls. Main_MiSTer presses the d-pad as well when the stick is past half way (`dpad_threshold`): while the pointer is on the screen `MisterEventSource::isStickDpad()` stops that press, or the engines' d-pad actions came with the stick; with the pointer hidden it goes through, and Grim walks with the stick. *Menu OK* / *Menu Back* (`mister-events.cpp`) are Enter / Esc in ScummVM's GUI (Esc not in the launcher, where it would quit), a left click / Esc in a game's own menus. On a physical button that is one of the eight actions as well (`menuActions()`, from `MH_MenuButtons()`; every PlayStation or Xbox pad without a mapping has the bottom button Menu OK and B, the right one Menu Back and A): in the GUI it is only Menu OK, as a click at the pointer, or Menu Back (`isMenuAction()` stops the action), in a game only its action. Whether an action is held says nothing there: the library reads Menu OK / Back from Linux, ahead of the core's buttons. No rumble, triggers or stick clicks.

### Grim Fandango

Measured on the MiSTer with `MISTER_PROF` (Windows CD, Manny's office, 640x480i): from 5.7 to 9.5 fps to about 21 standing, 14 to 19 walking, 13 with Manny filling a third of the screen. What did it: TinyGL's dirty rectangles off (`dirtyrects`, `mister.cpp`); textures point sampled, as the original's software renderer (`engines/grim/gfx_tinygl.cpp`); in TinyGL (`graphics/tinygl/`) an opaque colour-keyed image kept in the frame buffer's format, a fast textured span for RGB565 with 32-bit textures (`putTexturedSpanFast()`, compared span by span with the generic code), the stencil-only fill of Grim's shadows as a `memset`, a clear left out where blits overwrite it, and the frame's base draw calls drawn again only where the last frame drew over them (`presentBufferSimple()`, whole frames compared); in the backend the direct frame buffer and the two-frame copy above (the shown buffer compared with ScummVM's screen). Escape from Monkey Island, while it was built in (2026-10-27), got all of it but the clear, and its 24-bit textures made 32-bit so its opaque faces take the fast span (`createTexture()`); that code stays in the fork, unused while `monkey4` is off.

## Building

Everything builds in Docker on a Linux PC.

```sh
git clone --recursive https://github.com/ItsDanik/ScummVM_MiSTer.git
cd ScummVM_MiSTer
./build.sh              # ARM game binary  -> build/mister/scummvm
./core/build_core.sh    # FPGA core (Quartus Lite 17.0.2) -> core/output_files/ScummVM.rbf
./package.sh            # release zip      -> dist/ScummVM_YYYYMMDD.zip
```

The toolchain image (Debian bullseye, glibc 2.31 to match the MiSTer) is built from `hybrid/toolchain/` on first use. The first build also downloads and builds SDL2, SDL2_mixer and SDL2_net, and the libraries ScummVM uses (`tools/build_deps.sh`). `./package.sh` makes the theme (`tools/make_theme.py`), fetches the game icons (`tools/icons.sh`, kept in `build/icons/`) and the SoundFont (`hybrid/tools/soundfont.sh`), none of them committed.

### Repository layout

| Path | |
|---|---|
| `hybrid/` | submodule: [ItsDanik/Hybrid_MiSTer](https://github.com/ItsDanik/Hybrid_MiSTer), what all our hybrid ports share: the FPGA host module, the ARM side library, SDL2 drivers, the launcher (`danik_hybrid_ports.sh`), toolchain and conventions. See its README. |
| `core/` | FPGA core, based on [Template_MiSTer](https://github.com/MiSTer-devel/Template_MiSTer): `ScummVM.sv` (OSD and button names) around `hybrid/rtl/hybrid_host.sv` |
| `scummvm/` | submodule: [ItsDanik/scummvm](https://github.com/ItsDanik/scummvm) branch `mister`, [ScummVM](https://github.com/scummvm/scummvm) with the MiSTer backend (`backends/platform/sdl/mister/`) and a few `#ifdef MISTER_HYBRID` |
| `tools/` | `build_deps.sh` (the libraries), `make_theme.py` (the theme), `icons.sh` and `make_icons.py` (the game icons), `theme_preview.sh`, `prof.py`, and the template's `deploy.sh` and `test_on_mister.sh` |
| `package/` | files shipped in the release next to the binary (`danik_hybrid_launch.sh`, README), `games.txt`: the games and their menu entries, the logo, the OLED pictures and `info.txt` |
| `releases/` | release packages |

### Development notes

- `./build.sh host` builds the same game for the PC. It runs against `hybrid/tools/fakecore`, a stand-in for the FPGA core that takes scripted input and saves screenshots and audio. The engines' data files are looked for in `data/` next to the program: copy those a game needs (`lure.dat`, `sky.cpt`, ...) from the package's `data/` into `build/host/data/`.
  ```sh
  gcc -O2 -o build/host/fakecore hybrid/tools/fakecore.c
  build/host/fakecore /tmp/shm script.txt audio.raw &
  cd <data folder> && MISTER_HYBRID_SHM=/tmp/shm <repository>/build/host/scummvm
  ```
- `MISTER=root@<address> tools/test_on_mister.sh ScummVM` tries the build on a MiSTer next to what is installed there, without installing it: from `/tmp`, with the installed game's folder mirrored there (what ScummVM writes, `scummvm.ini`, `saves/` and `config/`, is copied, so it stays in `/tmp`) and its own OSD settings. `list` and `nodata` for the core started by itself and without data, `log` for the game's log, `stop` to remove all of it again.
- `touch /tmp/scummvm_nolaunch` on the MiSTer keeps the core loaded without starting the game, so you can start a development binary by hand (set `MISTER_HYBRID_CORE=ScummVM`). `/tmp/danik_hybrid_ports.log` shows what the launcher daemon did.
- `MISTER_PROF=<file>` (`mister-prof.cpp`) samples where the time goes on the MiSTer, which has no `perf`, and prints the frames shown per second; `tools/prof.py` makes the table with the unstripped binary's `nm` (libc on the MiSTer is dynamic and stripped: its time shows as one line).
- `tools/theme_preview.sh <folder or zip> [low|400|480] [--start <id>] [--shot out.png ...]` shows a theme in the ScummVM installed on the PC, 1x as the MiSTer draws it, without the CRT margin (the PC build against `fakecore` has it).
- What ScummVM prints goes to `/tmp/scummvm.log` while it runs and is added to `logs/dnk/ScummVM/scummvm.log` when it ends (the SD card is mounted `sync`, and every line written to it would stop the game); ScummVM's own log file is `/tmp/scummvm_mister.log`.
