"""
Aggiunge (o rimuove) gli hook del monitor in ~/.claude/settings.json.

Uso:
    python install_hooks.py            # mostra cosa cambierebbe (nessuna modifica)
    python install_hooks.py --apply    # scrive, dopo aver fatto un backup
    python install_hooks.py --remove   # toglie solo gli hook del monitor

Gli hook già presenti nel file non vengono toccati.
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

SETTINGS = Path.home() / ".claude" / "settings.json"
RELAY = Path(__file__).resolve().parent / "hook_relay.py"
MARKER = "hook_relay.py"  # serve a riconoscere i nostri hook

# Eventi da intercettare; i tool-event vogliono un matcher ("*" = tutti i tool)
EVENTS = ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
          "PostToolUseFailure", "Notification", "Stop", "SessionEnd"]
TOOL_EVENTS = {"PreToolUse", "PostToolUse", "PostToolUseFailure"}


def hook_command() -> str:
    # Percorsi con "/" e tra virgolette: funzionano sia in cmd sia in Git Bash,
    # che Claude Code usa su Windows per eseguire gli hook.
    return f'"{Path(sys.executable).as_posix()}" "{RELAY.as_posix()}"'


def is_ours(group: dict) -> bool:
    return any(MARKER in h.get("command", "") for h in group.get("hooks", []))


def updated(settings: dict, remove: bool) -> dict:
    hooks = settings.setdefault("hooks", {})
    for ev in EVENTS:
        # Togliamo sempre le nostre voci (così il comando è idempotente)
        groups = [g for g in hooks.get(ev, []) if not is_ours(g)]
        if not remove:
            group = {"hooks": [{"type": "command", "command": hook_command(), "timeout": 5}]}
            if ev in TOOL_EVENTS:
                group = {"matcher": "*", **group}
            groups.append(group)
        if groups:
            hooks[ev] = groups
        else:
            hooks.pop(ev, None)
    if not hooks:
        settings.pop("hooks")
    return settings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="scrive le modifiche")
    ap.add_argument("--remove", action="store_true", help="rimuove gli hook del monitor")
    args = ap.parse_args()

    current = json.loads(SETTINGS.read_text(encoding="utf-8")) if SETTINGS.exists() else {}
    new = updated(json.loads(json.dumps(current)), args.remove)  # copia profonda
    text = json.dumps(new, indent=2, ensure_ascii=False)

    if not (args.apply or args.remove):
        print(f"Anteprima di {SETTINGS} (nessuna modifica; usa --apply):\n")
        print(text)
        return

    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    if SETTINGS.exists():
        backup = SETTINGS.with_name(f"settings.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(SETTINGS, backup)
        print(f"Backup: {backup}")
    SETTINGS.write_text(text + "\n", encoding="utf-8")
    print("Hook rimossi." if args.remove else "Hook installati. Valgono per le nuove sessioni di Claude Code.")


if __name__ == "__main__":
    main()
