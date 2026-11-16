"""
Generatore di eventi finti per provare il monitor senza Claude Code.

Simula tre progetti che lavorano in parallelo, ognuno con il suo ritmo.
Gli eventi hanno lo stesso formato JSON degli hook veri, così si testa
anche il parsing (TodoWrite per un progetto, TaskCreate/TaskUpdate per gli altri).
"""

from __future__ import annotations

import random
import threading
import time


class DemoFeeder(threading.Thread):
    """Thread che invia eventi finti a una callback (es. StateStore.apply)."""

    PROJECTS = [
        ("demo-1", r"C:\Users\me\Progetti_Locale\rag-pipeline", "todowrite"),
        ("demo-2", r"C:\Users\me\Progetti_Locale\dashboard-vendite", "tasks"),
        ("demo-3", r"C:\Users\me\Progetti_Locale\ocr-fatture", "tasks"),
    ]
    TOOLS = ["Read", "Grep", "Edit", "Bash", "Write", "WebSearch"]

    def __init__(self, emit, speed: float = 1.0) -> None:
        super().__init__(daemon=True)
        self.emit = emit
        self.speed = speed           # >1 = più veloce
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def _sleep(self, seconds: float) -> bool:
        """Attende; restituisce False se il demo è stato fermato."""
        return not self.stop_event.wait(seconds / self.speed)

    def run(self) -> None:
        # Limiti finti (in produzione arrivano dal mod led-monitor-limits)
        soon = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() + 2 * 3600)) + "+00:00"
        later = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() + 4 * 86400)) + "+00:00"
        self.emit({"hook_event_name": "RateLimits", "rate_limits": [
            {"kind": "five_hour", "percentUsed": 37, "resetsAt": soon},
            {"kind": "seven_day", "percentUsed": 82.5, "resetsAt": later},
        ]})
        # Ogni progetto gira in un suo thread, sfasato nel tempo
        workers = [
            threading.Thread(target=self._project_loop, args=(p, i * 2.5), daemon=True)
            for i, p in enumerate(self.PROJECTS)
        ]
        for w in workers:
            w.start()
        self.stop_event.wait()
        # Alla fine chiudiamo le sessioni finte
        for sid, cwd, _ in self.PROJECTS:
            self.emit({"hook_event_name": "SessionEnd", "session_id": sid, "cwd": cwd})

    def _ev(self, sid, cwd, name, **extra) -> None:
        self.emit({"hook_event_name": name, "session_id": sid, "cwd": cwd, **extra})

    def _project_loop(self, project, delay: float) -> None:
        sid, cwd, mode = project
        rnd = random.Random(sid)
        if not self._sleep(delay):
            return
        self._ev(sid, cwd, "SessionStart")
        task_counter = 0

        while not self.stop_event.is_set():
            # 1) Arriva un prompt
            self._ev(sid, cwd, "UserPromptSubmit")
            if not self._sleep(1.0):
                return

            # 2) Claude si crea una todo list di N task
            n = rnd.randint(3, 7)
            if mode == "todowrite":
                todos = [{"content": f"step {i}", "status": "pending"} for i in range(n)]
                self._ev(sid, cwd, "PostToolUse", tool_name="TodoWrite", tool_input={"todos": todos})
            else:
                ids = []
                for _ in range(n):
                    task_counter += 1
                    ids.append(str(task_counter))
                    self._ev(sid, cwd, "PostToolUse", tool_name="TaskCreate",
                             tool_input={"subject": "step"},
                             tool_response=f"Task #{task_counter} created successfully")

            # 3) Lavora sui task uno alla volta, usando qualche tool
            for i in range(n):
                for _ in range(rnd.randint(2, 4)):
                    tool = rnd.choice(self.TOOLS)
                    self._ev(sid, cwd, "PreToolUse", tool_name=tool)
                    # Ogni tanto chiede un permesso e resta in attesa
                    if tool == "Bash" and rnd.random() < 0.25:
                        self._ev(sid, cwd, "Notification",
                                 message="Claude needs your permission to use Bash",
                                 notification_type="permission_prompt")
                        if not self._sleep(rnd.uniform(3, 6)):
                            return
                    if not self._sleep(rnd.uniform(0.6, 1.6)):
                        return
                    self._ev(sid, cwd, "PostToolUse", tool_name=tool)
                # Task completato
                if mode == "todowrite":
                    for j in range(i + 1):
                        todos[j]["status"] = "completed"
                    self._ev(sid, cwd, "PostToolUse", tool_name="TodoWrite", tool_input={"todos": todos})
                else:
                    self._ev(sid, cwd, "PostToolUse", tool_name="TaskUpdate",
                             tool_input={"taskId": ids[i], "status": "completed"})

            # 4) Fine risposta, pausa "umana" prima del prossimo prompt
            self._ev(sid, cwd, "Stop")
            if not self._sleep(rnd.uniform(5, 10)):
                return
