"""
Renderer dei tre profili di display.

Ogni profilo disegna su una superficie alla risoluzione NATIVA del display
(es. 64x32 pixel). La finestra del simulatore la ingrandisce poi con
scaling "nearest" ed eventualmente l'effetto LED a puntini, così quello
che vedi è fedele a quello che vedresti sul pannello reale.
"""

from __future__ import annotations

import math
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pygame

from state import DONE, IDLE, LABELS, WAITING, WORKING, Session

# --- Palette ---------------------------------------------------------------
BG = (8, 10, 14)
FG = (225, 228, 235)
DIM = (90, 96, 110)
STATUS_COLOR = {
    WORKING: (255, 122, 24),   # arancio
    WAITING: (255, 228, 0),    # giallo: ti aspetta
    DONE: (80, 220, 110),      # verde: finito
    IDLE: (110, 110, 130),     # grigio: in pausa
}

# Colori del corpo della mascotte (servono anche per trovare la testa
# quando si aggiunge il cappello delle feste)
MASCOT_BODY = (217, 119, 87)       # arancio terracotta
MASCOT_BODY_IDLE = (160, 98, 80)   # più spento in pausa

# Pausa: una scena diversa ogni PAUSE_SCENE_S secondi, poi dorme
PAUSE_SCENES = ("wink", "coffee", "walk", "music", "wink", "book", "walk", "guitar")  # passeggiata e occhiolino tornano due volte
WALK_SPEED = 8            # passeggiata: pixel del display al secondo
DONE_CELEBRATE_S = 10     # FINITO: festeggia per 10 s, poi passeggia
PAUSE_SCENE_S = 10
SLEEP_AFTER_S = 40 * 60   # dall'ultimo evento: 10 min "finito" + 30 min di scene

# Zoom al lavoro: dopo ZOOM_AFTER_S di LAVORA la mascotte cresce fino a riempire
# lo schermo di arancio con la faccia al centro (repo in alto, limiti in basso),
# si guarda intorno con calma e resta così finché almeno una sessione smette di
# lavorare; poi torna piccola e, se c'è ancora lavoro, riparte il conto
ZOOM_AFTER_S = 8
ZOOM_GROW_S = 0.6         # ingrandimento (e uguale per la riduzione)
ZOOM_EYES = ("open", "left", "right", "closed", "wink", "happy", "up")  # frame sprites/zoom_<n>.png
# Sguardi disegnati dal renderer con gli occhi che scivolano: indice -> spostamento (x, y) in px dello sprite.
# Gli altri (battito, occhiolino, risata) sono frame disegnati.
ZOOM_GAZE = {0: (0, 0), 1: (-1, 0), 2: (1, 0), 6: (0, -1)}
ZOOM_BODY = (9, 16, 14, 8)  # corpo nello sprite 32x32: x, y, larghezza, altezza
ZOOM_EYE_X, ZOOM_EYE_Y = (12, 19), 18  # occhi 1x2 nello sprite (vedi body() in make_sprites)
ZOOM_EYE = (24, 22, 22)
ZOOM_GLOW = (150, 80, 30)  # luce sommata: alone e bagliore al centro
ZOOM_CENTER_GLOW = 0.3    # forza del bagliore al centro quando è grande (0..1; l'alone resta pieno)
ZOOM_BREATH_S = 2.0        # periodo del respiro mentre è grande
ZOOM_GLIDE_S = 0.35        # tempo per far scivolare gli occhi da un lato all'altro
ZOOM_FACE = (0.5, 0.42)    # faccia (11x4 px dello sprite) al massimo: metà larghezza, 42% altezza
ZOOM_TEXT = (110, 45, 20)  # arancio scuro di repo e limiti sullo sfondo arancio

# --- Profili: risoluzione nativa e resa a LED ------------------------------
PROFILES = {
    "tft":   {"size": (320, 240), "led": False, "scale": 2, "name": "TFT 2.8\" 320x240"},
    "led":   {"size": (64, 32),   "led": True,  "scale": 12, "name": "Matrice LED 64x32"},
    "pixoo": {"size": (64, 64),   "led": True,  "scale": 10, "name": "Pixoo 64x64"},
}


# ===========================================================================
# Font bitmap 3x5 per i display a bassa risoluzione
# ===========================================================================
# Ogni glifo: 5 righe da 3 colonne separate da '|' ('#' = pixel acceso)
_GLYPHS = {
    "A": ".#.|#.#|###|#.#|#.#", "B": "##.|#.#|##.|#.#|##.", "C": ".##|#..|#..|#..|.##",
    "D": "##.|#.#|#.#|#.#|##.", "E": "###|#..|##.|#..|###", "F": "###|#..|##.|#..|#..",
    "G": ".##|#..|#.#|#.#|.##", "H": "#.#|#.#|###|#.#|#.#", "I": "###|.#.|.#.|.#.|###",
    "J": "..#|..#|..#|#.#|.#.", "K": "#.#|#.#|##.|#.#|#.#", "L": "#..|#..|#..|#..|###",
    "M": "#.#|###|###|#.#|#.#", "N": "##.|#.#|#.#|#.#|#.#", "O": ".#.|#.#|#.#|#.#|.#.",
    "P": "##.|#.#|##.|#..|#..", "Q": ".#.|#.#|#.#|##.|.##", "R": "##.|#.#|##.|#.#|#.#",
    "S": ".##|#..|.#.|..#|##.", "T": "###|.#.|.#.|.#.|.#.", "U": "#.#|#.#|#.#|#.#|###",
    "V": "#.#|#.#|#.#|#.#|.#.", "W": "#.#|#.#|###|###|#.#", "X": "#.#|#.#|.#.|#.#|#.#",
    "Y": "#.#|#.#|.#.|.#.|.#.", "Z": "###|..#|.#.|#..|###", "0": "###|#.#|#.#|#.#|###",
    "1": ".#.|##.|.#.|.#.|###", "2": "##.|..#|.#.|#..|###", "3": "##.|..#|.#.|..#|##.",
    "4": "#.#|#.#|###|..#|..#", "5": "###|#..|##.|..#|##.", "6": ".##|#..|###|#.#|###",
    "7": "###|..#|.#.|.#.|.#.", "8": "###|#.#|###|#.#|###", "9": "###|#.#|###|..#|##.",
    "+": "...|.#.|###|.#.|...", "/": "..#|..#|.#.|#..|#..", "-": "...|...|###|...|...",
    "%": "#.#|..#|.#.|#..|#.#", ":": "...|.#.|...|.#.|...",
    "?": "##.|..#|.#.|...|.#.", ".": "...|...|...|...|.#.", " ": "...|...|...|...|...",
}

