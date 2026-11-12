"""
Hook di Claude Code: inoltra l'evento al monitor locale.

Claude Code esegue questo script a ogni evento configurato in settings.json
e gli passa su stdin un JSON (session_id, cwd, hook_event_name, tool_name, ...).
Lo script lo rilancia via HTTP al monitor e termina subito.

Regole importanti per un hook:
- non stampare NULLA su stdout (per UserPromptSubmit verrebbe aggiunto
  al contesto di Claude);
- uscire sempre con codice 0, anche se il monitor è spento, così Claude
  Code non viene mai bloccato o disturbato;
- essere veloce: timeout di rete molto basso.
"""

import json
import os
import sys
import urllib.request

# Porta del monitor; sovrascrivibile con la variabile d'ambiente CLAUDE_MONITOR_URL
MONITOR_URL = os.environ.get("CLAUDE_MONITOR_URL", "http://127.0.0.1:8765/event")
TIMEOUT_S = 0.5

# Campi che servono davvero al monitor: evitiamo di spedire input/output
# voluminosi dei tool (es. il contenuto completo dei file modificati).
KEEP = ("session_id", "cwd", "hook_event_name", "tool_name", "message", "notification_type")
TODO_TOOLS = ("TodoWrite", "TaskCreate", "TaskUpdate")


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return  # input non valido: ignoriamo in silenzio

    payload = {k: event[k] for k in KEEP if k in event}
    # Input e risposta servono solo per i tool della todo list
    if event.get("tool_name") in TODO_TOOLS:
        payload["tool_input"] = event.get("tool_input")
        payload["tool_response"] = event.get("tool_response")

    try:
        req = urllib.request.Request(
            MONITOR_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=TIMEOUT_S).close()
    except Exception:
        pass  # monitor spento o non raggiungibile: nessun problema


if __name__ == "__main__":
    main()
    sys.exit(0)
