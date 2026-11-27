"""
Modalità tray: icona nell'area di notifica + popup sempre in primo piano.

L'icona è la mascotte animata dello stato più importante (arancio lavora, giallo
attende, verde finito, grigio pausa). Clic sull'icona: mostra/nasconde il
popup, una finestra senza bordi in basso a destra con il layout TFT.

ponytail: pystray gira in un thread (run_detached), pygame nel principale.
Funziona su Windows e Linux; su macOS pystray vuole il thread principale,
da sistemare se servirà lì.
"""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from pathlib import Path

import pygame
import pystray
from PIL import Image, ImageDraw

from render import _FPS, MASCOT_BODY, STATUS_COLOR

TOGGLE = pygame.event.custom_type()   # dal thread della tray: mostra/nasconde
RESET = pygame.event.custom_type()    # dal thread della tray: riporta il popup nell'angolo
MARGIN = 4                            # distanza del popup dai bordi dello schermo
SPRITES = Path(__file__).resolve().parent.parent / "sprites"
_frames: dict[str, list[Image.Image]] = {}


def icon_frames(state: str) -> list[Image.Image]:
    """
    Frame animati dell'icona: la mascotte dello stato (working_*.png, ...)
    con il corpo del colore di stato. Pallino fisso se mancano gli sprite.
    """
    if state in _frames:
        return _frames[state]
    color = STATUS_COLOR[state]
    srcs = [Image.open(f).convert("RGBA") for f in sorted(SPRITES.glob(f"{state}_*.png"))]
    if not srcs:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse((4, 4, 60, 60), fill=color, outline=(20, 22, 28), width=4)
        _frames[state] = [img]
        return _frames[state]
    # Corpo = colore pieno più frequente (in pausa è un arancio più scuro di MASCOT_BODY)
    body = max((c for c in srcs[0].getcolors() if c[1][3] == 255), default=(0, MASCOT_BODY))[1][:3]
    # Un solo ritaglio per tutti i frame, così la mascotte non "salta" tra un frame e l'altro
    boxes = [s.getbbox() for s in srcs]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes),
           max(b[2] for b in boxes), max(b[3] for b in boxes))
    out = []
    for src in srcs:
        src.putdata([(*color, a) if (r, g, b) == body else (r, g, b, a) for r, g, b, a in src.getdata()])
        src = src.crop(box)
        # Quadrato centrato, ingrandito a pixel netti
        side = max(src.size)
        sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        sq.paste(src, ((side - src.width) // 2, (side - src.height) // 2))
        out.append(sq.resize((64, 64), Image.NEAREST))
    _frames[state] = out
    return out


def icon_frame(state: str, t: float) -> int:
    """Indice del frame al tempo t (stessa velocità della mascotte nel popup)."""
    return int(t * _FPS[state]) % len(icon_frames(state))


_hicons: dict[tuple[str, int], int] = {}


def set_icon(icon: pystray.Icon, state: str, i: int) -> None:
    """
    Cambia il frame dell'icona. Su Windows pystray a ogni cambio scrive un .ico
    temporaneo e lo ricarica: su disco lento/antivirus il loop si blocca e Windows
    dà "Non risponde". Qui ogni frame diventa un HICON una volta sola, in memoria.
    """
    if sys.platform != "win32":
        icon.icon = icon_frames(state)[i]
        return
    from io import BytesIO
    from pystray._util import win32  # ponytail: API interna di pystray 0.19
    h = _hicons.get((state, i))
    if h is None:
        buf = BytesIO()
        icon_frames(state)[i].save(buf, "PNG")
        data = buf.getvalue()
        f = ctypes.windll.user32.CreateIconFromResourceEx
        f.restype = ctypes.c_void_p
        f.argtypes = [ctypes.c_char_p, ctypes.c_uint, ctypes.c_int, ctypes.c_uint,
                      ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        h = _hicons[(state, i)] = f(data, len(data), True, 0x00030000, 0, 0, 0)
    icon._message(win32.NIM_MODIFY, win32.NIF_ICON, hIcon=h)


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


wanted = ("idle", "Ledino")  # (stato, tooltip): lo scrive il loop pygame, lo legge _animate


def _animate(icon: pystray.Icon) -> None:
    """
    Anima l'icona in un thread suo. Shell_NotifyIcon parla con Explorer e può
    bloccarsi per secondi: se lo chiamasse il loop pygame, il popup andrebbe
    in "Non risponde".
    """
    t0, shown = time.time(), None
    while True:
        state, title = wanted
        now = (state, icon_frame(state, time.time() - t0))
        # icon.visible: prima che l'icona sia comparsa gli aggiornamenti vanno persi
        if icon.visible and now != shown:
            set_icon(icon, *now)
            icon.title = title  # pystray non fa nulla se non cambia
            shown = now
        time.sleep(0.05)


def start_icon() -> pystray.Icon:
    def toggle(icon, item):
        pygame.event.post(pygame.event.Event(TOGGLE))

    def reset(icon, item):
        pygame.event.post(pygame.event.Event(RESET))

    def quit_(icon, item):
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    icon = pystray.Icon(
        "ledino", icon_frames("idle")[0], "Ledino",
        menu=pystray.Menu(
            pystray.MenuItem("Mostra / nascondi", toggle, default=True),  # default = clic sinistro
            pystray.MenuItem("Riposiziona", reset),
            pystray.MenuItem("Esci", quit_),
        ),
    )
    icon.run_detached()
    threading.Thread(target=_animate, args=(icon,), daemon=True).start()
    return icon


def place_popup(corner: tuple[int, int] | None = None) -> pygame.Window:
    """
    Rende la finestra pygame un popup: senza bordi, in primo piano.
    corner: dove va l'angolo in basso a destra; di default sopra la tray.
    """
    win = pygame.Window.from_display_module()
    win.borderless = True
    win.always_on_top = True
    if corner is None:
        _, _, right, bottom = work_area()
        corner = (right - MARGIN, bottom - MARGIN)
    w, h = win.size
    win.position = (corner[0] - w, corner[1] - h)
    return win


def corner_of(win: pygame.Window) -> tuple[int, int]:
    """Angolo in basso a destra del popup: resta fermo quando cambia grandezza."""
    return win.position[0] + win.size[0], win.position[1] + win.size[1]
