"""
Genera in sprites/ la mascotte in stile Claude Code (pixel art 32x32, animata).

    python make_sprites.py

Render.Mascot carica da sola sprites/<nome>_<n>.png al prossimo avvio
del monitor. Per tornare al robottino basta cancellare la cartella sprites/.

32x32 perché è la dimensione nativa della mascotte su LED e Pixoo (1:1)
e sul TFT diventa 96x96 (x3): niente pixel deformati.

File generati:
    working_N / waiting_N / done_N / idle_N   uno per stato
    working-<gruppo>_N                        costume per gruppo di tool
                                              (gruppi: TOOL_GROUPS in render.py;
                                              "think" = ha il prompt ma nessun tool)
    error_N                                   tool fallito (qualche secondo)
    wake_N                                    sessione appena aperta
    idle-<scena>_N                            scene a rotazione in pausa

Il corpo resta arancione; ciò che è arancio vivo/giallo/verde/grigio è il colore
dello stato. Idee prese da clawd-actor (costumi) e clawd-on-desk (stati),
ridisegnate da zero.
"""

from pathlib import Path

import pygame

from render import MASCOT_BODY as BODY
from render import MASCOT_BODY_IDLE as BODY_IDLE
from render import PAUSE_SCENES, STATUS_COLOR
from state import DONE, IDLE, WAITING, WORKING

OUT = Path(__file__).resolve().parent.parent / "sprites"

SHADOW = (58, 50, 54)       # ombra a terra
EYE = (24, 22, 22)
MOUTH = (245, 236, 225)
INK = (24, 22, 22)
ERROR = (235, 70, 70)

# Colori extra per i costumi (lettere usate nelle ASCII art)
PAL = {
    "k": INK,
    "w": MOUTH,
    "n": (125, 88, 60),      # marrone cappello detective
    "r": (205, 50, 60),      # rosso basco / naso clown
    "t": (196, 150, 90),     # cuoio cappello cowboy / legno
    "p": (125, 75, 205),     # viola mago
    "y": (250, 210, 70),     # giallo stelle / palline
    "g": (90, 210, 120),     # verde
    "m": (245, 120, 180),    # rosa
    "c": (225, 230, 240),    # nuvola / bianco
    "b": (110, 70, 40),      # caffè / dorso del libro
    "h": (95, 75, 150),      # cuffie
}


def stamp(surf, art, x, y, color):
    """ASCII art: # = colore dato, lettere = PAL, . = trasparente."""
    for dy, line in enumerate(art):
        for dx, ch in enumerate(line):
            col = color if ch == "#" else PAL.get(ch)
            if col:
                surf.set_at((x + dx, y + dy), col)


def rect(surf, x, y, w, h, color):
    pygame.draw.rect(surf, color, (x, y, w, h))


def body(surf, lift=0, arms="down", legs=0, eyes="open", mouth="smile",
         color=BODY, sit=False, dx=0):
    """
    Corpo 14x8 con braccia, gambe e faccia. Restituisce la riga della testa.
    lift: saltello di N pixel. legs: 0/1 fase della camminata. dx: scossa laterale.
    arms: down | up | left_up | right_up. sit: niente gambe, corpo più basso.
    """
    y0 = 16 - lift + (2 if sit else 0)
    x0 = 9 + dx
    # Ombra a terra (non sale col saltello, si stringe quando è in aria)
    shrink = min(lift, 2)
    rect(surf, 11 + dx + shrink, 26 if sit else 27, 10 - 2 * shrink, 1, SHADOW)
    rect(surf, x0, y0, 14, 8, color)
    if arms in ("up", "left_up"):
        rect(surf, x0 - 2, y0 - 4, 2, 6, color)
    else:
        rect(surf, x0 - 2, y0 + 3, 2, 2, color)
    if arms in ("up", "right_up"):
        rect(surf, x0 + 14, y0 - 4, 2, 6, color)
    else:
        rect(surf, x0 + 14, y0 + 3, 2, 2, color)
    if not sit:
        for lx in ((1, 3, 10, 12) if legs == 0 else (2, 4, 9, 11)):
            rect(surf, x0 + lx, y0 + 8, 1, 3, color)
    # Occhi
    ey = y0 + 2
    if eyes in ("open", "left", "right", "up"):
        shift = {"open": 0, "left": -1, "right": 1, "up": 0}[eyes]
        for ex in (3, 10):
            rect(surf, x0 + ex + shift, ey - (1 if eyes == "up" else 0), 1, 2, EYE)
    elif eyes == "focus":  # sopracciglio inclinato: concentrato
        for ex, bx in ((3, 2), (10, 11)):
            rect(surf, x0 + ex, ey + 1, 1, 1, EYE)
            rect(surf, x0 + bx, ey, 1, 1, EYE)
    elif eyes == "happy":  # ^ ^
        for ex in (3, 10):
            surf.set_at((x0 + ex, ey), EYE)
            surf.set_at((x0 + ex - 1, ey + 1), EYE)
            surf.set_at((x0 + ex + 1, ey + 1), EYE)
    elif eyes == "wink":  # occhio sinistro aperto, destro chiuso
        rect(surf, x0 + 3, ey, 1, 2, EYE)
        rect(surf, x0 + 9, ey + 1, 3, 1, EYE)
    elif eyes == "closed":
        for ex in (2, 9):
            rect(surf, x0 + ex, ey + 1, 3, 1, EYE)
    elif eyes == "x":  # x x
        for ex in (2, 9):
            for d in range(3):
                surf.set_at((x0 + ex + d, ey - 1 + d), EYE)
                surf.set_at((x0 + ex + 2 - d, ey - 1 + d), EYE)
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
    elif mouth == "wavy":
        for k in range(5):
            surf.set_at((x0 + 5 + k, my + k % 2), MOUTH)
    return y0


