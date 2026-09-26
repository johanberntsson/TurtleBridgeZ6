#!/usr/bin/env python3
"""Cut Turtle Bridge's LCD segments out of the sprite sheet and build the Blorb.

usage: make_graphics.py <sprite sheet> <ozmoo tools dir>

Writes, into the current directory:
  turtlebridge.blb  the pictures, pixel doubled for a 640x400 screen (Reso)
  graphics.h        Inform constants and tables describing every picture
  pics/             the converted PNGs and preview.png (every slot lit)

The game is a Game & Watch: every sprite has one fixed place on the screen.
The screen is split into *slots* (a turtle, a player position, a score digit),
each showing at most one of its sprites at a time. A slot has one "clear"
picture, an opaque crop of the backdrop covering all its sprites, snapped
out to the 8x8 cell grid so that Ozmoo can copy it rather than generate it.
Sprites are black with transparent surroundings. To change a slot the game
draws its clear picture and then redraws the sprites of every slot that
clear picture overlaps (see graphics.h: slot_ovl).

Every picture shares one palette, the backdrop's. The backdrop is the only
direct picture; all others are listed as adaptive in an APal chunk, so the
MEGA65 draws them in the backdrop's palette bank rather than spending one of
its fourteen banks on each. sfrotz then also works in palette mode, and the
indices agree because every PNG carries the same palette.

The Blorb itself is written with make_blorb.py's helpers (pixel doubling,
the Reso chunk and the IFF writer), so the result matches what that tool
builds for a 640x400 screen.
"""

import os
import sys

from PIL import Image

SHEET_BACKDROP = (1, 1, 161, 145)   # 160x144, inside a 1-pixel white border
ART_W, ART_H = 224, 200             # the backdrop scaled to fill 200 rows
SCALE = 2                           # stored at 640x400 for sfrotz/Windows Frotz
CELL = 8
INK = (0, 0, 0)

# Source rectangles in the sprite sheet (x0, y0, x1, y1, inclusive). Each is
# trimmed to its dark pixels, so the boxes only need to be roughly right.
SRC = {
    # the player carrying a package on his head, and without it
    "A0": (1, 154, 18, 177), "A1": (20, 154, 36, 177), "A2": (38, 154, 55, 177),
    "A3": (57, 154, 74, 177), "A4": (76, 154, 95, 177), "A5": (97, 154, 116, 177),
    "B0": (1, 179, 18, 197), "B1": (20, 179, 36, 197), "B2": (38, 179, 55, 197),
    "B3": (57, 179, 75, 197), "B4": (77, 179, 96, 197), "B5": (98, 179, 114, 197),
    # waiting, reaching, handing the package up, catching it
    "C0": (1, 213, 17, 233), "C1": (19, 213, 32, 233),
    "C2": (34, 199, 49, 233), "C3": (51, 207, 68, 233),
    # the two men on the cliffs
    "D0": (0, 234, 15, 261), "D1": (16, 234, 38, 261), "D2": (39, 234, 54, 261),
    "D3": (55, 234, 70, 261), "D4": (71, 234, 86, 261), "D5": (87, 234, 109, 261),
    # falling in, and the splash
    "E0": (0, 262, 17, 299), "E1": (18, 262, 35, 299),
    # turtles: head down (eating), swimming, diving; two sets
    "T0": (1, 299, 18, 318), "T1": (19, 299, 39, 318), "T2": (40, 299, 54, 318),
    "T3": (55, 299, 72, 318), "T4": (73, 299, 93, 318), "T5": (94, 299, 108, 318),
    "F0": (1, 319, 9, 324), "F1": (10, 319, 18, 324),
    "F2": (19, 319, 27, 324), "F3": (28, 319, 36, 324),
    "MISS": (9, 325, 27, 331),
    "M0": (1, 332, 12, 343),
    "N0": (38, 325, 45, 339), "N1": (45, 325, 49, 339), "N2": (49, 325, 57, 339),
    "N3": (57, 325, 64, 339), "N4": (64, 325, 71, 339), "N5": (71, 325, 77, 339),
    "N6": (77, 325, 84, 339), "N7": (84, 325, 90, 339), "N8": (90, 325, 98, 339),
    "N9": (98, 325, 105, 339),
}