def _glyph(ch: str) -> list[str]:
    """Restituisce il glifo 3x5 come 5 righe da 3 caratteri."""
    return _GLYPHS.get(ch.upper(), _GLYPHS["?"]).split("|")


def tiny_text(surf: pygame.Surface, text: str, x: int, y: int, color) -> int:
    """Scrive testo con il font 3x5. Restituisce la x finale."""
    for ch in text:
        for row, line in enumerate(_glyph(ch)):
            for col, px in enumerate(line):
                if px == "#":
                    surf.set_at((x + col, y + row), color)
        x += 4  # 3 px di glifo + 1 di spazio
    return x


def tiny_width(text: str) -> int:
    return max(0, len(text) * 4 - 1)


def short_name(project: str, n: int) -> str:
    """Abbreviazione del progetto per i display piccoli (solo lettere/cifre)."""
    clean = "".join(c for c in project.upper() if c.isalnum())
    return (clean or "?")[:n]


# ===========================================================================
# Mascotte segnaposto (personaggio originale: un robottino con schermo-faccia)
# ===========================================================================
# Legenda: . trasparente, O contorno, b corpo, S schermo, a antenna, L luce
_BODY = [
    ".......LL.......",
    ".......aa.......",
    "..OOOOOOOOOOOO..",
    ".ObbbbbbbbbbbbO.",
    ".ObSSSSSSSSSSbO.",
    ".ObSSSSSSSSSSbO.",
    ".ObSSSSSSSSSSbO.",
    ".ObSSSSSSSSSSbO.",
    ".ObSSSSSSSSSSbO.",
    ".ObbbbbbbbbbbbO.",
    "..OOOOOOOOOOOO..",
    "....ObbbbbbO....",
    "...ObbbbbbbbO...",
    "..O.ObbbbbbO.O..",
    "....OO....OO....",
    "....OO....OO....",
]
# Facce 10x5 disegnate sullo schermo (righe 4-8, colonne 3-12).
# E = occhi, M = bocca. Due frame per stato per l'animazione.
_FACES = {
    WORKING: [
        ["..........", ".EE....EE.", ".EE....EE.", "..........", "...MMMM..."],
        ["..........", "EE....EE..", "EE....EE..", "..........", "...MMMM..."],
    ],
    WAITING: [
        ["..........", ".EE....EE.", ".EE....EE.", "..........", "....MM...."],
        ["..........", "..........", ".EE....EE.", "..........", "....MM...."],
    ],
    DONE: [
        ["..........", "..E....E..", ".E.E..E.E.", "..M....M..", "...MMMM..."],
        ["..........", "..E....E..", ".E.E..E.E.", "..M....M..", "...MMMM..."],
    ],
    IDLE: [
        ["..........", "..........", ".EEE..EEE.", "..........", "....MM...."],
        ["..........", "..........", ".EEE..EEE.", "..........", "....MM...."],
    ],
}
# Velocità dell'animazione (frame al secondo) per stato
_FPS = {WORKING: 4, WAITING: 2, DONE: 1, IDLE: 0.5, "error": 6, "wake": 6,
        "idle-coffee": 2, "idle-music": 2, "idle-book": 1, "idle-guitar": 3, "idle-wink": 2,"idle-walk": 4, "done-walk": 4, "done-walk-left": 4}


def _build_frame(state: str, frame: int) -> pygame.Surface:
    """Costruisce un frame 16x16 della mascotte per lo stato dato."""
    col = STATUS_COLOR[state]
    screen = tuple(int(c * 0.22) for c in col)          # schermo scuro tinto
    blink_off = state in (WAITING, IDLE) and frame == 1  # luce antenna lampeggia
    palette = {
        "O": (60, 66, 80),
        "a": (60, 66, 80),
        "b": (200, 205, 215),
        "S": screen,
        "L": tuple(int(c * 0.35) for c in col) if blink_off else col,
    }
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    for y, line in enumerate(_BODY):
        for x, ch in enumerate(line):
            if ch in palette:
                surf.set_at((x, y), palette[ch])
    for y, line in enumerate(_FACES[state][frame]):
        for x, ch in enumerate(line):
            if ch in "EM":
                surf.set_at((x + 3, y + 4), col)
    return surf


# Tool di Claude Code -> oggetto disegnato sopra la mascotte mentre lavora.
# I tool non elencati (Skill, ToolSearch, ...) usano i fulmini di default.
TOOL_GROUPS = {
    "Bash": "bash", "PowerShell": "bash", "BashOutput": "bash", "background": "bash",
    "Read": "read", "Grep": "read", "Glob": "read", "LS": "read",
    "Edit": "edit", "MultiEdit": "edit", "Write": "edit", "NotebookEdit": "edit",
    "WebFetch": "web", "WebSearch": "web",
    "TodoWrite": "todo", "TaskCreate": "todo", "TaskUpdate": "todo",
    "Agent": "agent", "Task": "agent",
}


def tool_group(tool: str) -> str:
    if tool.startswith("mcp__"):
        return "mcp"
    return TOOL_GROUPS.get(tool, "")


# Icone 5x5 del tipo di lavoro, accanto al nome della sessione durante lo zoom
_ZOOM_ICONS = {
    "bash":  ["#....", ".#...", "..#..", ".#...", "#.###"],  # prompt >_
    "read":  [".##..", "#..#.", "#..#.", ".##..", "...##"],  # lente
    "edit":  ["...##", "..###", ".###.", "###..", "##..."],  # matita
    "web":   [".###.", "#.#.#", "#####", "#.#.#", ".###."],  # globo
    "todo":  ["#.###", ".....", "#.###", ".....", "#.###"],  # lista
    "agent": ["#...#", ".#.#.", "..#..", "..#..", "..#.."],  # bivio: sotto-agente
    "mcp":   [".#.#.", ".#.#.", "#####", ".###.", "..#.."],  # spina
    "think": [".###.", "#####", ".###.", ".....", "#...."],  # nuvoletta
    "":      ["...#.", "..#..", ".####", "..#..", ".#..."],  # fulmine: altri tool
}


