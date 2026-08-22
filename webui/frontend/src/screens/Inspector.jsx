import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

const ROLE_STYLE = {
  writer: 'bg-accent/10 text-accent',
  judge: 'bg-fog-400/10 text-fog-300',
  review: 'bg-warn/10 text-warn',
}

function fmt(n) {
  return n == null ? '—' : n.toLocaleString()
}

function EventRow({ ev }) {
  const [open, setOpen] = useState(false)
  return (
    <li className="border-t border-ink-700 first:border-t-0">
      <button
        onClick={() => setOpen(!open)}
        className="grid w-full grid-cols-[7rem_5rem_1fr_1fr_5.5rem] items-center gap-4 px-4 py-3 text-left transition-colors hover:bg-ink-800"
      >
        <span className="font-mono text-xs text-fog-500">{ev.ts.slice(11, 19)}</span>
        <span className={`w-fit rounded px-1.5 py-0.5 font-mono text-xs ${ROLE_STYLE[ev.modelKey]}`}>
          {ev.modelKey}
        </span>
        <span className="font-mono text-sm text-fog-200">
          {ev.ok ? (
            <>↑ {fmt(ev.tokensIn)} · ↓ {fmt(ev.tokensOut)}</>
          ) : (
            <span className="text-bad">{ev.error}</span>
          )}
          {ev.attempt > 1 && (
            <span className="ml-2 rounded bg-warn/10 px-1 py-0.5 text-[10px] text-warn">
              retry {ev.attempt}
            </span>
          )}
        </span>
        <span className="font-mono text-xs text-fog-500">{(ev.durationMs / 1000).toFixed(1)}s</span>
        <span className={`font-mono text-xs text-right ${open ? 'text-fog-300' : 'text-fog-500'}`}>
          {open ? 'close' : 'prompt'}
        </span>
      </button>
      {open && (
        <div className="border-t border-ink-800 bg-ink-950 px-4 py-3">
          <p className="mb-2 font-mono text-[10px] uppercase tracking-wide text-fog-500">
            prompt head · {fmt(ev.promptChars)} chars sent
          </p>
          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-fog-300">
            {ev.promptHead}…
          </pre>
        </div>
      )}
    </li>
  )
}

export default function Inspector() {
  const [events, setEvents] = useState(null)
  const [live, setLive] = useState(false)

  useEffect(() => {
    api.listLlmEvents().then(setEvents)
  }, [])

  useEffect(() => {
    if (!live) return
    return api.subscribeLlmEvents('bells-second-son', (ev) =>
      setEvents((prev) => [...prev.slice(-99), ev]))
  }, [live])

  return (
    <div>
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-paper">LLM Inspector</h1>
        <button
          onClick={() => setLive(!live)}
          className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-transform active:scale-[0.98] ${
            live ? 'border-accent/40 bg-accent/10 text-accent' : 'border-ink-600 text-fog-400 hover:text-fog-200'
          }`}
        >
          {live && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />}
          {live ? 'Live' : 'Go live'}
        </button>
      </header>

      {!events ? (
        <ul className="rounded-xl border border-ink-700 bg-ink-900">
          {[0, 1, 2, 3].map((i) => (
            <li key={i} className="h-12 animate-pulse border-t border-ink-700 first:border-t-0 bg-ink-800"
              style={{ animationDelay: `${i * 120}ms` }} />
          ))}
        </ul>
      ) : (
        <ul className="overflow-hidden rounded-xl border border-ink-700 bg-ink-900">
          {[...events].reverse().map((ev, i) => (
            <EventRow key={`${ev.ts}-${i}`} ev={ev} />
          ))}
        </ul>
      )}
    </div>
  )
}