# Turtle and player columns, in backdrop coordinates (160x144).
TURTLE_X = [32, 56, 80, 104, 128]
SHORE_L, SHORE_R = 10, 151

# Each slot: name, anchor (bottom centre, backdrop coordinates) and its
# sprites as (name, source, flip, dx, dy). A sprite's bottom centre goes on
# the anchor, moved by dx, dy. Slots are listed bottom to top: a slot's
# sprite is drawn over those of the slots before it.
def build_slots():
    slots = []
    for k, x in enumerate(TURTLE_X, 1):
        slots.append((f"FISH{k}", (x, 104), [
            ("A", "F0", False, 0, 0), ("B", "F1", False, 0, 0)]))
    for k, x in enumerate(TURTLE_X, 1):
        s = ("T1", "T0", "T2") if k % 2 else ("T4", "T3", "T5")
        slots.append((f"TURTLE{k}", (x, 79), [
            ("SWIM", s[0], False, 0, 0), ("EAT", s[1], False, 0, 0),
            ("DIVE", s[2], False, 0, 2)]))
    slots.append(("PLAYER0", (SHORE_L, 74), [
        ("CARRY", "A0", False, 0, 0), ("EMPTY", "C1", False, 0, 0)]))
    for k, x in enumerate(TURTLE_X, 1):
        slots.append((f"PLAYER{k}", (x, 67), [
            ("CARRY", f"A{k}", False, 0, 0), ("EMPTY", f"B{k - 1}", True, 0, 0),
            ("FALL", "E0", False, 0, 20), ("SPLASH", "E1", False, 0, 26)]))
    slots.append(("PLAYER6", (SHORE_R, 74), [
        ("CARRY", "C2", False, 0, 0), ("EMPTY", "B5", True, 0, 0)]))
    slots.append(("SENDER", (10, 33), [
        ("IDLE", "D0", False, 0, 0), ("GIVE", "D1", False, 4, 0)]))
    slots.append(("RECEIVER", (137, 36), [
        ("IDLE", "D3", True, 0, 0), ("TAKE", "D4", True, 0, 0),
        ("LIFT", "D5", True, 0, 0)]))
    for i in range(4):
        slots.append((f"DIGIT{i + 1}", (68 + 8 * i, 17),
                      [(str(d), f"N{d}", False, 0, 0) for d in range(10)]))
    slots.append(("MISSLABEL", (80, 27), [("ON", "MISS", False, 0, 0)]))
    for i in range(3):
        slots.append((f"MISS{i + 1}", (67 + 13 * i, 41),
                      [("ON", "M0", False, 0, 0)]))
    return slots


def pixels(im):
    """An image's pixels as a flat sequence (getdata is deprecated)."""
    get = getattr(im, "get_flattened_data", None)
    return get() if get else ipixels(m)


def dark(p):
    return sum(p[:3]) < 200


def cut(sheet, box):
    """The dark pixels in box as a 1-bit mask ('L', 255 = ink), trimmed."""
    x0, y0, x1, y1 = box
    region = sheet.crop((x0, y0, x1 + 1, y1 + 1))
    mask = Image.new("L", region.size, 0)
    mask.putdata([255 if dark(p) else 0 for p in pixels(region)])
    bbox = mask.getbbox()
    if bbox is None:
        raise SystemExit(f"no ink in sheet box {box}")
    return mask.crop(bbox)


