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
