"""Rigenera gli screenshot dei display in docs/img/screen-*.png (sessioni finte, senza finestra)."""
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["CLAUDE_MONITOR_FESTA"] = "off"
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(root, "src"))
import pygame
from state import StateStore
from monitor import MonitorWindow

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
for p in ("tft", "led", "pixoo"):
    win.set_profile(p)
    pygame.image.save(win.frame(1.3), os.path.join(root, "docs", "img", f"screen-{p}.png"))


# Layout di pausa (TFT): tutte le sessioni ferme, scena caffè
import render
render.PAUSE_SCENES = ("coffee",)
win.store = store = StateStore()
store.limits = [{"kind": "five_hour", "percentUsed": 12, "resetsAt": soon},
                {"kind": "seven_day", "percentUsed": 48, "resetsAt": later}]
for sid, cwd in (("a", a), ("b", b)):
    ev(sid, cwd, "SessionStart")
for s in store._sessions.values():
    s.wake_until = 0
win.set_profile("tft")
pygame.image.save(win.frame(1.3), os.path.join(root, "docs", "img", "screen-pausa.png"))


# Galleria: foglio di frame dello zoom al lavoro (docs/img/anim/zoom.png), 64x64 come un Pixoo.
# Lo zoom è un effetto del renderer, non uno sprite: lo si disegna frame per frame dal vero _zoom.
from pathlib import Path
from state import WORKING
FPS, LEAD, TAIL = 12, 1.0, 0.5   # 1 s al lavoro prima, mezzo secondo dopo
r = render.Renderer("pixoo", render.Mascot(Path(root) / "sprites"))
r.mascot_rect = pygame.Rect(0, 0, 64, 64)
r.sessions = [s for s in store._sessions.values()][:1]
for s in r.sessions:
    s.status, s.tool = WORKING, "Edit"
r.limits = render.limit_rows(store.limits)
look = sum(d for _, d in render.ZOOM_PLAN)   # un giro di sguardi, poi una sessione finisce e torna piccola
total = LEAD + 2 * render.ZOOM_GROW_S + look + TAIL


def zoom_at(p):
    if p < render.ZOOM_GROW_S:
        r._zoom(p / render.ZOOM_GROW_S, None)
    elif p < render.ZOOM_GROW_S + look:
        r._zoom(1.0, p - render.ZOOM_GROW_S)
    elif p < 2 * render.ZOOM_GROW_S + look:
        r._zoom(1 - (p - render.ZOOM_GROW_S - look) / render.ZOOM_GROW_S, None)


n = round(total * FPS)
sheet = pygame.Surface((64 * n, 64), pygame.SRCALPHA)
for i in range(n):
    t = i / FPS
    # Due passate: su nero (con la luce sommata) e su trasparente (dove c'è qualcosa di pieno)
    lit, solid = (pygame.Surface((64, 64), pygame.SRCALPHA) for _ in range(2))
    lit.fill((0, 0, 0, 255))
    for surf in (lit, solid):
        r.surface = surf
        surf.blit(r.mascot.get(WORKING, t, 64), (0, 0))
        if t >= LEAD:
            zoom_at(t - LEAD)
    # Fuori dalle parti piene la luce diventa trasparenza (alone su sfondo trasparente)
    for y in range(64):
        for x in range(64):
            c = lit.get_at((x, y))
            if solid.get_at((x, y)).a:
                sheet.set_at((i * 64 + x, y), (c.r, c.g, c.b, 255))
            elif (a := max(c.r, c.g, c.b)):
                sheet.set_at((i * 64 + x, y), (c.r * 255 // a, c.g * 255 // a, c.b * 255 // a, a))
pygame.image.save(sheet, os.path.join(root, "docs", "img", "anim", "zoom.png"))
print(f"zoom.png: {n} frame, {total:.2f} s")
