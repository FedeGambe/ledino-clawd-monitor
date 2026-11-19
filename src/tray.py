"""
Modalità tray: icona nell'area di notifica + popup sempre in primo piano.

L'icona prende il colore dello stato più importante (arancio lavora, giallo
attende, verde finito, grigio pausa). Clic sull'icona: mostra/nasconde il
popup, una finestra senza bordi in basso a destra con il layout TFT.

ponytail: pystray gira in un thread (run_detached), pygame nel principale.
Funziona su Windows e Linux; su macOS pystray vuole il thread principale,
da sistemare se servirà lì.
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import pygame
import pystray
from PIL import Image, ImageDraw

from render import MASCOT_BODY, STATUS_COLOR
from state import IDLE

TOGGLE = pygame.event.custom_type()   # inviato dal thread della tray
MARGIN = 4                            # distanza del popup dai bordi dello schermo
SPRITE = Path(__file__).resolve().parent.parent / "sprites" / "wake_2.png"  # mascotte in piedi, senza costume


def icon_image(color: tuple[int, int, int]) -> Image.Image:
    """La mascotte con il corpo del colore di stato (pallino se mancano gli sprite)."""
    try:
        src = Image.open(SPRITE).convert("RGBA")
    except OSError:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse((4, 4, 60, 60), fill=color, outline=(20, 22, 28), width=4)
        return img
    body = tuple(MASCOT_BODY[:3])
    src.putdata([(*color, a) if (r, g, b) == body else (r, g, b, a) for r, g, b, a in src.getdata()])
    src = src.crop(src.getbbox())
    # Quadrato centrato, ingrandito a pixel netti
    side = max(src.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(src, ((side - src.width) // 2, (side - src.height) // 2))
    return sq.resize((64, 64), Image.NEAREST)


def work_area() -> tuple[int, int, int, int]:
    """Area dello schermo principale senza la barra delle applicazioni."""
    if sys.platform == "win32":
        class RECT(ctypes.Structure):
            _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
        r = RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
        return r.l, r.t, r.r, r.b
    w, h = pygame.display.get_desktop_sizes()[0]
    return 0, 0, w, h - 48  # ponytail: barra stimata a 48 px fuori da Windows


def start_icon() -> pystray.Icon:
    def toggle(icon, item):
        pygame.event.post(pygame.event.Event(TOGGLE))

    def quit_(icon, item):
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    icon = pystray.Icon(
        "claude-monitor", icon_image(STATUS_COLOR[IDLE]), "Claude Monitor",
        menu=pystray.Menu(
            pystray.MenuItem("Mostra / nascondi", toggle, default=True),  # default = clic sinistro
            pystray.MenuItem("Esci", quit_),
        ),
    )
    icon.run_detached()
    return icon


def place_popup() -> pygame.Window:
    """Rende la finestra pygame un popup: senza bordi, in primo piano, sopra la tray."""
    win = pygame.Window.from_display_module()
    win.borderless = True
    win.always_on_top = True
    _, _, right, bottom = work_area()
    w, h = win.size
    win.position = (right - w - MARGIN, bottom - h - MARGIN)
    return win
