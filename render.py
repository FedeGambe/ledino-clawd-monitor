"""
Renderer dei tre profili di display.

Ogni profilo disegna su una superficie alla risoluzione NATIVA del display
(es. 64x32 pixel). La finestra del simulatore la ingrandisce poi con
scaling "nearest" ed eventualmente l'effetto LED a puntini, così quello
che vedi è fedele a quello che vedresti sul pannello reale.
"""

from __future__ import annotations

import time
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
_FPS = {WORKING: 4, WAITING: 2, DONE: 1, IDLE: 0.5, "error": 6}


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
    "Bash": "bash", "PowerShell": "bash", "BashOutput": "bash",
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


# Posti liberi nel 32x32 per le mini-mascotte: in basso a sx, in basso a dx, a sx
_MINI_SPOTS = [(0, 27), (25, 27), (0, 21)]


def _draw_minis(img: pygame.Surface, colors: list, t: float) -> None:
    """Mini-mascotte 7x4 del colore di stato della sessione, che saltellano sfasate."""
    for n, (col, (x, y)) in enumerate(zip(colors, _MINI_SPOTS)):
        y -= int(t * 3 + n) % 2
        pygame.draw.rect(img, col, (x + 1, y, 5, 3))
        img.set_at((x, y + 1), col)          # braccia
        img.set_at((x + 6, y + 1), col)
        img.set_at((x + 2, y + 1), (24, 22, 22))  # occhi
        img.set_at((x + 4, y + 1), (24, 22, 22))
        img.set_at((x + 2, y + 3), col)      # gambe
        img.set_at((x + 4, y + 3), col)


