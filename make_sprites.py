"""
Genera in sprites/ la mascotte in stile Claude Code (pixel art 32x32, animata).

    python make_sprites.py

Render.Mascot carica da sola sprites/<stato>_<n>.png al prossimo avvio
del monitor. Per tornare al robottino basta cancellare la cartella sprites/.

32x32 perché è la dimensione nativa della mascotte su LED e Pixoo (1:1)
e sul TFT diventa 96x96 (x3): niente pixel deformati.

Il corpo resta arancione; gli oggetti sopra la testa usano il colore
dello stato (azzurro lavora, ambra attende, verde finito, grigio pausa).
"""

from pathlib import Path

import pygame

from render import STATUS_COLOR
from state import DONE, IDLE, WAITING, WORKING

OUT = Path(__file__).resolve().parent / "sprites"

BODY = (217, 119, 87)       # arancio terracotta
BODY_IDLE = (160, 98, 80)   # più spento in pausa
EYE = (24, 22, 22)
MOUTH = (245, 236, 225)
INK = (24, 22, 22)          # testo dentro i fumetti

# --- Oggetti (ASCII: # = colore dato, k = INK, w = chiaro, . = trasparente) -------------
BOLT = [
    "..##",
    ".##.",
    "####",
    ".##.",
    "##..",
    "#...",
]
BUBBLE_Q = [
    ".#######.",
    "###kk####",
    "#####k###",
    "####k####",
    "#########",
    "####k####",
    ".#######.",
    "..#......",
]
CHECK = [
    "......##",
    ".....##.",
    "##..##..",
    ".####...",
    "..##....",
]
Z_BIG = ["#####", "...#.", "..#..", ".#...", "#####"]
Z_SMALL = ["####", "..#.", ".#..", "####"]
SPARK = [".#.", "###", ".#."]


def stamp(surf, art, x, y, color):
    for dy, line in enumerate(art):
        for dx, ch in enumerate(line):
            if ch == "#":
                surf.set_at((x + dx, y + dy), color)
            elif ch == "k":
                surf.set_at((x + dx, y + dy), INK)
            elif ch == "w":
                surf.set_at((x + dx, y + dy), MOUTH)


def rect(surf, x, y, w, h, color):
    pygame.draw.rect(surf, color, (x, y, w, h))


def body(surf, lift=0, arms="down", legs=0, eyes="open", mouth="smile", color=BODY, sit=False):
    """
    Corpo 14x8 con braccia, gambe e faccia.
    lift: sposta su di N pixel (saltello). legs: 0/1 fase della camminata.
    arms: down | up | left_up | right_up. sit: niente gambe, corpo più basso.
    """
    y0 = 16 - lift + (2 if sit else 0)
    x0 = 9
    rect(surf, x0, y0, 14, 8, color)
    # Braccia
    left_up = arms in ("up", "left_up")
    right_up = arms in ("up", "right_up")
    if left_up:
        rect(surf, x0 - 2, y0 - 4, 2, 6, color)
    else:
        rect(surf, x0 - 2, y0 + 3, 2, 2, color)
    if right_up:
        rect(surf, x0 + 14, y0 - 4, 2, 6, color)
    else:
        rect(surf, x0 + 14, y0 + 3, 2, 2, color)
    # Gambe
    if not sit:
        xs = (1, 3, 10, 12) if legs == 0 else (2, 4, 9, 11)
        for lx in xs:
            rect(surf, x0 + lx, y0 + 8, 1, 3, color)
    # Occhi
    ey = y0 + 2
    if eyes == "open":
        for ex in (3, 10):
            rect(surf, x0 + ex, ey, 1, 2, EYE)
    elif eyes == "focus":  # sopracciglio inclinato: concentrato
        for ex, bx in ((3, 2), (10, 11)):
            rect(surf, x0 + ex, ey + 1, 1, 1, EYE)
            rect(surf, x0 + bx, ey, 1, 1, EYE)
    elif eyes == "side":
        for ex in (2, 9):
            rect(surf, x0 + ex, ey, 1, 2, EYE)
    elif eyes == "happy":  # ^ ^
        for ex in (3, 10):
            surf.set_at((x0 + ex, ey), EYE)
            surf.set_at((x0 + ex - 1, ey + 1), EYE)
            surf.set_at((x0 + ex + 1, ey + 1), EYE)
    elif eyes == "closed":
        for ex in (2, 9):
            rect(surf, x0 + ex, ey + 1, 3, 1, EYE)
    # Bocca
    my = y0 + 5
    if mouth == "smile":
        rect(surf, x0 + 6, my, 2, 1, MOUTH)
    elif mouth == "grin":
        rect(surf, x0 + 5, my, 4, 1, MOUTH)
        rect(surf, x0 + 6, my + 1, 2, 1, MOUTH)
    elif mouth == "o":
        rect(surf, x0 + 6, my, 2, 2, MOUTH)
    elif mouth == "flat":
        rect(surf, x0 + 6, my + 1, 2, 1, MOUTH)
    return y0


def frame(draw):
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    draw(surf)
    return surf


# --- Stati ------------------------------------------------------------------
def working(i):
    """Cammina concentrato, fulmini che lampeggiano sopra la testa."""
    c = STATUS_COLOR[WORKING]

    def draw(s):
        lift = i % 2
        top = body(s, lift=lift, legs=i % 2, eyes="focus", mouth="smile")
        if i in (0, 1):
            stamp(s, BOLT, 10, top - 8, c)
        if i in (2, 3):
            stamp(s, BOLT, 18, top - 8, c)
        stamp(s, SPARK, 4 if i < 2 else 25, top - 6 + i % 2, c)
    return frame(draw)


