"""
Stato aggregato delle sessioni Claude Code.

Riceve gli eventi JSON inviati dal mod led-monitor (hooks/register.ts) e mantiene,
per ogni sessione, progetto, stato corrente e avanzamento della todo list.
È indipendente dal display: lo usano sia il simulatore sia (in futuro)
il codice che pilota il pannello vero.
"""

from __future__ import annotations

import copy
import re
import threading
import time
from dataclasses import dataclass, field

# --- Stati possibili di una sessione -------------------------------------
WORKING = "working"   # sta elaborando / usando tool
WAITING = "waiting"   # ti aspetta (es. richiesta di permesso)
DONE = "done"         # ha appena finito di rispondere
IDLE = "idle"         # sessione aperta ma ferma da un po'

# Priorità per decidere lo stato "globale" mostrato dalla mascotte:
# se anche una sola sessione ti aspetta, è la cosa più importante da vedere.
PRIORITY = {WAITING: 3, WORKING: 2, DONE: 1, IDLE: 0}

# Etichette brevi in italiano, usate dai renderer
LABELS = {WORKING: "LAVORA", WAITING: "ATTENDE", DONE: "FINITO", IDLE: "PAUSA"}

# --- Timeout -------------------------------------------------------------
DONE_TO_IDLE_S = 10 * 60      # dopo 10 min "finito" diventa "pausa"
ERROR_SHOW_S = 4             # durata dell'animazione di errore
WAKE_SHOW_S = 2              # durata del risveglio a inizio sessione

# Tool con cui Claude ti fa una domanda o ti chiede di approvare un piano
ASK_TOOLS = ("AskUserQuestion", "ExitPlanMode")
STALE_SESSION_S = 60 * 60     # sessione senza eventi da 1 h: la rimuoviamo
                              # (copre le sessioni chiuse senza SessionEnd)


@dataclass
class Session:
    """Una sessione di Claude Code (una finestra/terminale)."""

    session_id: str
    project: str
    status: str = IDLE
    tool: str = ""                 # ultimo tool in uso (Edit, Bash, ...)
    message: str = ""              # testo dell'ultima Notification
    error_until: float = 0.0       # fino a quando mostrare l'errore di un tool
    wake_until: float = 0.0        # fino a quando mostrare il risveglio (sessione nuova)
    background: int = 0            # comandi ancora in background (dal mod led-monitor)
    title: str = ""                # nome della sessione (/rename o titolo automatico)
    updated: float = field(default_factory=time.time)
    # Todo list: id del task -> stato ("pending" | "in_progress" | "completed")
    todos: dict = field(default_factory=dict)
    _auto_id: int = 0              # contatore per task senza id riconoscibile

    @property
    def progress(self) -> tuple[int, int]:
        """Restituisce (completati, totale) della todo list."""
        total = len(self.todos)
        done = sum(1 for s in self.todos.values() if s == "completed")
        return done, total


def project_name(cwd: str) -> str:
    """Nome del progetto = ultima cartella del cwd (gestisce / e \\)."""
    parts = [p for p in re.split(r"[\\/]", cwd or "") if p]
    return parts[-1] if parts else "?"


def _extract_task_id(response) -> str | None:
    """
    Cerca l'id del task creato nella risposta del tool TaskCreate.
    Il formato non è documentato in modo stabile, quindi proviamo più strade:
    chiavi note in un dict, poi pattern testuali come "Task #3 created".
    """
    if isinstance(response, dict):
        for key in ("id", "taskId", "task_id"):
            if key in response:
                return str(response[key])
        if isinstance(response.get("task"), dict):
            return _extract_task_id(response["task"])
    text = str(response)
    m = re.search(r"#(\w+)", text) or re.search(
        r"[\"']?(?:id|taskId)[\"']?\s*[:=]\s*[\"']?(\w+)", text
    )
    return m.group(1) if m else None