def _draw_icon(surf: pygame.Surface, icon: list[str], x: int, y: int, k: int) -> None:
    """Icona 5x5 con pixel da k x k, nel colore del testo dello zoom."""
    for dy, line in enumerate(icon):
        for dx, ch in enumerate(line):
            if ch == "#":
                surf.fill(ZOOM_TEXT, (x + dx * k, y + dy * k, k, k))


# Mini-mascotte 10x5: stesse proporzioni della grande (corpo largo, braccia
# in basso, due paia di gambe). # = colore di stato, k = occhi.
_MINI = [
    ".########.",
    ".#k####k#.",
    ".########.",
    "##########",
    ".#.#..#.#.",
]
# Posti liberi nel 32x32: in basso a sx, in basso a dx, in alto a sx
_MINI_SPOTS = [(0, 27), (22, 27), (0, 1)]


def _draw_minis(img: pygame.Surface, colors: list, t: float) -> None:
    """Una mini-mascotte per sessione, del suo colore di stato, che saltellano sfasate."""
    for n, (col, (x, y)) in enumerate(zip(colors, _MINI_SPOTS)):
        y -= int(t * 3 + n) % 2
        for dy, line in enumerate(_MINI):
            for dx, ch in enumerate(line):
                if ch != ".":
                    img.set_at((x + dx, y + dy), col if ch == "#" else (24, 22, 22))


# --- Feste: cappello sulla testa + particelle sullo sfondo ------------------
# Si attivano da sole in base alla data; CLAUDE_MONITOR_FESTA=<nome>|off forza.
_HAT_COSTUMES = {"working-read", "working-edit", "working-agent", "working-mcp", "idle-music"}
_HOLI = {
    "r": (205, 50, 60), "w": (240, 240, 245), "y": (250, 210, 70), "m": (245, 120, 180),
    "p": (125, 75, 205), "g": (90, 200, 110),
}
_HATS = {  # ultima riga = tesa, appoggiata sulla prima riga del corpo
    "christmas": ["..........ww", ".......rrrw.", "....rrrrrr..", "..rrrrrrrr..", "wwwwwwwwwwww"],
    "newyear":   ["......w.....", ".....ym.....", "....ymym....", "...ymymym...", "..ymymymym.."],
    "halloween": [".....pp.....", "....pppp....", "...pppppp...", "...gggggg...", "pppppppppppp"],
}


def holiday_for(d) -> str:
    """Festa del giorno (date), "" se nessuna."""
    md = (d.month, d.day)
    if (12, 1) <= md <= (12, 30):
        return "christmas"
    if md == (12, 31) or md <= (1, 2):
        return "newyear"
    if (10, 25) <= md <= (11, 1):
        return "halloween"
    if (2, 13) <= md <= (2, 15):
        return "valentine"
    return ""


def _head_top(img: pygame.Surface) -> int | None:
    """Prima riga del corpo (testa) nel frame 32x32, cercando il colore del corpo."""
    for y in range(32):
        for x in (13, 18):
            if tuple(img.get_at((x, y)))[:3] in (MASCOT_BODY, MASCOT_BODY_IDLE):
                return y
    return None


def _draw_holiday(img: pygame.Surface, holiday: str, t: float, hat: bool) -> None:
    art = _HATS.get(holiday) if hat else None
    top = _head_top(img) if art else None
    if top is not None:
        y0 = top - len(art) + 1
        # Niente cappello se sopra la testa c'è già un oggetto (fumetto, terminale...)
        if any(img.get_at((10 + dx, y)).a for y in range(max(0, y0), top) for dx in range(12)):
            top = None

    def free(x, y):  # le particelle passano dietro la mascotte
        return 0 <= x < 32 and 0 <= y < 32 and img.get_at((x, y)).a == 0

    for k in range(7):
        x = (k * 11 + 3) % 32
        if holiday == "christmas":    # neve che scende
            y = int(t * 4 + k * 9) % 32
            if free(x, y):
                img.set_at((x, y), _HOLI["w"])
        elif holiday == "valentine":  # cuori che salgono
            y = 31 - int(t * 3 + k * 9) % 32
            for dx, dy in ((0, 0), (2, 0), (0, 1), (1, 1), (2, 1), (1, 2)):
                if free(x + dx, y + dy):
                    img.set_at((x + dx, y + dy), _HOLI["m"] if k % 2 else _HOLI["r"])
        elif holiday == "newyear" and k < 3:  # fuochi d'artificio che si aprono
            cx, cy = ((5, 6), (26, 4), (27, 14))[k]
            r = (int(t * 4) + k) % 4
            col = (_HOLI["y"], _HOLI["m"], _HOLI["g"])[k]
            for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r), (r, r), (-r, -r), (r, -r), (-r, r)):
                if r and free(cx + dx, cy + dy):
                    img.set_at((cx + dx, cy + dy), col)
        elif holiday == "halloween" and k < 2:  # fantasmini che fluttuano
            gx, gy = ((2, 8), (26, 3))[k]
            gy += int(t * 2 + k) % 2
            for dx, dy in ((1, 0), (0, 1), (1, 1), (2, 1), (0, 2), (2, 2)):
                if free(gx + dx, gy + dy):
                    img.set_at((gx + dx, gy + dy), _HOLI["w"])
    if top is not None:
        for dy, line in enumerate(art):
            for dx, ch in enumerate(line):
                if ch != "." and 0 <= y0 + dy < 32:
                    img.set_at((10 + dx, y0 + dy), _HOLI[ch])


# Sequenza degli occhi durante lo zoom: (indice in ZOOM_EYES, secondi), ripetuta
# finché dura. Destra e sinistra scivolando, battito, di nuovo destra e
# sinistra, occhiolino, risata, da capo.
ZOOM_PLAN = [
    (0, 1.2), (2, 1.0), (1, 1.0),             # guarda a destra e a sinistra
    (6, 1.0), (0, 0.8),                       # in su
    (3, 0.15), (0, 0.8),                      # battito
    (2, 1.0), (1, 1.0), (0, 0.8),             # di nuovo destra e sinistra
    (4, 0.7), (0, 0.5),                       # occhiolino
    (5, 1.2), (0, 0.8),                       # risata
]


