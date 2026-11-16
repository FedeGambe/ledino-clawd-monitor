"""
Claude Code LED Monitor — simulatore su PC.

Avvia:
  - un piccolo server HTTP locale che riceve gli eventi da hook_relay.py;
  - una finestra pygame che emula il pannello scelto.

Uso:
    python monitor.py                 # profilo TFT 320x240
    python monitor.py --profile led   # matrice LED 64x32
    python monitor.py --demo          # eventi finti, senza Claude Code

Tasti nella finestra:
    1 / 2 / 3   cambia profilo (TFT / LED 64x32 / Pixoo 64x64)
    D           avvia/ferma la demo
    ESC         esci
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pygame

from demo import DemoFeeder
from render import PROFILES, Mascot, Renderer, make_led_mask, upscale
from state import StateStore, overall_status

HERE = Path(__file__).resolve().parent
BEZEL = 24          # cornice scura attorno al display, in pixel finestra
FPS = 20


# ===========================================================================
# Server HTTP: riceve gli eventi dagli hook
# ===========================================================================
def make_handler(store: StateStore):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            # POST /event  -> evento hook in formato JSON
            if self.path != "/event":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                store.apply(json.loads(self.rfile.read(length)))
                self.send_response(204)
            except Exception:
                self.send_response(400)
            self.end_headers()

        def do_GET(self):
            # GET /state -> stato aggregato; il pannello vero potrà leggerlo da qui
            if self.path != "/state":
                self.send_error(404)
                return
            body = json.dumps(store.to_json()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass  # niente log su console a ogni evento

    return Handler


def start_server(store: StateStore, port: int) -> ThreadingHTTPServer:
    # Solo 127.0.0.1: il server non è raggiungibile da altri PC della rete
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(store))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ===========================================================================
# Finestra
# ===========================================================================
class MonitorWindow:
    def __init__(self, store: StateStore, profile: str, scale: int | None) -> None:
        self.store = store
        self.scale_override = scale
        self.mascot = None
        self.set_profile(profile)

    def set_profile(self, profile: str) -> None:
        """Cambia profilo e ridimensiona la finestra di conseguenza."""
        cfg = PROFILES[profile]
        self.profile = profile
        self.scale = self.scale_override or cfg["scale"]
        w, h = cfg["size"]
        self.screen = pygame.display.set_mode((w * self.scale + 2 * BEZEL, h * self.scale + 2 * BEZEL))
        pygame.display.set_caption(f"Claude Monitor — {cfg['name']}   [1/2/3 profilo · D demo · ESC esci]")
        # Gli sprite PNG vanno caricati dopo set_mode (servono per convert)
        if self.mascot is None:
            self.mascot = Mascot(HERE / "sprites")
        self.renderer = Renderer(profile, self.mascot)
        self.led_mask = make_led_mask(cfg["size"], self.scale) if cfg["led"] else None

    def frame(self, t: float) -> pygame.Surface:
        """Disegna un frame completo (display + cornice) e lo restituisce."""
        sessions = self.store.snapshot()
        native = self.renderer.draw(sessions, overall_status(sessions), t, self.store.limits)
        self.screen.fill((28, 30, 36))  # cornice
        self.screen.blit(upscale(native, self.scale, self.led_mask), (BEZEL, BEZEL))
        return self.screen


def main() -> None:
    ap = argparse.ArgumentParser(description="Simulatore pannello Claude Code")
    ap.add_argument("--profile", choices=PROFILES, default="tft")
    ap.add_argument("--scale", type=int, help="ingrandimento (default dipende dal profilo)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--demo", action="store_true", help="genera eventi finti")
    ap.add_argument("--festa", choices=["christmas", "newyear", "halloween", "valentine", "off"],
                    help="forza una festa (default: in base alla data)")
    args = ap.parse_args()
    if args.festa:
        os.environ["CLAUDE_MONITOR_FESTA"] = args.festa

    store = StateStore()
    try:
        start_server(store, args.port)
    except OSError:
        print(f"Porta {args.port} occupata: il monitor è già aperto? Prova --port.")
        return

    pygame.init()
    win = MonitorWindow(store, args.profile, args.scale)
    demo = DemoFeeder(store.apply) if args.demo else None
    if demo:
        demo.start()

    print(f"In ascolto su http://127.0.0.1:{args.port}/event  (stato: /state)")
    clock, t0 = pygame.time.Clock(), time.time()
    keys = {pygame.K_1: "tft", pygame.K_2: "led", pygame.K_3: "pixoo"}

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False
            elif e.type == pygame.KEYDOWN and e.key in keys:
                win.set_profile(keys[e.key])
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_d:
                # Avvia/ferma la demo al volo
                if demo and demo.is_alive():
                    demo.stop()
                    demo = None
                else:
                    demo = DemoFeeder(store.apply)
                    demo.start()
        win.frame(time.time() - t0)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
