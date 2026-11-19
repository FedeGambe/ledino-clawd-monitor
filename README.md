# Claude Monitor — simulatore del pannello

Mostra in una finestra cosa stanno facendo le sessioni di Claude Code
(VS Code, Antigravity, terminale): quante sono, chi lavora, chi ti aspetta,
e l'avanzamento della todo list. Emula tre display: TFT 320×240,
matrice LED 64×32, Pixoo 64×64.

## Cartella

```
.claude-plugin/    plugin.json + marketplace.json: il mod per Claude Code
hooks/register.ts  il mod: inoltra eventi, nome sessione, limiti d'uso, comandi in background
avvia.bat          avvio rapido su Windows (crea il venv la prima volta)
avvia.sh           avvio rapido su macOS / Linux
ANIMAZIONI.md      repo da cui vengono le idee per le animazioni
requirements.txt
sprites/           PNG della mascotte (generati)
src/
  monitor.py       finestra pygame + server HTTP locale (porta 8765)
  state.py         logica: aggrega gli eventi per sessione, calcola l'avanzamento
  render.py        disegno dei 3 profili e della mascotte
  demo.py          eventi finti per provare senza Claude Code
  tray.py          icona nella tray + popup (--tray)
  make_sprites.py  rigenera sprites/
```

## Installazione (Windows, macOS, Linux)

1. **Monitor**: clona il repo e avvia `avvia.bat` (Windows) o `./avvia.sh` (macOS/Linux).
   La prima volta crea il venv e installa le dipendenze. Serve Python 3.10+.
2. **Mod per Claude Code**: nel prompt di Claude Code scrivi

   ```
   /plugin install led-monitor --marketplace <owner>/<repo>
   ```

   rispondi `y` per aggiungere il marketplace e scegli lo scope utente.
   Vale per la sessione in corso e per tutte le successive.

Nessun percorso da configurare e niente da toccare in `settings.json`.
Se il monitor gira su un altro PC (o sul pannello vero), cambia l'opzione
`monitor_url` del mod da `/config` (default `http://127.0.0.1:8765/event`).
Se il monitor è chiuso, il mod non fa nulla: Claude Code non ne risente.

Per provare il mod da una copia locale senza installarlo:
`claude --plugin-dir <cartella del repo>`.

## Tre modi di vederlo

| Modo | Avvio | Cosa fa |
|---|---|---|
| finestra | `avvia.bat` | finestra normale, tasti 1/2/3 per i profili |
| tray | `avvia.bat --tray` | pallino del colore di stato nell'area di notifica; clic = mostra/nasconde un popup sempre in primo piano in basso a destra (layout TFT). `ESC` nasconde, si esce dal menu dell'icona (tasto destro) |
| pannello LED | da definire | il pannello leggerà `GET /state` oppure riceverà i frame 64×32 / 64×64 già disegnati |

La tray è provata su Windows; su macOS `pystray` vuole il thread principale, va ancora adattata.

## Prova senza Claude Code

`avvia.bat --demo` (o `./avvia.sh --demo`): eventi finti.
Accetta gli stessi argomenti di `src/monitor.py`.

Tasti: `1` TFT · `2` LED 64×32 · `3` Pixoo · `D` avvia/ferma demo · `ESC` esci.

## Stati

| Colore | Stato | Quando |
|---|---|---|
| arancio | LAVORA | dopo il tuo prompt e a ogni uso di tool |
| giallo | ATTENDE | richiesta di permesso (Notification) |
| verde | FINITO | ha terminato la risposta (Stop) |
| grigio | PAUSA | finito da più di 10 minuti |

La mascotte mostra lo stato più importante tra tutte le sessioni
(attende > lavora > finito > pausa).

Mascotte (`python src/make_sprites.py` rigenera `sprites/`):
- mentre lavora indossa un costume a seconda del tool: nuvoletta che pensa
  (nessun tool ancora), terminale (Bash), detective (Read/Grep), pittore
  (Edit/Write), cowboy (Agent), mago (MCP), giocoliere (todo), meteo (Web);
- un tool fallito la fa scuotere con gli occhi a X per 4 secondi
  (evento `PostToolUseFailure`);
- le altre sessioni attive compaiono come mini-mascotte del loro colore di stato (max 3).
- in FINITO festeggia per 10 s, poi passeggia con la spunta verde sopra la testa;
- ATTENDE scatta anche quando Claude ti fa una domanda (`AskUserQuestion`) o propone un piano (`ExitPlanMode`);
- a ogni nuova sessione fa un doppio salto di benvenuto;
- in PAUSA alterna una scena ogni 20 s (caffè, passeggiata, cuffie, libro, chitarra) e dopo 30 min si addormenta;
  la passeggiata va avanti e indietro su Pixoo e TFT, sul LED 64x32 cammina sul posto;
- feste automatiche per data (Natale, Capodanno, Halloween, San Valentino): cappello e
  neve/fuochi/fantasmini/cuori. Per provarle: `python src/monitor.py --festa christmas`
  (`--festa off` le spegne).

**Limiti d'uso**: in fondo compaiono sessione (5h) e settimana (7g). La tacca bianca
segna il tempo trascorso della finestra (il "ritmo giusto"): barra verde se sei sotto la tacca,
gialla fino a 15 punti sopra, rossa oltre (stai consumando troppo in fretta); sul TFT con percentuale e ora di reset, su LED/Pixoo come
due barrette nell'ultima riga. Li invia il mod (evento `session.measure`), come
`{"hook_event_name": "RateLimits", "rate_limits": [...]}` su `/event`.
I limiti sono dell'account, quindi includono anche l'uso in claude.ai, ma si
aggiornano solo quando Claude Code fa una richiesta. Con una API key (senza
abbonamento) non ci sono e la riga resta vuota.

**Nome sessione**: sul TFT ogni card mostra `progetto · nome sessione`
(il titolo automatico o quello di `/rename`), dal prompt successivo.

**Comandi in background**: se Claude ha finito di rispondere ma un comando lanciato in
background (Bash/PowerShell, anche con ctrl+b) gira ancora, la sessione resta LAVORA con
il costume terminale finché il comando non termina (evento `Background` con `count`).

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

- Il mod gira dentro Claude Code: nessun processo avviato a ogni evento.
- Aggiornamento da una versione con `hook_relay.py`: togli prima i vecchi hook
  del monitor da `~/.claude/settings.json` (le voci che contengono `hook_relay.py`),
  altrimenti ogni evento arriva due volte.
- Il server ascolta solo su `127.0.0.1`.