def _eyes_at(plan, t: float) -> tuple[int, tuple[float, float]]:
    """Frame degli occhi e spostamento (x, y in px dello sprite, scivolato) al tempo t della sequenza."""
    prev = (0.0, 0.0)
    for eyes, d in plan:
        target = ZOOM_GAZE.get(eyes, prev)
        if t < d:
            g = min(1.0, t / ZOOM_GLIDE_S)
            g = g * g * (3 - 2 * g)
            return eyes, (prev[0] + (target[0] - prev[0]) * g, prev[1] + (target[1] - prev[1]) * g)
        t -= d
        prev = target
    return 0, (0.0, 0.0)


def _ease_out_back(x: float) -> float:
    """0..1 con un piccolo sorpasso finale (circa +10%): effetto rimbalzo."""
    return 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2


_RADIAL: pygame.Surface | None = None


def _radial() -> pygame.Surface:
    """Bagliore radiale 32x32 (centro acceso, bordi spenti), da scalare morbido."""
    global _RADIAL
    if _RADIAL is None:
        _RADIAL = pygame.Surface((32, 32))
        for y in range(32):
            for x in range(32):
                v = max(0.0, 1 - math.hypot(x - 15.5, y - 15.5) / 16) ** 2
                _RADIAL.set_at((x, y), tuple(round(c * v) for c in ZOOM_GLOW))
    return _RADIAL


class Mascot:
    """
    Gestisce i frame della mascotte.

    Se nella cartella sprites/ trovi file come working_0.png, working_1.png,
    waiting_0.png, ... vengono usati al posto del robottino segnaposto
    (qualsiasi dimensione: vengono scalati senza sfocatura).
    """

    def __init__(self, sprite_dir: Path | None = None) -> None:
        # Carica tutti i gruppi <nome>_<n>.png (stati, costumi, scene, ...)
        self.frames: dict[str, list[pygame.Surface]] = {}
        groups: dict[str, list] = {}
        for f in sprite_dir.glob("*_*.png") if sprite_dir and sprite_dir.is_dir() else []:
            name, _, idx = f.stem.rpartition("_")
            if idx.isdigit():
                groups.setdefault(name, []).append((int(idx), f))
        for name, items in groups.items():
            self.frames[name] = [pygame.image.load(str(f)) for _, f in sorted(items)]
        # Stati senza sprite: robottino segnaposto
        for state in STATUS_COLOR:
            self.frames.setdefault(state, [_build_frame(state, i) for i in range(2)])

    def get(self, state: str, t: float, size: int, variant: str = "",
            minis: list = (), holiday: str = "") -> pygame.Surface:
        """
        Frame corrente, scalato (nearest) a un quadrato di lato `size`.
        variant: animazione specifica (costume, errore, scena di pausa...),
        usata se esiste, altrimenti quella dello stato. minis: colori delle
        mini-mascotte (altre sessioni). holiday: festa da sovrapporre.
        """
        key = variant if variant in self.frames else state
        frames = self.frames[key]
        img = frames[int(t * _FPS.get(key, _FPS[state])) % len(frames)]
        if (minis or holiday) and img.get_size() == (32, 32):
            img = img.copy()
            if holiday:
                _draw_holiday(img, holiday, t, hat=key not in _HAT_COSTUMES)
            if minis:
                _draw_minis(img, minis, t)
        # Mantiene le proporzioni dentro il quadrato
        w, h = img.get_size()
        k = size / max(w, h)
        return pygame.transform.scale(img, (max(1, int(w * k)), max(1, int(h * k))))


