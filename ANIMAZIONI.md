# Repo di riferimento per le animazioni

Progetti della community sulla mascotte di Claude Code (Clawd) da cui sono
venute le **idee** per le animazioni del monitor. Nessun file è stato copiato:
gli sprite sono disegnati da zero in `src/make_sprites.py`.

| Repo | Cosa fa | Idee prese | Commit |
|---|---|---|---|
| [rullerzhou-afk/clawd-on-desk](https://github.com/rullerzhou-afk/clawd-on-desk) | pet desktop (Electron) che segue Claude Code, Codex, Cursor… | stati pensa/errore, FINITO che si guarda intorno, una mascotte per sessione | `eb690ad` |
| [BrianHuang813/clawd-actor](https://github.com/BrianHuang813/clawd-actor) | plugin Claude Code: Clawd recita il tool in uso sopra il prompt (26 scene) | costumi per tool (detective, pittore, cowboy, mago…) | `eb690ad` |
| [b-barri/clawd-touchbar](https://github.com/b-barri/clawd-touchbar) | Clawd sulla Touch Bar del Mac | risveglio con salto, scene di pausa, ombra a terra | `d152368` |
| [xixicc186/clawd-emotes-skill](https://github.com/xixicc186/clawd-emotes-skill) | skill con espressioni/emote di Clawd | feste per data con cappello e particelle | `d152368` |

L'icona (`icona.ico`, generata da `tool/make_icon.py`) usa la stessa mascotte
degli sprite: anche lì nessun file copiato.

Progetti simili, utili come spunto futuro:
- [Clawdmeter](https://techcrunch.com/2026/05/14/clawdmeter-turns-your-claude-code-usage-stats-into-a-tiny-desktop-dashboard/): dashboard ESP32-S3 con Clawd che accelera col consumo (vicino al nostro pannello vero).
- [Eyalm321/clawdpanel](https://github.com/Eyalm321/clawdpanel): HUD retro per Claude Code.
