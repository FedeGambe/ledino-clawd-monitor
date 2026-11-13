# Claude Monitor — simulatore del pannello

Mostra in una finestra cosa stanno facendo le sessioni di Claude Code
(VS Code, Antigravity, terminale): quante sono, chi lavora, chi ti aspetta,
e l'avanzamento della todo list. Emula tre display: TFT 320×240,
matrice LED 64×32, Pixoo 64×64.

## File

| File | Ruolo |
|---|---|
| `monitor.py` | finestra pygame + server HTTP locale (porta 8765) |
| `state.py` | logica: aggrega gli eventi per sessione, calcola l'avanzamento |
| `render.py` | disegno dei 3 profili e della mascotte segnaposto |
| `hook_relay.py` | lo script che Claude Code lancia a ogni evento |
| `install_hooks.py` | aggiunge/rimuove gli hook in `~/.claude/settings.json` |
| `demo.py` | eventi finti per provare senza Claude Code |

## 1. Prova senza Claude Code

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python monitor.py --demo
```

Tasti: `1` TFT · `2` LED 64×32 · `3` Pixoo · `D` avvia/ferma demo · `ESC` esci.

## 2. Collegarlo a Claude Code

Con il venv attivo (così gli hook usano lo stesso Python):

```powershell
python install_hooks.py           # anteprima, non modifica nulla
python install_hooks.py --apply   # scrive settings.json (con backup)
```

Poi lascia aperto `python monitor.py` e apri **nuove** sessioni di Claude Code:
gli hook vengono letti all'avvio della sessione. Per toglierli:
`python install_hooks.py --remove`.

Se il monitor è chiuso, gli hook escono in silenzio: Claude Code non ne risente.

## Stati

| Colore | Stato | Quando |
|---|---|---|
| arancio | LAVORA | dopo il tuo prompt e a ogni uso di tool |
| giallo | ATTENDE | richiesta di permesso (Notification) |
| verde | FINITO | ha terminato la risposta (Stop) |
| grigio | PAUSA | finito da più di 10 minuti |

La mascotte mostra lo stato più importante tra tutte le sessioni
(attende > lavora > finito > pausa).

Mascotte (`python make_sprites.py` rigenera `sprites/`):
- mentre lavora indossa un costume a seconda del tool: nuvoletta che pensa
  (nessun tool ancora), terminale (Bash), detective (Read/Grep), pittore
  (Edit/Write), cowboy (Agent), mago (MCP), giocoliere (todo), meteo (Web);
- un tool fallito la fa scuotere con gli occhi a X per 4 secondi
  (serve l'hook `PostToolUseFailure`: rilancia `install_hooks.py --apply`);
- le altre sessioni attive compaiono come mini-mascotte del loro colore di stato (max 3).
- ATTENDE scatta anche quando Claude ti fa una domanda (`AskUserQuestion`) o propone un piano (`ExitPlanMode`);
- a ogni nuova sessione fa un doppio salto di benvenuto;
- in PAUSA alterna una scena ogni 20 s (caffè, passeggiata, cuffie, libro, chitarra) e dopo 30 min si addormenta;
  la passeggiata va avanti e indietro su Pixoo e TFT, sul LED 64x32 cammina sul posto;
- feste automatiche per data (Natale, Capodanno, Halloween, San Valentino): cappello e
  neve/fuochi/fantasmini/cuori. Per provarle: `python monitor.py --festa christmas`
  (`--festa off` le spegne).

**Avanzamento**: deriva dalla todo list interna di Claude Code
(`TodoWrite` o `TaskCreate`/`TaskUpdate`, a seconda della versione).
Sulle richieste brevi senza todo list la barra scorre e basta.

## Mascotte personalizzata

Metti dei PNG nella cartella `sprites/` con nomi
`working_0.png`, `working_1.png`, `waiting_0.png`, `done_0.png`, `idle_0.png`, …
(qualsiasi dimensione, meglio pixel art quadrata). Ogni stato può avere
più frame. Se mancano, si usa il robottino segnaposto.

## Verso il pannello vero

`GET http://127.0.0.1:8765/state` restituisce lo stato in JSON:
è quello che il pannello (ESP32 via seriale o Wi-Fi) dovrà ricevere.

## Note

- Ogni hook avvia un processo Python (~50–100 ms su Windows) a ogni uso
  di tool. Se ti sembra pesante, si possono togliere `PreToolUse` e
  `PostToolUse` per tool diversi dalla todo list (perdi il nome del tool
  corrente).
- Il server ascolta solo su `127.0.0.1`.