def frame(draw):
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    draw(surf)
    return surf


# --- Oggetti ----------------------------------------------------------------
BOLT = ["..##", ".##.", "####", ".##.", "##..", "#..."]
SPARK = [".#.", "###", ".#."]
BUBBLE_Q = [
    ".#######.", "###kk####", "#####k###", "####k####",
    "#########", "####k####", ".#######.", "..#......",
]
CHECK = ["......##", ".....##.", "##..##..", ".####...", "..##...."]
Z_BIG = ["#####", "...#.", "..#..", ".#...", "#####"]
Z_SMALL = ["####", "..#.", ".#..", "####"]
TERMINAL = [
    ["#########", "#kkkkkkk#", "#k#kkkkk#", "#kk#kkkk#", "#k#k###k#", "#kkkkkkk#", "#########"],
    ["#########", "#kkkkkkk#", "#k#kkkkk#", "#kk#kkkk#", "#k#kkkkk#", "#kkkkkkk#", "#########"],
]
THOUGHT = [
    "..ccccccc..",
    ".ccccccccc.",
    "ccccccccccc",
    "ccccccccccc",
    ".ccccccccc.",
    "..ccccccc..",
]
CLOUD = ["....ccc....", "..ccccccc..", ".ccccccccc.", "ccccccccccc"]
FEDORA = ["...nnnnnn...", "..nnnnnnnn..", "..kkkkkkkk..", "nnnnnnnnnnnn"]
LENS = [".###.", "#...#", "#...#", "#...#", ".###."]
BERET = ["....rr...", ".rrrrrrr.", "rrrrrrrrr"]
PALETTE = [".tttt.", "tr#ytt", "ttgtt.", ".ttt.."]
COWBOY = ["....tttttt....", "....tttttt....", "t...kkkkkk...t", ".tttttttttttt."]
WIZARD = [
    "......p...", ".....pp...", ".....ppp..", "....pppp..",
    "....ppypp.", "...pppppp.", "..ppppppp.", "pppppppppp",
]


# --- Stati ------------------------------------------------------------------
def working(i):
    """Tool generico: cammina concentrato, fulmini che lampeggiano."""
    c = STATUS_COLOR[WORKING]

    def draw(s):
        top = body(s, lift=i % 2, legs=i % 2, eyes="focus")
        stamp(s, BOLT, 10 if i < 2 else 18, top - 8, c)
        stamp(s, SPARK, 4 if i < 2 else 25, top - 6 + i % 2, c)
    return frame(draw)


def think(i):
    """Prompt ricevuto, ancora nessun tool: nuvoletta che si riempie di puntini."""
    c = STATUS_COLOR[WORKING]

    def draw(s):
        top = body(s, eyes="up" if i < 3 else "right", mouth="flat")
        stamp(s, THOUGHT, 14, top - 12, c)
        s.set_at((13, top - 4), PAL["c"])
        rect(s, 14, top - 6, 2, 1, PAL["c"])
        for k in range(i):  # 0..3 puntini
            rect(s, 16 + 3 * k, top - 10, 2, 2, c)
    return frame(draw)