# Oggetto per gruppo di tool: due frame ciascuno (k = inchiostro scuro).
# I gruppi corrispondono a TOOL_GROUPS in render.py.
TOOL_PROPS = {
    "bash": [  # terminale con cursore che lampeggia
        ["#########", "#kkkkkkk#", "#k#kkkkk#", "#kk#kkkk#", "#k#k###k#", "#kkkkkkk#", "#########"],
        ["#########", "#kkkkkkk#", "#k#kkkkk#", "#kk#kkkk#", "#k#kkkkk#", "#kkkkkkk#", "#########"],
    ],
    "read": [  # lente che scorre
        [".###...", "#...#..", "#...#..", "#...#..", ".###...", "....##.", ".....##"],
        ["..###..", ".#...#.", ".#...#.", ".#...#.", "..###..", ".....##", "......#"],
    ],
    "edit": [  # matita che scrive
        [".....##", "....###", "...###.", "..###..", ".###...", "w##....", "ww....."],
        ["......##", ".....###", "....###.", "...###..", "..###...", ".w##....", ".ww.#.#."],
    ],
    "web": [  # globo che ruota
        ["..###..", ".#k#k#.", "#kk#kk#", "#######", "#kk#kk#", ".#k#k#.", "..###.."],
        ["..###..", ".##k##.", "#k#k#k#", "#######", "#k#k#k#", ".##k##.", "..###.."],
    ],
    "todo": [  # lista che si spunta
        [".#####.", "#######", "#k#kkk#", "#######", "#k#kk##", "#######", "#k#k###", "#######"],
        [".#####.", "#######", "#k#kkk#", "#######", "#k#kkk#", "#######", "#k#kk##", "#######"],
    ],
    "mcp": [  # spina
        [".#.#.", ".#.#.", "#####", "#####", ".###.", "..#..", "..#.."],
        [".#.#.", ".#.#.", "#####", "#####", ".###.", "..#..", "....."],
    ],
    "agent": [  # mini aiutante che saltella (disegnato a parte, vedi working_tool)
        None, None,
    ],
}


def working_tool(group, i):
    """Come working(), ma con l'oggetto del tool al posto dei fulmini."""
    c = STATUS_COLOR[WORKING]

    def draw(s):
        top = body(s, lift=i % 2, legs=i % 2, eyes="focus", mouth="smile")
        if group == "agent":
            # Due mini-mascotte che saltellano a turno
            for n, x in enumerate((6, 19)):
                y = top - 7 - (1 if (i + n) % 2 else 0)
                rect(s, x + 1, y, 6, 3, BODY)          # corpo
                s.set_at((x, y + 1), BODY)             # braccia
                s.set_at((x + 7, y + 1), BODY)
                s.set_at((x + 2, y + 1), EYE)          # occhi
                s.set_at((x + 5, y + 1), EYE)
                for lx in (2, 5):                      # gambe
                    s.set_at((x + lx, y + 3), BODY)
            return
        art = TOOL_PROPS[group][(i // 2) % 2]
        w, h = len(art[0]), len(art)
        stamp(s, art, 16 - w // 2, top - h - 2 + (i % 2), c)
    return frame(draw)


def waiting(i):
    """Fumetto col punto di domanda e saluto alternato: ti sta aspettando."""
    c = STATUS_COLOR[WAITING]

    def draw(s):
        arms = ("left_up", "down", "right_up", "down")[i]
        top = body(s, arms=arms, eyes="side" if i < 2 else "open", mouth="o")
        stamp(s, BUBBLE_Q, 12, top - 10 - (i % 2), c)
    return frame(draw)


def done(i):
    """Spunta verde e braccia al cielo."""
    c = STATUS_COLOR[DONE]

    def draw(s):
        top = body(s, lift=i, arms="up" if i else "down", eyes="happy", mouth="grin")
        stamp(s, CHECK, 12, top - 8, c)
        if i:
            stamp(s, SPARK, 3, top - 7, c)
            stamp(s, SPARK, 26, top - 5, c)
    return frame(draw)


def idle(i):
    """Seduto a dormire, le Z salgono."""
    c = STATUS_COLOR[IDLE]

    def draw(s):
        top = body(s, eyes="closed", mouth="flat", color=BODY_IDLE, sit=True)
        stamp(s, Z_SMALL, 18, top - 4 - i, c)
        if i >= 1:
            stamp(s, Z_BIG, 21, top - 10 - i, c)
    return frame(draw)


FRAMES = {
    WORKING: [working(i) for i in range(4)],
    WAITING: [waiting(i) for i in range(4)],
    DONE: [done(i) for i in range(2)],
    IDLE: [idle(i) for i in range(3)],
}
# working-<gruppo>_<n>.png: usati quando la sessione sta usando quel tool
FRAMES.update({f"{WORKING}-{g}": [working_tool(g, i) for i in range(4)] for g in TOOL_PROPS})


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    for state, frames in FRAMES.items():
        for i, surf in enumerate(frames):
            pygame.image.save(surf, str(OUT / f"{state}_{i}.png"))
    print(f"Sprite scritti in {OUT}")


if __name__ == "__main__":
    main()
