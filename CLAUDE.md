# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An arcade game on the Z-machine: Nintendo's Game & Watch *Turtle Bridge*, written in Inform 6 for version 6 (graphics). It does not use the PunyInform library or its parser. It only includes `ext_z6graphics.h` from `$(PUNY)/lib`. The main target is `turtlebridge.z6` + `turtlebridge.blb` in sfrotz. It must also stay playable on the MEGA65 through Ozmoo, the z6 branch now merged into `$(OZMOO)`. `~/commodore/ozmoo-z6` has Ozmoo's z6 notes (its CLAUDE.md), the tools and `z-spec10.pdf`.

## Build and run

Tool paths are set at the top of the `Makefile`.

- `make` / `make sfrotz`: builds everything and runs it in sfrotz. The blorb has to be passed on the command line.
- `make z6`: builds only the story file. `make blorb`: builds only the graphics.
- `make mega65_turtlebridge.d81` / `make mega65`: the MEGA65 build (`make.rb -t:mega65 -fcm -pics`), and running it in xemu.
- `make x16_turtlebridge.zip`: the X16 build. It is not a target and has not been tested.

There are no tests. To check a change, play it. Headless recipes:

- **sfrotz:** `xvfb-run` it, send keys with `xdotool key --window <id>`, and take a screenshot with `import -window root`.
- **MEGA65:** run `xemu-xmega65 -headless -autoload -uartmon <sock> -screenshot out.png` and type keys through the monitor socket: `s0277 <petscii>` then `s00c6 01`. Cursor right is `1d`, left is `9d`. The screenshot is only written when xemu exits. Keep the socket path short, because AF_UNIX paths are limited to about 108 characters.

## Architecture

**Graphics pipeline.** `tools/make_graphics.py` reads `TurtleBridgeGraphics.png` and writes `turtlebridge.blb`, `graphics.h` and `pics/`. All three are generated and ignored by git. The sheet is a rip of the LCD segments, so on-screen positions are *not* in it. They come from the slot table in `build_slots()`: anchor points in the 160x144 backdrop's coordinates, with sprites placed bottom-centre on them. `pics/preview*.png` shows every slot lit, one image per sprite variant, for checking the layout by eye. Everything is scaled to 224x200 art pixels and centred on the 320x200 screen, and the borders hold text windows.

**Slots.** Each slot (a turtle, a player position, a score digit…) shows at most one sprite at a time. Each slot also has an opaque "clear" picture: the backdrop behind all its sprites, snapped to the 8x8 cell grid. Sprites are black with index-0 transparency. `Flush()` in the story draws a changed slot's clear picture, then redraws the sprites of every slot listed in `slot_ovl` for it. Sprite picture numbers are consecutive within a slot, and slots of the same kind have the same layout. So the code finds turtle *k*'s sprite as `PIC_TURTLE1_x + (k-1) * stride` (see `ShowState`). Keep that invariant when adding sprites.

**Shared palette and APal. This is why `make_blorb.py` isn't used directly.** Every picture uses the backdrop's palette at the same indices. Only the backdrop is a direct picture; all the others are listed in an `APal` chunk. On the MEGA65 an adaptive picture draws in the last direct picture's palette bank. Otherwise each distinct picture on screen would take one of only 14 banks, and this game shows more than 14 at once. sfrotz also switches to palette mode when `APal` is present. `make_blorb.py` quantises each picture separately and has no transparency, so the script imports its helpers instead (`upscale`, `png_bytes`, `reso_chunk`, `build_blorb`). The Blorb is stored at `scale` 2 with a `Reso` chunk, for sfrotz and Windows Frotz.

**Units.** sfrotz reports a 640x400 screen and pixel-doubled picture sizes; Ozmoo reports 320x200. `InitScreen` gets `scale` from the backdrop's `picture_data` height divided by `GAME_H`. Every coordinate is art pixels × `scale`, relative to the centred origin.

**Game loop.** `@read_char 1 1 TickOver` is a 0.1 s tick. A key moves the player straight away. Every `step_ticks` timeouts, `WorldStep()` advances the turtles, fish and the men on the cliffs. `ShowState()` then maps the game state onto slots, and `Flush()` redraws only what changed. World time only counts timeouts, so fast key presses slow the world slightly.

## Status (2026-09-26)

It is a fun side project, first playable version committed (`ef02161`). The story file is 8.5K and the blorb has 126 pictures.

- **Verified:** it plays in sfrotz and on the MEGA65 under xemu, driven by scripts rather than played by hand. The screens match, and the MEGA65 keeps up at roughly real time: 40 world steps in about 30 s, against 0.7 s per step nominal.
- **Not tested:** the X16 build and Windows Frotz.
- **The layout is a reconstruction.** The sheet doesn't record where segments go, so the positions in `build_slots()` were chosen by eye, not taken from the original LCD.
- **The rules are approximations of the original:**
  - A fish swims toward a turtle. The turtle dips its head (`T_EAT`, 2 steps, still safe), then dives (`T_DIVE`, and anyone on it falls), then stays under 3–5 steps.
  - The sender hands over a package one step after the player reaches the left shore empty-handed. The receiver takes it one step after arrival on the right.
  - Scoring is +1 per step onto a turtle while carrying, +10 per delivery. 300 points clears the misses.
  - Game B is faster, with more fish and longer dives.
- **Unused sprites:** some are still unused (`C0`, `C3`, `D2`, `F2`, `F3`), and so are the sheet's "GAME A/B" labels.
- **Possible upstream change:** `make_blorb.py` could gain shared-palette/adaptive and transparency support, which would shrink `make_graphics.py` to sprite cutting.
