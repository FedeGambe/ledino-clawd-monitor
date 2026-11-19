#!/bin/sh
# Avvio rapido del Claude Monitor (macOS / Linux).
#   ./avvia.sh            monitor collegato al mod
#   ./avvia.sh --demo     eventi finti
#   ./avvia.sh --festa christmas
cd "$(dirname "$0")" || exit 1

if [ ! -x .venv/bin/python ]; then
    echo "Prima volta: creo il venv e installo le dipendenze..."
    python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt || exit 1
fi

exec .venv/bin/python src/monitor.py "$@"