def scale_mask(mask, bx, by):
    """Place a backdrop-resolution mask at (bx, by), scale it to the art size
    with an area filter, threshold, and return (image, x, y) trimmed."""
    layer = Image.new("L", (SHEET_BACKDROP[2] - SHEET_BACKDROP[0],
                            SHEET_BACKDROP[3] - SHEET_BACKDROP[1]), 0)
    layer.paste(mask, (bx, by))
    big = layer.resize((ART_W, ART_H), Image.BOX)
    big = big.point(lambda v: 255 if v >= 90 else 0)
    bbox = big.getbbox()
    return big.crop(bbox), bbox[0], bbox[1]


def main(argv):
    if len(argv) != 3:
        sys.exit(f"usage: {argv[0]} <sprite sheet> <ozmoo tools dir>")
    sys.path.insert(0, argv[2])
    import make_blorb

    sheet = Image.open(argv[1]).convert("RGB")
    backdrop = sheet.crop(SHEET_BACKDROP).resize((ART_W, ART_H), Image.NEAREST)

    # The shared palette: index 0 transparent, then the backdrop's colours.
    colours = [c for _n, c in sorted(backdrop.getcolors(256), reverse=True)]
    if INK not in colours:
        colours.append(INK)
    if len(colours) > 15:
        sys.exit(f"backdrop has {len(colours)} colours; at most 15 fit")
    index = {c: i + 1 for i, c in enumerate(colours)}
    palette = [0, 0, 0] + [v for c in colours for v in c]
    palette += [0, 0, 0] * (16 - len(palette) // 3)

    def indexed(w, h, pixels):
        im = Image.new("P", (w, h))
        im.putdata(pixels)
        im.putpalette(palette)
        im.info["transparency"] = 0
        return im

    def crop_backdrop(x0, y0, x1, y1):
        region = backdrop.crop((x0, y0, x1, y1))
        return indexed(x1 - x0, y1 - y0, [index[p] for p in pixels(region)])

    pictures = []       # (number, name, image, x, y) in art pixels
    def add(name, im, x, y):
        pictures.append((len(pictures) + 1, name, im, x, y))
        return len(pictures)

    add("BACKDROP", crop_backdrop(0, 0, ART_W, ART_H), 0, 0)

    masks = {k: cut(sheet, box) for k, box in SRC.items()}
    slots = build_slots()

    # Place every sprite first, so each slot's clear box is known.
    placed = []         # per slot: list of (sprite name, mask, x, y)
    for sname, (ax, ay), sprites in slots:
        out = []
        for spname, src, flip, dx, dy in sprites:
            m = masks[src]
            if flip:
                m = m.transpose(Image.FLIP_LEFT_RIGHT)
            bx = ax - m.width // 2 + dx
            by = ay - m.height + dy
            im, x, y = scale_mask(m, bx, by)
            out.append((spname, im, x, y))
        placed.append(out)

    clear_boxes = []
    for sprites in placed:
        x0 = min(x for _n, _m, x, _y in sprites)
        y0 = min(y for _n, _m, _x, y in sprites)
        x1 = max(x + m.width for _n, m, x, _y in sprites)
        y1 = max(y + m.height for _n, m, _x, y in sprites)
        x0, y0 = x0 // CELL * CELL, y0 // CELL * CELL
        x1 = min(ART_W, -(-x1 // CELL) * CELL)
        y1 = min(ART_H, -(-y1 // CELL) * CELL)
        clear_boxes.append((x0, y0, x1, y1))

    clear_pics = []
    for (sname, _a, _s), (x0, y0, x1, y1) in zip(slots, clear_boxes):
        clear_pics.append(add(f"CLEAR_{sname}",
                              crop_backdrop(x0, y0, x1, y1), x0, y0))

    sprite_pics = []    # per slot: list of (sprite name, picture number)
    ink = index[INK]
    for (sname, _a, _s), sprites in zip(slots, placed):
        nums = []
        for spname, m, x, y in sprites:
            im = indexed(m.width, m.height,
                         [ink if v else 0 for v in pixels(m)])
            nums.append((spname, add(f"{sname}_{spname}", im, x, y)))
        sprite_pics.append(nums)

    # Which slots each slot's clear picture touches (including itself).
    def overlaps(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    sprite_boxes = []
    for sprites in placed:
        sprite_boxes.append([(x, y, x + m.width, y + m.height)
                             for _n, m, x, y in sprites])
    ovl = []
    for i, cb in enumerate(clear_boxes):
        ovl.append([j for j in range(len(slots))
                    if j == i or any(overlaps(cb, sb) for sb in sprite_boxes[j])])

    # Write the converted pictures, a preview and the Blorb.
    os.makedirs("pics", exist_ok=True)
    resources, apal = [], b""
    for num, name, im, _x, _y in pictures:
        big = make_blorb.upscale(im, SCALE)
        big.save(os.path.join("pics", f"{num:03d}-{name.lower()}.png"))
        resources.append((b"Pict", num, b"PNG ", make_blorb.png_bytes(big)))
        if num != 1:
            apal += num.to_bytes(4, "big")
    extra = [(b"Reso", make_blorb.reso_chunk(SCALE)), (b"APal", apal)]
    size = make_blorb.build_blorb(resources, "turtlebridge.blb", extra)

    # preview.png lights every slot's first sprite, preview2.png its second
    # and so on, for checking the layout by eye.
    for n in range(max(len(s) for s in placed)):
        preview = backdrop.copy()
        for sprites in placed:
            if n < len(sprites):
                _n, m, x, y = sprites[n]
                preview.paste(INK, (x, y), m)
        preview.resize((ART_W * 3, ART_H * 3), Image.NEAREST).save(
            os.path.join("pics", f"preview{n + 1 if n else ''}.png"))

    with open("graphics.h", "w") as f:
        f.write("! Generated by tools/make_graphics.py -- do not edit.\n\n"
                "System_file;\n\n")
        f.write(f"Constant GAME_W = {ART_W};\nConstant GAME_H = {ART_H};\n")
        f.write(f"Constant PIC_BACKDROP = 1;\n")
        f.write(f"Constant NUM_PICTURES = {len(pictures)};\n")
        f.write(f"Constant NUM_SLOTS = {len(slots)};\n\n")
        for i, (sname, _a, _s) in enumerate(slots):
            f.write(f"Constant SLOT_{sname} = {i};\n")
        f.write("\n")
        for sname_nums, (sname, _a, _s) in zip(sprite_pics, slots):
            for spname, num in sname_nums:
                f.write(f"Constant PIC_{sname}_{spname} = {num};\n")
        f.write("\n! Where each picture goes, in art pixels from the game "
                "area's top left.\n")
        f.write("Array pic_x --> 0 " +
                " ".join(str(x) for _n, _nm, _i, x, _y in pictures) + ";\n")
        f.write("Array pic_y --> 0 " +
                " ".join(str(y) for _n, _nm, _i, _x, y in pictures) + ";\n")
        f.write("\n! Each slot's clear picture.\n")
        f.write("Array slot_clear --> " +
                " ".join(str(n) for n in clear_pics) + ";\n")
        f.write("\n! The slots whose sprites each slot's clear picture "
                "overlaps: slot_ovl_start-->s indexes slot_ovl, a list "
                "ending in 255.\n")
        starts, flat = [], []
        for lst in ovl:
            starts.append(len(flat))
            flat += lst + [255]
        f.write("Array slot_ovl_start --> " +
                " ".join(map(str, starts)) + ";\n")
        f.write("Array slot_ovl -> " + " ".join(map(str, flat)) + ";\n")

    print(f"Wrote turtlebridge.blb ({size} bytes, {len(pictures)} pictures, "
          f"{len(colours)} colours), graphics.h and pics/")


if __name__ == "__main__":
    main(sys.argv)
