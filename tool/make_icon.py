"""
Genera icona.ico (collegamento / app): Ledino, la mascotte accesa su una matrice LED.

    python tool/make_icon.py

Dai 48 px in su ogni pixel è un LED tondo, con i LED spenti appena visibili
sul fondo, sopra la mascotte la scritta LEDINO e sotto una barra di consumo
(come limit_bar del pannello); sotto i 48 px solo la mascotte a quadrati
pieni, altrimenti si sfoca.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))   # make_sprites e render stanno in src/

import pygame

from make_sprites import SHADOW, body, frame
from render import BG, FG, MASCOT_BODY

OUT = ROOT / "icona.ico"
OFF_LED = (34, 38, 48)
SIZES = (256, 128, 64, 48, 32, 24, 16)

# Font 5 righe, larghezza variabile: LEDINO = 23 colonne con gli spazi
FONT = {
    "L": ["#..", "#..", "#..", "#..", "###"],
    "E": ["###", "#..", "##.", "#..", "###"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "I": ["#", "#", "#", "#", "#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#"],  # 4 colonne sembrava una M
    "O": ["###", "#.#", "#.#", "#.#", "###"],
}
NAME = "LEDINO"
BAR_FULL, BAR_TICK = 11, 12     # barra finta: LED pieni, posizione della tacca


def mascot() -> Image.Image:
    surf = frame(lambda s: body(s, mouth="grin"))
    im = Image.frombytes("RGBA", surf.get_size(), pygame.image.tobytes(surf, "RGBA"))
    im.putdata([(0, 0, 0, 0) if p[:3] == SHADOW else p for p in im.getdata()])  # niente ombra
    return im.crop(im.getbbox())


def leds(text: bool) -> tuple[int, dict[tuple[int, int], tuple[int, int, int]]]:
    """(lato griglia, LED accesi): mascotte centrata; se text, scritta sopra e barra sotto."""
    m = mascot()
    cells = 26 if text else 22
    text_h, gap = (5, 2) if text else (0, 0)
    bar_h = 4 if text else 0           # 2 righe vuote + barra alta 2
    top = (cells - (text_h + gap + m.height + bar_h)) // 2
    on = {}
    if text:
        width = sum(len(FONT[c][0]) for c in NAME) + len(NAME) - 1
        x = (cells - width) // 2
        for c in NAME:
            for dy, row in enumerate(FONT[c]):
                for dx, ch in enumerate(row):
                    if ch == "#":
                        on[(x + dx, top + dy)] = FG
            x += len(FONT[c][0]) + 1
    ox, oy = (cells - m.width) // 2, top + text_h + gap
    for y in range(m.height):
        for x in range(m.width):
            p = m.getpixel((x, y))
            if p[3] > 128:
                on[(x + ox, y + oy)] = p[:3]
    if text:
        width = sum(len(FONT[c][0]) for c in NAME) + len(NAME) - 1
        x0, by = (cells - width) // 2, oy + m.height + 2
        for y in (by, by + 1):
            for x in range(width):
                on[(x0 + x, y)] = MASCOT_BODY if x < BAR_FULL else tuple(int(c * 0.35) for c in MASCOT_BODY)
        for y in range(by - 1, by + 3):   # tacca del tempo trascorso, sporge sopra e sotto
            on[(x0 + BAR_TICK, y)] = FG
    return cells, on


def tile(size: int, big_icon: bool) -> Image.Image:
    s = 4 if big_icon else 1           # supersampling per i LED tondi
    big = size * s
    img = Image.new("RGBA", (big, big), (*BG, 255))
    d = ImageDraw.Draw(img)
    cells, on = leds(text=big_icon)
    cell = big / cells
    for gy in range(cells):
        for gx in range(cells):
            color = on.get((gx, gy))
            x0, y0 = gx * cell, gy * cell
            if big_icon:
                pad = cell * 0.12
                d.ellipse((x0 + pad, y0 + pad, x0 + cell - pad, y0 + cell - pad), fill=color or OFF_LED)
            elif color:
                d.rectangle((x0, y0, x0 + cell, y0 + cell), fill=color)
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=big // 5, fill=255)
    img.putalpha(mask)
    return img.resize((size, size), Image.LANCZOS) if s > 1 else img


if __name__ == "__main__":
    imgs = [tile(n, big_icon=n >= 48) for n in SIZES]
    for text in (True, False):
        cells, on = leds(text)
        assert all(0 <= x < cells and 0 <= y < cells for x, y in on), "LED fuori griglia"
    imgs[0].save(OUT, sizes=[i.size for i in imgs], append_images=imgs[1:])
    print(f"{OUT}  ({', '.join(map(str, SIZES))} px)")