# ===========================================================================
# Elementi comuni
# ===========================================================================
def progress_bar(surf, rect: pygame.Rect, s: Session, t: float, border: bool) -> None:
    """
    Barra di avanzamento di una sessione:
    - con todo list: riempimento proporzionale (completati/totale);
    - senza todo list e al lavoro: segmento che scorre (indeterminata);
    - in attesa: barra gialla lampeggiante.
    """
    col = STATUS_COLOR[s.status]
    track = tuple(int(c * 0.18) for c in col)
    pygame.draw.rect(surf, track, rect)
    done, total = s.progress
    inner = rect.inflate(-2, -2) if border else rect

    if s.status == WAITING and int(t * 2) % 2 == 0:
        pygame.draw.rect(surf, col, inner)
    elif total:
        w = round(inner.width * done / total)
        if w:
            pygame.draw.rect(surf, col, (inner.x, inner.y, w, inner.height))
    elif s.status == WORKING:
        seg = max(2, inner.width // 4)
        pos = int((t * 0.6 % 1.0) * (inner.width + seg)) - seg
        x0, x1 = max(inner.x, inner.x + pos), min(inner.right, inner.x + pos + seg)
        if x1 > x0:
            pygame.draw.rect(surf, col, (x0, inner.y, x1 - x0, inner.height))
    if border:
        pygame.draw.rect(surf, tuple(int(c * 0.5) for c in col), rect, 1)


# ===========================================================================
# Limiti d'uso (sessione 5h, settimana)
# ===========================================================================
LIMIT_LABELS = {"five_hour": "5h", "seven_day": "7g"}
LIMIT_WINDOW_S = {"five_hour": 5 * 3600, "seven_day": 7 * 86400}


def limit_rows(limits: list[dict]) -> list[tuple[str, float, str, float | None]]:
    """
    (etichetta, % usata, ora di reset "HH:MM" o "gg/mm", % di finestra trascorsa)
    per 5h e 7g. La % trascorsa è il "ritmo giusto": usare più di così = consumi tanto.
    """
    now = datetime.now().astimezone()
    rows = []
    for kind, label in LIMIT_LABELS.items():
        lim = next((l for l in limits if l.get("kind") == kind), None)
        if lim is None:
            continue
        pct, reset, elapsed = float(lim.get("percentUsed", 0)), "", None
        try:
            at = datetime.fromisoformat(lim["resetsAt"]).astimezone()
            if at <= now:
                pct = 0.0  # finestra già ripartita, il dato è vecchio
            else:
                left = (at - now).total_seconds() / LIMIT_WINDOW_S[kind]
                elapsed = min(100.0, max(0.0, (1 - left) * 100))
            reset = at.strftime("%H:%M" if at - now < timedelta(days=1) else "%d/%m")
        except (KeyError, TypeError, ValueError):
            pass
        rows.append((label, pct, reset, elapsed))
    return rows


def limit_color(pct: float, elapsed: float | None = None):
    """Con il tempo trascorso: verde se in linea, giallo un po' sopra, rosso molto sopra."""
    over = pct - elapsed if elapsed is not None else pct - 50
    return (80, 220, 110) if over <= 0 else (255, 228, 0) if over <= 15 else (240, 70, 60)


def limit_bar(surf, rect: pygame.Rect, pct: float, elapsed: float | None = None) -> None:
    """Barra di consumo con una tacca bianca dove "dovresti" essere col tempo trascorso."""
    col = limit_color(pct, elapsed)
    pygame.draw.rect(surf, tuple(int(c * 0.18) for c in col), rect)
    w = round(rect.width * min(pct, 100) / 100)
    if w:
        pygame.draw.rect(surf, col, (rect.x, rect.y, w, rect.height))
    if elapsed is not None:
        x = rect.x + min(rect.width - 1, round(rect.width * elapsed / 100))
        pygame.draw.line(surf, FG, (x, rect.y - (rect.height > 1)), (x, rect.bottom - 1 + (rect.height > 1)))


# ===========================================================================
# Profili
# ===========================================================================
class Renderer:
    """Disegna lo stato su una superficie alla risoluzione nativa del profilo."""

    def __init__(self, profile: str, mascot: Mascot) -> None:
        self.profile = profile
        self.size = PROFILES[profile]["size"]
        self.mascot = mascot
        self.surface = pygame.Surface(self.size)
        self.working_since = 0.0   # inizio del LAVORA corrente (0 = non lavora)
        self.zoom_t0 = 0.0         # inizio dello zoom in corso (0 = piccola)
        self.zoom_ids: set[str] = set()  # sessioni al lavoro durante lo zoom
        self.shrink_at = 0.0       # fine dell'ultimo zoom (per l'animazione di ritorno)
        self.sessions: list[Session] = []
        if profile == "tft":
            # pygame.font.Font(None, ...) = font di default, sempre disponibile
            self.font_s = pygame.font.Font(None, 15)
            self.font_m = pygame.font.Font(None, 18)
            self.font_l = pygame.font.Font(None, 22)

    def draw(self, sessions: list[Session], overall: str, t: float, limits=()) -> pygame.Surface:
        self.surface.fill(BG)
        self.limits = limit_rows(list(limits))
        now = time.time()
        # Tool della prima sessione al lavoro ("" = ha il prompt, sta pensando)
        tool = next((s.tool for s in sessions if s.status == WORKING), "")
        # Animazione da mostrare, in ordine di precedenza
        if any(s.error_until > now for s in sessions):
            self.variant = "error"
        elif any(s.wake_until > now for s in sessions):
            self.variant = "wake"
        elif overall == WORKING:
            group = tool_group(tool) if tool else "think"
            self.variant = f"{WORKING}-{group}" if group else ""
        elif overall == DONE:
            # Festeggia appena finito, poi passeggia con la spunta
            last = max(s.updated for s in sessions if s.status == DONE)
            self.variant = f"{DONE}-walk" if now - last > DONE_CELEBRATE_S else ""
        elif overall == IDLE and sessions and now - max(s.updated for s in sessions) < SLEEP_AFTER_S:
            # In pausa da poco: scena a rotazione; poi si addormenta
            self.variant = f"{IDLE}-{PAUSE_SCENES[int(now // PAUSE_SCENE_S) % len(PAUSE_SCENES)]}"
        else:
            self.variant = ""
        # Le altre sessioni attive diventano mini-mascotte (max 3)
        self.minis = [STATUS_COLOR[s.status] for s in sessions[1:] if s.status != IDLE][:3]
        festa = os.environ.get("CLAUDE_MONITOR_FESTA", "")
        self.holiday = "" if festa == "off" else festa or holiday_for(date.today())
        getattr(self, f"_draw_{self.profile}")(sessions, overall, t)
        self.sessions = sessions
        self._zoom_step(sessions, overall, now)
        return self.surface

    def _zoom_step(self, sessions, overall, now) -> None:
        """Avvia, tiene e chiude lo zoom; solo nel lavoro "puro" (niente errore o risveglio)."""
        working = {s.session_id for s in sessions if s.status == WORKING}
        pure = overall == WORKING and self.variant not in ("error", "wake")
        if overall != WORKING:
            self.working_since = 0.0
        elif not self.working_since:
            self.working_since = now
        if self.zoom_t0 and (not pure or self.zoom_ids - working):
            # Almeno una sessione ha smesso di lavorare: torna piccola, riparte il conto
            self.zoom_t0, self.shrink_at = 0.0, now
            self.working_since = now if overall == WORKING else 0.0
        if not self.zoom_t0 and pure and self.working_since and now - self.working_since >= ZOOM_AFTER_S:
            self.zoom_t0, self.zoom_ids = now, set()
        if self.zoom_t0:
            self.zoom_ids |= working  # chi parte durante lo zoom conta anche lui
            p = now - self.zoom_t0
            self._zoom(min(1.0, p / ZOOM_GROW_S), p - ZOOM_GROW_S if p >= ZOOM_GROW_S else None)
        elif now - self.shrink_at < ZOOM_GROW_S:
            self._zoom(1 - (now - self.shrink_at) / ZOOM_GROW_S, None)

    def _zoom(self, k: float, t_look: float | None) -> None:
        """
        Claw'd a grandezza k (0 = al suo posto, 1 = faccia al centro su schermo
        arancio); t_look = secondi da quando è arrivato (None mentre cresce o torna).
        """
        frames = self.mascot.frames.get("zoom")
        if not frames:
            return  # sprite non rigenerati (o robottino segnaposto): niente zoom
        if t_look is not None:
            t_look %= sum(d for _, d in ZOOM_PLAN)  # la sequenza si ripete finché dura
        eyes, shift = _eyes_at(ZOOM_PLAN, t_look) if t_look is not None else (0, (0.0, 0.0))
        # Respiro: sobbalzo lento mentre è grande (niente scala: con lo scaling
        # nearest bocca e occhi cambierebbero di un pixel avanti e indietro)
        breath = math.sin(2 * math.pi * t_look / ZOOM_BREATH_S) if t_look is not None else 0.0
        kp = k * k * (3 - 2 * k)  # posizione: smoothstep, parte e arriva dolce
        ks = _ease_out_back(k)    # scala: supera un po' l'arrivo e rimbalza indietro
        w, h = self.size
        bx, by, bw, bh = ZOOM_BODY
        m = self.mascot_rect
        s0 = m.w / 32
        # Faccia (occhi che guardano di lato: 11x4 px dello sprite) dentro ZOOM_FACE
        # dello schermo, con spazio attorno per repo e limiti; il resto lo copre
        # lo sfondo arancio qui sotto. Scala intera: ogni pixel dello sprite uguale.
        s1 = max(1, round(min(w * ZOOM_FACE[0] / 11, h * ZOOM_FACE[1] / 4)))
        s = s0 + (s1 - s0) * ks
        # Centro del corpo: dalla posizione sul display al centro dello schermo
        c0 = (m.x + (bx + bw / 2) * s0, m.y + (by + bh / 2) * s0)
        cx = c0[0] + (w / 2 - c0[0]) * kp
        cy = c0[1] + (h / 2 - c0[1]) * kp - 0.25 * s * breath
        # Sfondo arancio: dal riquadro del corpo a tutto lo schermo, solo nell'ultimo
        # 40% dello zoom (prima coprirebbe gambe e braccia ancora piccole)
        kb = max(0.0, (kp - 0.6) / 0.4)
        x0, y0 = (cx - bw / 2 * s) * (1 - kb), (cy - bh / 2 * s) * (1 - kb)
        x1, y1 = cx + bw / 2 * s + (w - cx - bw / 2 * s) * kb, cy + bh / 2 * s + (h - cy - bh / 2 * s) * kb
        pygame.draw.rect(self.surface, MASCOT_BODY, (round(x0), round(y0), round(x1 - x0), round(y1 - y0)))
        ox, oy = cx - (bx + bw / 2) * s, cy - (by + bh / 2) * s  # angolo dello sprite
        # Alone attorno alla sagoma mentre cresce e si riduce
        if kb < 1:
            self._add_glow(self._halo(frames[0]), (ox - 8 * s, oy - 8 * s), (48 * s, 48 * s),
                           min(1.0, k * 3) * (1 - kb))
        # Battito e occhiolino: frame disegnati; occhi aperti: corpo senza occhi +
        # occhi che scivolano di `shift` pixel dello sprite. Con lo sfondo arancio
        # niente ombra a terra (riga 27), che resterebbe come una striscia scura.
        img = self._eyeless(frames[0]) if eyes in ZOOM_GAZE else frames[eyes]
        rows = 27 if kb > 0 else 32
        self.surface.blit(pygame.transform.scale(img.subsurface((0, 0, 32, rows)), (round(32 * s), round(rows * s))),
                          (round(ox), round(oy)))
        if eyes in ZOOM_GAZE:
            for ex in ZOOM_EYE_X:
                pygame.draw.rect(self.surface, ZOOM_EYE, (round(ox + (ex + shift[0]) * s), round(oy + (ZOOM_EYE_Y + shift[1]) * s),
                                                          max(1, round(s)), max(1, round(2 * s))))
        # Luce calda al centro che pulsa col respiro, quando lo schermo è arancio.
        # Sommata sopra lo sprite: sotto, il corpo pieno la coprirebbe e se ne vedrebbe la sagoma
        if kb > 0:
            self._add_glow(_radial(), (0, 0), (w, h), kb * ZOOM_CENTER_GLOW * (0.65 + 0.35 * breath))
        if kb >= 1:
            self._zoom_text()

    def _zoom_text(self) -> None:
        """
        In alto icona del tipo di lavoro + nome della sessione (o repo), todo e
        altre sessioni al lavoro; in basso consumi 5h e 7g a sinistra e orario a destra.
        """
        w, h = self.size
        tft = self.profile == "tft"
        work = [s for s in self.sessions if s.status == WORKING]
        if work:
            s = work[0]
            done, total = s.progress
            tail = " ".join(x for x in (f"{done}/{total}" if total else "", f"+{len(work) - 1}" if len(work) > 1 else "") if x)
            icon = _ZOOM_ICONS.get(tool_group(s.tool) if s.tool else "think", _ZOOM_ICONS[""])
            name = s.title or s.project
            if tft:  # icona 15 px + testo, centrati insieme
                while len(name) > 1 and self.font_m.size(f"{name} {tail}")[0] > w - 40:
                    name = name[:-2] + "…"
                img = self.font_m.render(f"{name} {tail}".strip(), True, ZOOM_TEXT)
                x = (w - 20 - img.get_width()) // 2
                _draw_icon(self.surface, icon, x, 10, 3)
                self.surface.blit(img, (x + 20, 11))
            else:  # icona 5 px + font 3x5: fino a 14 caratteri
                name = "".join(c for c in name.upper() if c.isalnum() or c == " ").strip()
                txt = (name[:max(1, 14 - len(tail) - bool(tail))].strip() + " " + tail).strip()
                x = (w - 7 - tiny_width(txt)) // 2
                _draw_icon(self.surface, icon, x, 1, 1)
                tiny_text(self.surface, txt, x + 7, 1, ZOOM_TEXT)
        # In basso: consumi a sinistra (5h poi 7g), orario a destra
        clock = datetime.now().strftime("%H:%M")
        if tft:
            lims = "   ".join(f"{label} {pct:.0f}%" for label, pct, _, _ in self.limits)
            for txt, right in ((lims, False), (clock, True)):
                img = self.font_m.render(txt, True, ZOOM_TEXT)
                self.surface.blit(img, (w - 14 - img.get_width() if right else 14, h - 10 - img.get_height()))
            return
        # Font 3x5: senza etichette per starci (prima 5h, poi 7g)
        lims = " ".join(f"{pct:.0f}%" for _, pct, _, _ in self.limits)
        tiny_text(self.surface, lims, 1, h - 6, ZOOM_TEXT)
        tiny_text(self.surface, clock, w - 1 - tiny_width(clock), h - 6, ZOOM_TEXT)

    def _add_glow(self, glow: pygame.Surface, pos, size, intensity: float) -> None:
        """Somma una luce (scalata morbida) allo schermo, con intensità 0..1."""
        if intensity <= 0.01 or size[0] < 1:
            return
        g = pygame.transform.smoothscale(glow, (round(size[0]), round(size[1])))
        v = round(255 * min(1.0, intensity))
        g.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
        self.surface.blit(g, (round(pos[0]), round(pos[1])), special_flags=pygame.BLEND_RGB_ADD)

    def _halo(self, sprite: pygame.Surface) -> pygame.Surface:
        """Sagoma sfocata della mascotte (48x48, sprite al centro), calcolata una volta."""
        if getattr(self, "_halo_cache", None) is None:
            base = pygame.Surface((48, 48))
            sil = pygame.mask.from_surface(sprite).to_surface(setcolor=ZOOM_GLOW, unsetcolor=(0, 0, 0))
            base.blit(sil, (8, 8))
            self._halo_cache = pygame.transform.gaussian_blur(base, 3)
        return self._halo_cache

    def _eyeless(self, sprite: pygame.Surface) -> pygame.Surface:
        """Frame a occhi aperti con gli occhi coperti dal colore del corpo (li ridisegna _zoom)."""
        if getattr(self, "_eyeless_cache", None) is None:
            img = sprite.copy()
            for ex in ZOOM_EYE_X:
                pygame.draw.rect(img, MASCOT_BODY, (ex, ZOOM_EYE_Y, 1, 2))
            self._eyeless_cache = img
        return self._eyeless_cache

    def _mascot(self, overall, t, size, left, room, y):
        """
        Mascotte e posizione per blit. Ferma è centrata nei `room` pixel liberi
        a partire da `left`; nella passeggiata va avanti e indietro lì dentro,
        specchiata quando torna verso sinistra.
        """
        img = self.mascot.get(overall, t, size, self.variant, self.minis, self.holiday)
        self.mascot_rect = pygame.Rect((left + room // 2, y), img.get_size())  # punto di partenza dello zoom
        if not self.variant.endswith("-walk") or room <= 0:
            return img, (left + room // 2, y)
        pos = (time.time() * WALK_SPEED) % (2 * room)
        if pos < room:
            return img, (left + int(pos), y)
        # Ritorno verso sinistra: frame "-left" se esistono, altrimenti specchio
        back = f"{self.variant}-left"
        if back in self.mascot.frames:
            img = self.mascot.get(overall, t, size, back, self.minis, self.holiday)
        else:
            img = pygame.transform.flip(img, True, False)
        return img, (left + int(2 * room - pos), y)

    def _limit_strip(self, x: int, y: int, w: int) -> None:
        """Display piccoli: una barretta da 1 px per limite, 5h poi 7g, affiancate."""
        for i, (_, pct, _, elapsed) in enumerate(self.limits):
            limit_bar(self.surface, pygame.Rect(x + i * (w + 1), y, w, 1), pct, elapsed)

    # ---------------------------------------------------------------- TFT --
    def _draw_tft(self, sessions, overall, t):
        surf = self.surface
        # Barra superiore con titolo e numero di sessioni
        pygame.draw.rect(surf, (22, 26, 34), (0, 0, 320, 20))
        surf.blit(self.font_m.render("LEDINO", True, FG), (6, 4))
        n_work = sum(1 for s in sessions if s.status == WORKING)
        n_wait = sum(1 for s in sessions if s.status == WAITING)
        info = f"{len(sessions)} sess · {n_work} lav · {n_wait} att"
        txt = self.font_s.render(info, True, DIM)
        surf.blit(txt, (314 - txt.get_width(), 6))
        if overall == IDLE:
            return self._tft_pause(sessions, t)

        # Pannello sinistro: mascotte + stato globale
        surf.blit(*self._mascot(overall, t, 96, left=0, room=16, y=40))
        label = self.font_l.render(LABELS[overall], True, STATUS_COLOR[overall])
        surf.blit(label, (56 - label.get_width() // 2, 150))
        if not sessions:
            msg = self.font_s.render("nessuna sessione", True, DIM)
            surf.blit(msg, (56 - msg.get_width() // 2, 172))
        # In fondo a sinistra: limiti sessione (5h) e settimana (7g)
        for i, (label, pct, reset, elapsed) in enumerate(self.limits):
            y = 192 + i * 22
            surf.blit(self.font_s.render(f"{label} {pct:.0f}%", True, limit_color(pct, elapsed)), (6, y))
            if reset:
                r = self.font_s.render(reset, True, DIM)
                surf.blit(r, (106 - r.get_width(), y))
            limit_bar(surf, pygame.Rect(6, y + 11, 100, 5), pct, elapsed)

        # Pannello destro: fino a 4 card di sessione
        x0, y, card_h = 116, 26, 52
        shown = sessions[:4]
        for s in shown:
            self._tft_card(s, pygame.Rect(x0, y, 198, card_h - 4), t)
            y += card_h
        if len(sessions) > 4:
            more = self.font_s.render(f"+{len(sessions) - 4} altre", True, DIM)
            surf.blit(more, (x0, 226))

    def _tft_pause(self, sessions, t):
        """Tutto in pausa: mascotte grande al centro, sessioni piccole in riga sotto il titolo, consumi in fondo."""
        surf = self.surface
        # Sessioni: una riga sola, pallino + nome, max 4 poi "+N"
        shown = sessions[:4] if len(sessions) <= 4 else sessions[:3]
        if not sessions:
            msg = self.font_s.render("nessuna sessione", True, DIM)
            surf.blit(msg, (160 - msg.get_width() // 2, 25))
        w = 308 // max(1, len(shown) + (len(sessions) > 4))
        for i, s in enumerate(shown):
            x = 6 + i * w
            pygame.draw.circle(surf, STATUS_COLOR[s.status], (x + 3, 30), 3)
            name = s.title or s.project
            while len(name) > 1 and self.font_s.size(name)[0] > w - 16:
                name = name[:-2] + "…"
            surf.blit(self.font_s.render(name, True, DIM), (x + 10, 25))
        if len(sessions) > 4:
            surf.blit(self.font_s.render(f"+{len(sessions) - 3}", True, DIM), (6 + 3 * w, 25))

        # Mascotte 160 px (5x lo sprite 32) al centro; passeggiando attraversa tutto il popup
        surf.blit(*self._mascot(IDLE, t, 160, left=0, room=160, y=36))
        label = self.font_l.render(LABELS[IDLE], True, STATUS_COLOR[IDLE])
        surf.blit(label, (160 - label.get_width() // 2, 186))

        # In fondo: limiti 5h e 7g affiancati
        for i, (label, pct, reset, elapsed) in enumerate(self.limits):
            x = 6 + i * 157
            surf.blit(self.font_s.render(f"{label} {pct:.0f}%", True, limit_color(pct, elapsed)), (x, 212))
            if reset:
                r = self.font_s.render(reset, True, DIM)
                surf.blit(r, (x + 151 - r.get_width(), 212))
            limit_bar(surf, pygame.Rect(x, 224, 151, 5), pct, elapsed)

    def _tft_card(self, s: Session, r: pygame.Rect, t: float) -> None:
        surf, col = self.surface, STATUS_COLOR[s.status]
        pygame.draw.rect(surf, (18, 21, 28), r, border_radius=4)
        pygame.draw.rect(surf, col, (r.x, r.y, 3, r.height))  # bordo colorato
        # Riga 1: progetto · nome sessione, troncato alla larghezza della card
        name = f"{s.project} · {s.title}" if s.title else s.project
        while len(name) > 1 and self.font_m.size(name)[0] > r.width - 12:
            name = name[:-2] + "…"
        surf.blit(self.font_m.render(name, True, FG), (r.x + 8, r.y + 4))
        # Riga 2: stato + tool corrente
        detail = LABELS[s.status].lower()
        if s.status == WORKING and s.tool:
            detail += f" · {s.tool}"
        elif s.status == WAITING:
            detail += " · serve te"
        surf.blit(self.font_s.render(detail, True, col), (r.x + 8, r.y + 19))
        # Riga 3: barra + contatore todo
        done, total = s.progress
        progress_bar(surf, pygame.Rect(r.x + 8, r.y + 33, 140, 9), s, t, border=True)
        cnt = f"{done}/{total}" if total else "—"
        surf.blit(self.font_s.render(cnt, True, DIM), (r.x + 154, r.y + 32))

    # -------------------------------------------------------- LED 64x32 --
    def _draw_led(self, sessions, overall, t):
        surf = self.surface
        # Mascotte 32x32 a sinistra
        surf.blit(*self._mascot(overall, t, 32, left=0, room=0, y=0))  # nessuno spazio: cammina sul posto
        if not sessions:
            tiny_text(surf, "ZZ", 42, 13, DIM)
            self._limit_strip(33, 31, 15)
            return
        # A destra: una riga ogni 8 px (max 4) con sigla + barra
        rows = sessions[:4]
        if len(sessions) > 4:
            rows = sessions[:3]
        for i, s in enumerate(rows):
            y = i * 8 + 1
            tiny_text(surf, short_name(s.project, 3), 33, y, STATUS_COLOR[s.status])
            progress_bar(surf, pygame.Rect(46, y + 1, 17, 3), s, t, border=False)
        if len(sessions) > 4:
            tiny_text(surf, f"+{len(sessions) - 3}", 33, 25, DIM)
        self._limit_strip(33, 31, 15)

    # ------------------------------------------------------ Pixoo 64x64 --
    def _draw_pixoo(self, sessions, overall, t):
        surf = self.surface
        # Mascotte 32x32 centrata in alto
        surf.blit(*self._mascot(overall, t, 32, left=0, room=32, y=1))
        # Etichetta di stato globale + numero sessioni
        label = LABELS[overall]
        tiny_text(surf, label, (64 - tiny_width(label)) // 2, 35, STATUS_COLOR[overall])
        self._limit_strip(0, 63, 31)
        if not sessions:
            return
        # Fino a 3 righe di sessione (sigla + barra)
        rows = sessions[:3]
        if len(sessions) > 3:
            rows = sessions[:2]
        for i, s in enumerate(rows):
            y = 43 + i * 7
            tiny_text(surf, short_name(s.project, 3), 1, y, STATUS_COLOR[s.status])
            progress_bar(surf, pygame.Rect(14, y + 1, 49, 3), s, t, border=False)
        if len(sessions) > 3:
            tiny_text(surf, f"+{len(sessions) - 2} ALTRE", 1, 57, DIM)


# ===========================================================================
# Resa a schermo (ingrandimento + effetto LED)
# ===========================================================================
def make_led_mask(size: tuple[int, int], scale: float) -> pygame.Surface:
    """
    Maschera nera con "buchi" circolari: sovrapposta all'immagine ingrandita
    simula i singoli LED con lo spazio scuro tra uno e l'altro.
    """
    w, h = size
    mask = pygame.Surface((round(w * scale), round(h * scale)), pygame.SRCALPHA)
    mask.fill((0, 0, 0, 255))
    radius = scale * 0.42
    # Disegniamo i fori direttamente sulla maschera: draw.circle scrive anche
    # l'alpha (0 = trasparente), mentre un blit lo fonderebbe senza bucare.
    for y in range(h):
        for x in range(w):
            pygame.draw.circle(mask, (0, 0, 0, 0), ((x + 0.5) * scale, (y + 0.5) * scale), radius)
    return mask


def upscale(native: pygame.Surface, scale: float, led_mask: pygame.Surface | None):
    """
    Ingrandisce senza sfocatura e applica la maschera LED se presente.
    ponytail: con scala non intera i pixel escono larghi 1 o 2 punti alterni (nearest);
    a schermo quasi non si nota, smoothscale sfocherebbe la pixel art.
    """
    big = pygame.transform.scale(native, (round(native.get_width() * scale), round(native.get_height() * scale)))
    if led_mask is not None:
        big.blit(led_mask, (0, 0))
    return big

