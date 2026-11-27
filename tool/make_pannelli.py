"""
Render dei display a grandezza reale: TFT 2.8" e matrici LED 64x64 / 64x32 a passo 2, 2.5, 3 mm.
Stessa scala (PX_MM pixel per millimetro) per tutti, cosi' le dimensioni si confrontano a occhio.
Output in docs/img/pannelli/: un PNG per pannello + confronto.png.
"""
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["CLAUDE_MONITOR_FESTA"] = "off"
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "src"))
import pygame
from state import StateStore
from monitor import MonitorWindow, overall_status

PX_MM = 5                      # risoluzione del render
TFT_MM = (57.6, 43.2)          # area attiva tipica di un TFT 2.8" 320x240
LED_MM = {2: 1.2, 2.5: 1.5, 3: 1.7}   # ponytail: diametro emissivo stimato dei LED SMD (1515/2020/2121), da tarare sul pannello vero
OUT = os.path.join(root, "docs", "img", "pannelli")

# --- stesse sessioni finte di make_shots.py --------------------------------
store = StateStore()
soon = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() + 2 * 3600)) + "+00:00"
later = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() + 4 * 86400)) + "+00:00"
store.apply({"hook_event_name": "RateLimits", "rate_limits": [
    {"kind": "five_hour", "percentUsed": 37, "resetsAt": soon},
    {"kind": "seven_day", "percentUsed": 62, "resetsAt": later}]})
def ev(sid, cwd, name, **kw):
    store.apply({"hook_event_name": name, "session_id": sid, "cwd": cwd, **kw})
a, b, c = r"C:\p\rag-pipeline", r"C:\p\dashboard-vendite", r"C:\p\ocr-fatture"
ev("c", c, "UserPromptSubmit", session_title="estrai totali"); ev("c", c, "Stop")
ev("b", b, "UserPromptSubmit", session_title="grafici Q3"); ev("b", b, "PreToolUse", tool_name="Bash")
ev("b", b, "Notification", message="Claude needs your permission to use Bash", notification_type="permission_prompt")
ev("a", a, "UserPromptSubmit", session_title="nuovo retriever")
ev("a", a, "PostToolUse", tool_name="TodoWrite", tool_input={"todos": [
    {"status": "completed"}, {"status": "completed"}, {"status": "in_progress"}, {"status": "pending"}]})
ev("a", a, "PreToolUse", tool_name="Edit")

pygame.init()
win = MonitorWindow(store, "tft", None)
def native(profile):
    win.set_profile(profile)
    s = store.snapshot()
    return win.renderer.draw(s, overall_status(s), 1.3, store.limits).copy()


def led_panel(img, pitch):
    """Matrice LED: pacchetti SMD neri su PCB, punto luminoso tondo + alone."""
    w, h = img.get_size()
    k = pitch * PX_MM                                   # pixel di render per LED
    W, H = round(w * k), round(h * k)
    out = pygame.Surface((W, H)); out.fill((6, 6, 8))
    body = pygame.Surface((W, H), pygame.SRCALPHA)
    lit = pygame.Surface((W, H)); lit.fill((0, 0, 0))
    r = LED_MM[pitch] * PX_MM / 2
    for y in range(h):
        for x in range(w):
            cx, cy = (x + 0.5) * k, (y + 0.5) * k
            pygame.draw.rect(body, (24, 24, 27), (cx - r * 1.25, cy - r * 1.25, r * 2.5, r * 2.5), border_radius=2)
            col = img.get_at((x, y))[:3]
            if any(col):
                pygame.draw.circle(lit, col, (cx, cy), r)
    out.blit(body, (0, 0))
    glow = pygame.transform.gaussian_blur(pygame.transform.smoothscale(img, (W, H)), round(k * 0.6))
    glow.fill((70, 70, 70), special_flags=pygame.BLEND_MULT)   # alone ~27%
    out.blit(glow, (0, 0), special_flags=pygame.BLEND_ADD)
    out.blit(lit, (0, 0), special_flags=pygame.BLEND_ADD)
    return out


def tft_panel(img):
    """TFT: pixel piccolissimi, riduzione morbida alla grandezza reale + leggero vetro."""
    W, H = round(TFT_MM[0] * PX_MM), round(TFT_MM[1] * PX_MM)
    out = pygame.transform.smoothscale(img, (W, H))
    out.fill((235, 238, 245), special_flags=pygame.BLEND_MULT)
    return out


def framed(panel, title, mm):
    """Cornice nera con titolo e misure sotto."""
    pad, lab = 6 * PX_MM, 44
    s = pygame.Surface((panel.get_width() + 2 * pad, panel.get_height() + 2 * pad + lab))
    s.fill((22, 23, 27))
    pygame.draw.rect(s, (12, 12, 14), (pad // 2, pad // 2, panel.get_width() + pad, panel.get_height() + pad), border_radius=6)
    s.blit(panel, (pad, pad))
    f = pygame.font.Font(None, 26); g = pygame.font.Font(None, 20)
    y = panel.get_height() + 2 * pad
    s.blit(f.render(title, True, (235, 235, 235)), (pad, y))
    s.blit(g.render(f"{mm[0]:g} x {mm[1]:g} mm", True, (150, 150, 160)), (pad, y + 22))
    return s


os.makedirs(OUT, exist_ok=True)
tiles = []
tft = framed(tft_panel(native("tft")), 'TFT 2.8" 320x240', TFT_MM)
tiles.append(("tft", tft))
for prof, (w, h) in (("pixoo", (64, 64)), ("led", (64, 32))):
    img = native(prof)
    for p in (2, 2.5, 3):
        name = f"led{w}x{h}-p{p:g}".replace(".", "")
        tiles.append((name, framed(led_panel(img, p), f"LED {w}x{h} P{p:g}", (w * p, h * p))))
for name, t in tiles:
    pygame.image.save(t, os.path.join(OUT, f"{name}.png"))

# Confronto a scala comune: riga 1 TFT + 64x64, riga 2 64x32
rows = [tiles[:4], tiles[4:]]
gap = 30
W = max(sum(t.get_width() for _, t in r) + gap * (len(r) + 1) for r in rows)
H = sum(max(t.get_height() for _, t in r) for r in rows) + gap * 3 + 40
sheet = pygame.Surface((W, H)); sheet.fill((40, 42, 48))
sheet.blit(pygame.font.Font(None, 30).render(f"Stessa scala: {PX_MM} px = 1 mm", True, (220, 220, 220)), (gap, 14))
y = 40 + gap
for r in rows:
    x = gap
    for _, t in r:
        sheet.blit(t, (x, y + max(u.get_height() for _, u in r) - t.get_height())); x += t.get_width() + gap
    y += max(t.get_height() for _, t in r) + gap
pygame.image.save(sheet, os.path.join(OUT, "confronto.png"))
print("ok", OUT)