class StateStore:
    """Contenitore thread-safe di tutte le sessioni."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        # Limiti d'uso dell'account (dal mod led-monitor), es.
        # [{"kind": "five_hour", "percentUsed": 23.5, "resetsAt": "2026-..."}]
        self.limits: list[dict] = []

    # ------------------------------------------------------------------
    # Ingresso eventi
    # ------------------------------------------------------------------
    def apply(self, ev: dict) -> None:
        """Aggiorna lo stato in base a un evento hook di Claude Code."""
        name = ev.get("hook_event_name", "")
        if name == "RateLimits":
            # Valgono per tutto l'account: l'ultima lettura vince
            self.limits = list(ev.get("rate_limits") or [])
            return
        sid = ev.get("session_id")
        if not sid:
            return

        with self._lock:
            # Fine sessione: la togliamo dal pannello
            if name == "SessionEnd":
                self._sessions.pop(sid, None)
                return

            s = self._sessions.get(sid)
            if s is None:
                s = Session(session_id=sid, project=project_name(ev.get("cwd", "")))
                self._sessions[sid] = s
            elif ev.get("cwd"):
                s.project = project_name(ev["cwd"])
            if ev.get("session_title"):
                s.title = ev["session_title"]
            s.updated = time.time()

            if name == "Background":
                s.background = int(ev.get("count") or 0)

            elif name == "SessionStart":
                s.status = IDLE
                s.wake_until = time.time() + WAKE_SHOW_S

            elif name == "UserPromptSubmit":
                # Nuova richiesta: Claude inizia a lavorare
                s.status, s.tool, s.message = WORKING, "", ""

            elif name == "PreToolUse":
                s.tool = ev.get("tool_name", "")
                # Domanda o piano da approvare: anche questo aspetta te
                s.status = WAITING if s.tool in ASK_TOOLS else WORKING

            elif name == "PostToolUse":
                s.status = WORKING
                self._update_todos(s, ev)

            elif name == "PostToolUseFailure":
                # Tool fallito: la sessione continua, la mascotte fa "errore" per qualche secondo
                s.status = WORKING
                s.error_until = time.time() + ERROR_SHOW_S

            elif name == "Notification":
                self._handle_notification(s, ev)

            elif name == "Stop":
                # Ha finito di rispondere: ora tocca a te
                s.status, s.tool = DONE, ""

    def _handle_notification(self, s: Session, ev: dict) -> None:
        """
        Le Notification arrivano sia per le richieste di permesso (vero
        "ti aspetta") sia dopo un po' di inattività a risposta finita.
        Il secondo caso non deve trasformare "finito" in "attende".
        """
        msg = ev.get("message", "") or ""
        ntype = (ev.get("notification_type") or "").lower()
        is_idle_ping = "idle" in ntype or (
            s.status in (DONE, IDLE) and "permission" not in msg.lower()
        )
        if not is_idle_ping:
            s.status, s.message = WAITING, msg

    def _update_todos(self, s: Session, ev: dict) -> None:
        """
        Ricava l'avanzamento dalla todo list interna di Claude Code.
        Supporta sia il vecchio TodoWrite (lista completa a ogni chiamata)
        sia i tool incrementali TaskCreate / TaskUpdate delle versioni recenti.
        """
        tool = ev.get("tool_name", "")
        tin = ev.get("tool_input") or {}

        if tool == "TodoWrite":
            # Ogni chiamata riscrive l'intera lista
            todos = tin.get("todos") or []
            s.todos = {str(i): t.get("status", "pending") for i, t in enumerate(todos)}

        elif tool == "TaskCreate":
            tid = _extract_task_id(ev.get("tool_response"))
            if tid is None:
                s._auto_id += 1
                tid = f"auto{s._auto_id}"
            s.todos[tid] = "pending"

        elif tool == "TaskUpdate":
            tid = str(tin.get("taskId", ""))
            status = tin.get("status")
            if not tid or not status:
                return
            if status == "deleted":
                s.todos.pop(tid, None)
            else:
                s.todos[tid] = status

    # ------------------------------------------------------------------
    # Lettura
    # ------------------------------------------------------------------
    def snapshot(self) -> list[Session]:
        """
        Copia delle sessioni attive, già pulita dai timeout e ordinata:
        prima chi ti aspetta, poi chi lavora, poi le altre.
        """
        now = time.time()
        with self._lock:
            for sid, s in list(self._sessions.items()):
                age = now - s.updated
                if age > STALE_SESSION_S and not s.background:
                    del self._sessions[sid]
                elif s.status == DONE and age > DONE_TO_IDLE_S:
                    s.status = IDLE
            sessions = [copy.deepcopy(s) for s in self._sessions.values()]
        for s in sessions:
            # Ha finito di rispondere ma un comando gira ancora in background:
            # per il pannello sta ancora lavorando (costume terminale)
            if s.background and s.status in (DONE, IDLE):
                s.status, s.tool = WORKING, "background"
        sessions.sort(key=lambda s: (-PRIORITY[s.status], s.project.lower()))
        return sessions

    def to_json(self) -> dict:
        """Stato serializzabile: utile per far interrogare il pannello vero."""
        sessions = self.snapshot()
        return {
            "overall": overall_status(sessions),
            "sessions": [
                {
                    "project": s.project,
                    "title": s.title,
                    "status": s.status,
                    "tool": s.tool,
                    "done": s.progress[0],
                    "total": s.progress[1],
                }
                for s in sessions
            ],
            "limits": self.limits,
        }


def overall_status(sessions: list[Session]) -> str:
    """Stato più importante tra tutte le sessioni (guida la mascotte)."""
    if not sessions:
        return IDLE
    return max((s.status for s in sessions), key=PRIORITY.__getitem__)
