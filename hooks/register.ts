import type { EngineInterface, Register } from 'claude-code'

// Mod del Claude Monitor: al posto dei vecchi hook in settings.json (hook_relay.py).
// Inoltra al monitor gli eventi hook di Claude Code (lo stesso JSON che gli
// hook ricevono su stdin, filtrato), i limiti d'uso e i comandi in background.

// Campi che servono davvero: niente input/output voluminosi dei tool
const KEEP = ['session_id', 'cwd', 'hook_event_name', 'tool_name', 'message',
  'notification_type', 'session_title']
// Input e risposta servono solo per i tool della todo list
const TODO_TOOLS = ['TodoWrite', 'TaskCreate', 'TaskUpdate']

// Indirizzo del monitor: opzione `monitor_url` del mod (/config)
let monitorUrl = 'http://127.0.0.1:8765/event'

// Comandi in background ancora vivi in questa sessione.
// ponytail: in memoria del modulo, un reload del mod li azzera
// (il monitor torna a FINITO finché non ne parte un altro); $.state se serve.
const running = new Set<string>()

function post($: EngineInterface, body: object): void {
  $.http
    .fetch(monitorUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    .catch(() => {}) // monitor spento: nessun problema
}

function forward($: EngineInterface, e: object): void {
  const ev = e as Record<string, unknown>
  const payload: Record<string, unknown> = {}
  for (const k of KEEP) if (ev[k] !== undefined) payload[k] = ev[k]
  if (TODO_TOOLS.includes(String(ev.tool_name))) {
    payload.tool_input = ev.tool_input
    payload.tool_response = ev.tool_response
  }
  post($, payload)
}

async function sendBackground($: EngineInterface): Promise<void> {
  post($, { hook_event_name: 'Background', session_id: await $.session.id(), count: running.size })
}

export const register: Register = (on, options) => {
  if (options.monitor_url) monitorUrl = String(options.monitor_url)

  // Eventi che il monitor sa leggere (src/state.py); on() vuole nomi letterali
  on('classic.SessionStart', ($, e, next) => (forward($, e), next(e)))
  on('classic.UserPromptSubmit', ($, e, next) => (forward($, e), next(e)))
  on('classic.PreToolUse', ($, e, next) => (forward($, e), next(e)))
  on('classic.PostToolUse', ($, e, next) => (forward($, e), next(e)))
  on('classic.PostToolUseFailure', ($, e, next) => (forward($, e), next(e)))
  on('classic.Notification', ($, e, next) => (forward($, e), next(e)))
  on('classic.Stop', ($, e, next) => (forward($, e), next(e)))
  on('classic.SessionEnd', ($, e, next) => (forward($, e), next(e)))

  // Limiti d'uso: dopo ogni turno e quando una finestra si sposta di un punto.
  // ponytail: invia a ogni misura (non solo su `changed`), così un monitor
  // aperto dopo la sessione riceve i valori al turno successivo.
  on('session.measure', ($, e, next) => {
    if (e.rateLimits.length) post($, { hook_event_name: 'RateLimits', rate_limits: e.rateLimits })
    return next(e)
  })

  // Un comando parte in background (run_in_background o ctrl+b): lo contiamo.
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const ran = await next(e)
    const id = ran.deny === undefined && !ran.isError ? ran.result.backgroundTaskId : undefined
    if (id) {
      running.add(id)
      await sendBackground($)
    }
    return ran
  })

  on('tool.call', { tool: 'PowerShell' }, async ($, e, next) => {
    const ran = await next(e)
    const id = ran.deny === undefined && !ran.isError ? ran.result.backgroundTaskId : undefined
    if (id) {
      running.add(id)
      await sendBackground($)
    }
    return ran
  })

  // Claude ferma un comando in background.
  on('tool.call', { tool: 'TaskStop' }, async ($, e, next) => {
    const ran = await next(e)
    const id = e.task_id ?? e.shell_id
    if (id && running.delete(id)) await sendBackground($)
    return ran
  })

  // Il comando è finito: arriva la notifica <task-notification> con il suo id.
  on('session.receive', { origin: { kind: 'task-notification' } }, async ($, e, next) => {
    const id = /<task-id>([^<]+)<\/task-id>/.exec(e.text)?.[1]
    const ended = /<status>(completed|failed|killed)<\/status>/.test(e.text)
    if (id && ended && running.delete(id)) await sendBackground($)
    return next(e)
  })
}