class Mascot:
    """
    Gestisce i frame della mascotte.

    Se nella cartella sprites/ trovi file come working_0.png, working_1.png,
    waiting_0.png, ... vengono usati al posto del robottino segnaposto
    (qualsiasi dimensione: vengono scalati senza sfocatura).
    """

    def __init__(self, sprite_dir: Path | None = None) -> None:
        self.frames: dict[str, list[pygame.Surface]] = {}
        for state in STATUS_COLOR:
            custom = self._load_custom(sprite_dir, state) if sprite_dir else []
            self.frames[state] = custom or [_build_frame(state, i) for i in range(2)]
        # Varianti "working-<gruppo>" con l'oggetto del tool in uso (opzionali)
        for group in set(TOOL_GROUPS.values()) | {"mcp", "think"}:
            key = f"{WORKING}-{group}"
            custom = self._load_custom(sprite_dir, key) if sprite_dir else []
            if custom:
                self.frames[key] = custom
        # Tool fallito (opzionale): sostituisce per qualche secondo la mascotte
        custom = self._load_custom(sprite_dir, "error") if sprite_dir else []
        if custom:
            self.frames["error"] = custom

    @staticmethod
    def _load_custom(sprite_dir: Path, state: str) -> list[pygame.Surface]:
        files = sorted(sprite_dir.glob(f"{state}_*.png"))
        return [pygame.image.load(str(f)) for f in files]

    def get(self, state: str, t: float, size: int, tool: str = "",
            error: bool = False, minis: list = ()) -> pygame.Surface:
        """
        Frame corrente, scalato (nearest) a un quadrato di lato `size`.
        tool: tool in uso ("" = sta pensando), sceglie il costume se esiste.
        error: un tool è appena fallito. minis: colori delle mini-mascotte
        (una per ogni altra sessione attiva).
        """
        frames, fps = self.frames[state], _FPS[state]
        if error and "error" in self.frames:
            frames, fps = self.frames["error"], _FPS["error"]
        elif state == WORKING:
            group = tool_group(tool) if tool else "think"
            frames = self.frames.get(f"{WORKING}-{group}", frames)
        img = frames[int(t * fps) % len(frames)]
        if minis and img.get_size() == (32, 32):
            img = img.copy()
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
# Profili
# ===========================================================================
class Renderer:
    """Disegna lo stato su una superficie alla risoluzione nativa del profilo."""

    def __init__(self, profile: str, mascot: Mascot) -> None:
        self.profile = profile
        self.size = PROFILES[profile]["size"]
        self.mascot = mascot
        self.surface = pygame.Surface(self.size)
        if profile == "tft":
            # pygame.font.Font(None, ...) = font di default, sempre disponibile
            self.font_s = pygame.font.Font(None, 15)
            self.font_m = pygame.font.Font(None, 18)
            self.font_l = pygame.font.Font(None, 22)

    def draw(self, sessions: list[Session], overall: str, t: float) -> pygame.Surface:
        self.surface.fill(BG)
        # Tool mostrato dalla mascotte: quello della prima sessione al lavoro
        # ("" = ha ricevuto il prompt ma non usa ancora tool: sta pensando)
        self.tool = next((s.tool for s in sessions if s.status == WORKING), "")
        now = time.time()
        self.error = any(s.error_until > now for s in sessions)
        # Le altre sessioni attive diventano mini-mascotte (max 3)
        self.minis = [STATUS_COLOR[s.status] for s in sessions[1:] if s.status != IDLE][:3]
        getattr(self, f"_draw_{self.profile}")(sessions, overall, t)
        return self.surface

    # ---------------------------------------------------------------- TFT --
    def _draw_tft(self, sessions, overall, t):
        surf = self.surface
        # Barra superiore con titolo e numero di sessioni
        pygame.draw.rect(surf, (22, 26, 34), (0, 0, 320, 20))
        surf.blit(self.font_m.render("CLAUDE MONITOR", True, FG), (6, 4))
        n_work = sum(1 for s in sessions if s.status == WORKING)
        n_wait = sum(1 for s in sessions if s.status == WAITING)
        info = f"{len(sessions)} sess · {n_work} lav · {n_wait} att"
        txt = self.font_s.render(info, True, DIM)
        surf.blit(txt, (314 - txt.get_width(), 6))

        # Pannello sinistro: mascotte + stato globale
        img = self.mascot.get(overall, t, 96, self.tool, self.error, self.minis)
        surf.blit(img, (8 + (96 - img.get_width()) // 2, 40))
        label = self.font_l.render(LABELS[overall], True, STATUS_COLOR[overall])
        surf.blit(label, (56 - label.get_width() // 2, 150))
        if not sessions:
            msg = self.font_s.render("nessuna sessione", True, DIM)
            surf.blit(msg, (56 - msg.get_width() // 2, 172))

        # Pannello destro: fino a 4 card di sessione
        x0, y, card_h = 116, 26, 52
        shown = sessions[:4]
        for s in shown:
            self._tft_card(s, pygame.Rect(x0, y, 198, card_h - 4), t)
            y += card_h
        if len(sessions) > 4:
            more = self.font_s.render(f"+{len(sessions) - 4} altre", True, DIM)
            surf.blit(more, (x0, 226))

    def _tft_card(self, s: Session, r: pygame.Rect, t: float) -> None:
        surf, col = self.surface, STATUS_COLOR[s.status]
        pygame.draw.rect(surf, (18, 21, 28), r, border_radius=4)
        pygame.draw.rect(surf, col, (r.x, r.y, 3, r.height))  # bordo colorato
        # Riga 1: nome progetto (troncato)
        name = s.project if len(s.project) <= 22 else s.project[:21] + "…"
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
        surf.blit(self.mascot.get(overall, t, 32, self.tool, self.error, self.minis), (0, 0))
        if not sessions:
            tiny_text(surf, "ZZ", 42, 13, DIM)
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

    # ------------------------------------------------------ Pixoo 64x64 --
    def _draw_pixoo(self, sessions, overall, t):
        surf = self.surface
        # Mascotte 32x32 centrata in alto
        surf.blit(self.mascot.get(overall, t, 32, self.tool, self.error, self.minis), (16, 1))
        # Etichetta di stato globale + numero sessioni
        label = LABELS[overall]
        tiny_text(surf, label, (64 - tiny_width(label)) // 2, 35, STATUS_COLOR[overall])
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
def make_led_mask(size: tuple[int, int], scale: int) -> pygame.Surface:
    """
    Maschera nera con "buchi" circolari: sovrapposta all'immagine ingrandita
    simula i singoli LED con lo spazio scuro tra uno e l'altro.
    """
    w, h = size
    mask = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
    mask.fill((0, 0, 0, 255))
    radius = scale * 0.42
    # Disegniamo i fori direttamente sulla maschera: draw.circle scrive anche
    # l'alpha (0 = trasparente), mentre un blit lo fonderebbe senza bucare.
    for y in range(h):
        for x in range(w):
            pygame.draw.circle(mask, (0, 0, 0, 0), ((x + 0.5) * scale, (y + 0.5) * scale), radius)
    return mask


def upscale(native: pygame.Surface, scale: int, led_mask: pygame.Surface | None):
    """Ingrandisce senza sfocatura e applica la maschera LED se presente."""
    big = pygame.transform.scale(native, (native.get_width() * scale, native.get_height() * scale))
    if led_mask is not None:
        big.blit(led_mask, (0, 0))
    return big