def costume(group, i):
    """Costume per gruppo di tool (cammina sul posto, oggetto animato)."""
    c = STATUS_COLOR[WORKING]

    def draw(s):
        bob = i % 2
        if group == "bash":
            top = body(s, lift=bob, legs=bob, eyes="focus")
            stamp(s, TERMINAL[(i // 2) % 2], 12, top - 9 + bob, c)

        elif group == "read":  # detective: fedora e lente che si muove
            top = body(s, lift=bob, legs=bob, eyes="right" if i < 2 else "focus")
            stamp(s, FEDORA, 10, top - 4, c)
            ly = top - 3 + (i % 4 > 1)
            stamp(s, LENS, 26, ly, c)
            s.set_at((25, top + 3), c)       # manico verso la mano

        elif group == "edit":  # pittore: basco, tavolozza, pennello
            top = body(s, lift=bob, legs=bob, eyes="focus", mouth="o")
            stamp(s, BERET, 11 if i < 2 else 12, top - 3, c)
            stamp(s, PALETTE, 1, top + 1, c)
            tip = (28, top - 3) if i % 2 else (27, top - 1)
            pygame.draw.line(s, PAL["t"], (25, top + 3), tip)
            rect(s, tip[0], tip[1] - 1, 2, 2, c)

        elif group == "agent":  # cowboy col lazo: manda gli agenti
            top = body(s, lift=bob, legs=bob, arms="right_up", eyes="focus", mouth="grin")
            stamp(s, COWBOY, 9, top - 4, c)
            loop = [".###.", "#...#", ".###."] if i % 2 else ["..#..", ".#.#.", "#...#", ".###."]
            stamp(s, loop, 25, top - 10, c)

        elif group == "mcp":  # mago: cappello a punta e bacchetta
            top = body(s, lift=bob, legs=bob, eyes="focus")
            stamp(s, WIZARD, 11, top - 7, c)
            pygame.draw.line(s, PAL["t"], (25, top + 3), (28, top))
            stamp(s, SPARK if i % 2 else ["#.#", ".#.", "#.#"], 28, top - 3, c)

        elif group == "todo":  # clown giocoliere: naso rosso e palline
            top = body(s, arms="left_up" if i % 2 else "right_up", eyes="happy", mouth="grin")
            rect(s, 15, top + 4, 2, 1, PAL["r"])
            arc = [(7, top - 6), (11, top - 9), (16, top - 10), (21, top - 9), (25, top - 6), (16, top - 6)]
            for k, col in enumerate((c, PAL["y"], PAL["m"])):
                x, y = arc[(i + 2 * k) % 6]
                rect(s, x, y, 2, 2, col)

        elif group == "web":  # meteo: nuvola con la pioggia
            top = body(s, eyes="up", mouth="o")
            stamp(s, CLOUD, 10, top - 12, c)
            for k, x in enumerate((12, 15, 18, 21)):
                y = top - 7 + (i + 2 * k) % 4
                rect(s, x, y, 1, 2, c)
    return frame(draw)


def waiting(i):
    """Fumetto col punto di domanda e saluto alternato: ti sta aspettando."""
    c = STATUS_COLOR[WAITING]

    def draw(s):
        arms = ("left_up", "down", "right_up", "down")[i]
        top = body(s, arms=arms, eyes="left" if i < 2 else "open", mouth="o")
        stamp(s, BUBBLE_Q, 12, top - 10 - (i % 2), c)
    return frame(draw)


def done_walk(i, facing):
    """Finito, dopo aver festeggiato: passeggia con la spunta sopra la testa.
    Due versioni (destra/sinistra) invece di specchiare, così la spunta resta dritta."""
    c = STATUS_COLOR[DONE]

    def draw(s):
        top = body(s, lift=i % 2, legs=i % 2, eyes=facing, mouth="smile")
        stamp(s, CHECK, 12, top - 10, c)
    return frame(draw)


def done(i):
    """Festeggia, poi si guarda intorno e sbatte le palpebre."""
    c = STATUS_COLOR[DONE]
    pose = [
        dict(eyes="happy", mouth="grin"),
        dict(lift=1, arms="up", eyes="happy", mouth="grin"),
        dict(eyes="open"),
        dict(eyes="left"),
        dict(eyes="right"),
        dict(eyes="closed"),   # battito di palpebre
    ][i]

    def draw(s):
        top = body(s, **pose)
        stamp(s, CHECK, 12, top - 10, c)
        if i == 1:
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


def error(i):
    """Tool fallito: scossa, occhi a X, X rossa sopra la testa."""
    def draw(s):
        top = body(s, dx=(-1, 1, -1, 0)[i], eyes="x", mouth="wavy")
        if i != 3:
            for d in range(5):
                s.set_at((14 + d, top - 8 + d), ERROR)
                s.set_at((18 - d, top - 8 + d), ERROR)
                s.set_at((15 + d, top - 8 + d), ERROR)
                s.set_at((19 - d, top - 8 + d), ERROR)
    return frame(draw)


def wake(i):
    """Sessione appena aperta: doppio salto con il punto esclamativo."""
    pose = [
        dict(sit=True, eyes="closed", mouth="flat"),
        dict(lift=4, arms="up", eyes="open", mouth="o"),
        dict(eyes="open", mouth="smile"),
        dict(lift=3, arms="up", eyes="happy", mouth="grin"),
    ][i]

    def draw(s):
        top = body(s, **pose)
        if i in (1, 3):
            stamp(s, ["w", "w", "w", ".", "w"], 16, top - 7, None)
    return frame(draw)


NOTE = ["..##", "..#.", "..#.", "###.", "##.."]


def pause_scene(scene, i):
    """Scene a rotazione in PAUSA (prima di addormentarsi)."""
    c = STATUS_COLOR[IDLE]

    def draw(s):
        if scene == "coffee":  # tazza fumante
            top = body(s, color=BODY_IDLE, eyes="happy" if i >= 2 else "open")
            stamp(s, ["cbbc.", "cccc#", "cccc#", "cccc."], 25, top + 1, c)
            s.set_at((26, top - 1 - i % 2), c)
            s.set_at((27, top - 3 + i % 2), c)
        elif scene == "music":  # cuffie e note, dondola
            dx = (-1, 0, 1, 0)[i]
            top = body(s, color=BODY_IDLE, dx=dx, eyes="closed", mouth="smile")
            x0 = 9 + dx
            rect(s, x0 + 1, top - 3, 12, 1, PAL["h"])
            s.set_at((x0, top - 2), PAL["h"])
            s.set_at((x0 + 13, top - 2), PAL["h"])
            rect(s, x0 - 1, top + 1, 2, 3, PAL["h"])
            rect(s, x0 + 13, top + 1, 2, 3, PAL["h"])
            stamp(s, NOTE, 25 if i < 2 else 2, top - 9 + i % 2, c)
        elif scene == "book":  # seduto a leggere
            top = body(s, color=BODY_IDLE, sit=True, eyes="right", mouth="flat")
            # Libro rosso tenuto in mano di lato, con il titolo
            cover = ["rrrrrr", "rwwwwr", "rrrrrr", "rwwwrr", "rrrrrr", "rrrrrr", "rrrrrr"]
            stamp(s, cover, 24, top, c)
            if i == 3:  # gira pagina
                rect(s, 25, top - 1, 4, 1, PAL["c"])
        elif scene == "guitar":  # strimpella
            top = body(s, color=BODY_IDLE, lift=i % 2, eyes="happy", mouth="smile")
            stamp(s, [".ttt.", "ttttt", "ttktt", ".ttt."], 10, top + 4, c)
            pygame.draw.line(s, PAL["b"], (15, top + 5), (24, top + 1))
            rect(s, 24, top - 1, 2, 2, PAL["b"])
            stamp(s, NOTE, 26, top - 8 - i % 2, c)
        elif scene == "wink":  # guarda verso di te e ammicca, con un luccichio
            top = body(s, color=BODY_IDLE, eyes="wink" if i == 2 else "open",
                       mouth="grin" if i == 2 else "smile")
            if i == 2:
                stamp(s, SPARK, 22, top - 3, c)
        elif scene == "walk":  # passeggia verso destra (il monitor lo specchia al ritorno)
            body(s, color=BODY_IDLE, lift=i % 2, legs=i % 2, eyes="right", mouth="smile")
    return frame(draw)



GROUPS = ("bash", "read", "edit", "agent", "mcp", "todo", "web")

FRAMES = {
    WORKING: [working(i) for i in range(4)],
    f"{WORKING}-think": [think(i) for i in range(4)],
    WAITING: [waiting(i) for i in range(4)],
    DONE: [done(i) for i in range(6)],
    IDLE: [idle(i) for i in range(3)],
    "error": [error(i) for i in range(4)],
    "wake": [wake(i) for i in range(4)],
    f"{DONE}-walk": [done_walk(i, "right") for i in range(4)],
    f"{DONE}-walk-left": [done_walk(i, "left") for i in range(4)],
}
FRAMES.update({f"{IDLE}-{sc}": [pause_scene(sc, i) for i in range(4)] for sc in PAUSE_SCENES})
FRAMES.update({f"{WORKING}-{g}": [costume(g, i) for i in range(6 if g == "todo" else 4)] for g in GROUPS})


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    for name, frames in FRAMES.items():
        for i, surf in enumerate(frames):
            pygame.image.save(surf, str(OUT / f"{name}_{i}.png"))
    print(f"Sprite scritti in {OUT}")


if __name__ == "__main__":
    main()
