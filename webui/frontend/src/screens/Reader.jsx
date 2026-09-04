import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client.js'

function ScoreDonut({ score }) {
  const pct = Math.max(0, Math.min(1, (score ?? 0) / 10))
  const c = 2 * Math.PI * 15
  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 36 36" className="h-16 w-16 -rotate-90">
        <circle cx="18" cy="18" r="15" fill="none" stroke="var(--color-ink-600)" strokeWidth="3" />
        <circle
          cx="18" cy="18" r="15" fill="none"
          stroke={pct >= 0.65 ? 'var(--color-accent)' : 'var(--color-bad)'}
          strokeWidth="3" strokeDasharray={`${pct * c} ${c}`} strokeLinecap="butt"
        />
      </svg>
      <div>
        <p className="font-display text-2xl text-paper">{score != null ? score.toFixed(2) : '—'}</p>
        <p className="font-mono text-[10px] text-fog-500">
          {score != null ? (score >= 6.5 ? 'gate: pass' : 'gate: fail') : 'no kept attempt'}
        </p>
      </div>
    </div>
  )
}

function Panel({ label, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <section className="border-b border-ink-700 last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-ink-900"
      >
        <span className="section-head">{label}</span>
        <span className={`text-[10px] text-fog-500 transition-transform ${open ? '' : '-rotate-90'}`}>▾</span>
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </section>
  )
}

export default function Reader() {
  const [chapters, setChapters] = useState(null)
  const [evals, setEvals] = useState({})
  const [sel, setSel] = useState(0)

  useEffect(() => {
    api.listChapters().then((cs) => {
      setChapters(cs)
      const first = cs.findIndex((c) => c.status === 'kept')
      setSel(first >= 0 ? first : 0)
    })
  }, [])

  const ch = chapters?.[sel]
  useEffect(() => {
    if (!ch) return
    let stale = false
    api.getEvals('sir-the-confortable-v3', ch.id).then((a) => {
      if (!stale) setEvals((prev) => ({ ...prev, [ch.id]: a }))
    })
    return () => { stale = true }
  }, [ch?.id])

  const attempt = useMemo(() => {
    if (!ch) return null
    const list = evals[ch.id]
    return list?.length ? list[list.length - 1] : null
  }, [ch?.id, evals])

  if (!chapters) {
    return (
      <div className="grid grid-cols-[12rem_1fr_18rem] gap-6">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-96 animate-pulse rounded-xl bg-ink-800" />
        ))}
      </div>
    )
  }

  const go = (d) => setSel((s) => Math.max(0, Math.min(chapters.length - 1, s + d)))
  const [heading, ...rest] = ch.prose.split('\n')
  const paras = rest.join('\n').split(/\n\s*\n/).filter((p) => p.trim())

  return (
    <div className="-m-8 flex h-[calc(100vh-1px)] flex-col">
      {/* control bar */}
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-ink-700 px-5">
        <p className="font-mono text-xs text-fog-400">
          <span className="text-accent">[06]</span> manuscript // prose_reader
        </p>
        <div className="flex items-center gap-2">
          <button onClick={() => go(-1)} disabled={sel === 0}
            className="border border-ink-600 px-3 py-1 font-mono text-xs text-fog-400 transition-colors hover:border-accent/50 hover:text-accent disabled:opacity-40">
            ‹ prev
          </button>
          <button onClick={() => go(1)} disabled={sel === chapters.length - 1}
            className="border border-ink-600 px-3 py-1 font-mono text-xs text-fog-400 transition-colors hover:border-accent/50 hover:text-accent disabled:opacity-40">
            next ›
          </button>
          <span className="mx-1 h-4 w-px bg-ink-600" />
          <button className="border border-ink-600 px-3 py-1 font-mono text-xs text-fog-400 transition-colors hover:border-accent/50 hover:text-accent">
            [export pdf]
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* chapter rail */}
        <nav className="w-52 shrink-0 overflow-y-auto border-r border-ink-700 bg-ink-900 py-2">
          <p className="section-head px-4 pb-2">// chapters</p>
          <ul>
            {chapters.map((c, i) => (
              <li key={c.id}>
                <button
                  onClick={() => setSel(i)}
                  className={`flex w-full items-center gap-2 px-4 py-1.5 text-left font-mono text-xs transition-colors ${
                    i === sel
                      ? 'border-r-2 border-accent bg-ink-800 text-accent'
                      : 'text-fog-400 hover:text-fog-200'
                  }`}
                >
                  {i === sel && <span className="text-accent">&gt;</span>}
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                    c.status === 'kept' ? 'bg-good' : c.status === 'discarded' ? 'bg-bad' : 'border border-fog-500'
                  }`} />
                  <span className="flex-1">{c.id}</span>
                  <span className="text-[10px] text-fog-500">{(c.words / 1000).toFixed(1)}k</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* prose */}
        <article className="min-w-0 flex-1 overflow-y-auto">
          <div className="mx-auto max-w-prose px-10 py-10">
            <p className="font-mono text-xs text-fog-500">
              {ch.id} <span className="opacity-50">//</span> {ch.title}
            </p>
            <div className="mt-2 flex flex-wrap gap-2 font-mono text-[10px] text-fog-400">
              <span className="border border-ink-600 px-1.5 py-0.5">[status: {ch.status}]</span>
              <span className="border border-ink-600 px-1.5 py-0.5">[words: {ch.words.toLocaleString()}]</span>
              {ch.score != null && (
                <span className="border border-accent/40 px-1.5 py-0.5 text-accent">[score: {ch.score.toFixed(2)}]</span>
              )}
              {ch.attempts.length > 1 && (
                <span className="border border-ink-600 px-1.5 py-0.5">[attempts: {ch.attempts.length}]</span>
              )}
            </div>
            <div className="mt-8 space-y-5 font-prose text-[17px] leading-[1.75] text-fog-200">
              {paras.map((p, i) => (
                <p key={i} className="whitespace-pre-wrap">{p.trim()}</p>
              ))}
            </div>
            <div className="mt-12 flex justify-between border-t border-ink-700 pt-4 font-mono text-[10px] text-fog-500">
              <button onClick={() => go(-1)} disabled={sel === 0} className="hover:text-accent disabled:opacity-40">
                ‹ {chapters[sel - 1]?.id ?? 'start'}
              </button>
              <span>[ end_of_chapter ]</span>
              <button onClick={() => go(1)} disabled={sel === chapters.length - 1} className="hover:text-accent disabled:opacity-40">
                {chapters[sel + 1]?.id ?? 'end'} ›
              </button>
            </div>
          </div>
        </article>

        {/* analysis rail */}
        <aside className="w-72 shrink-0 overflow-y-auto border-l border-ink-700 bg-ink-900">
          <Panel label="// chapter_score">
            <ScoreDonut score={ch.score} />
            {attempt && (
              <div className="mt-3 space-y-1.5">
                {Object.entries(attempt.dims).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-2 font-mono text-[10px]">
                    <span className="w-28 truncate text-fog-500">{k.replace(/_/g, ' ')}</span>
                    <div className="h-1 flex-1 bg-ink-700">
                      <div className="h-full bg-accent/70" style={{ width: `${(v.score ?? 0) * 10}%` }} />
                    </div>
                    <span className="w-7 text-right text-fog-300">{v.score?.toFixed(1)}</span>
                  </div>
                ))}
              </div>
            )}
          </Panel>

          <Panel label={`// attempts (${ch.attempts.length})`}>
            <ul className="space-y-1 font-mono text-xs">
              {ch.attempts.map((a, i) => (
                <li key={i} className="flex items-center justify-between">
                  <span className="text-fog-500">attempt {i + 1}</span>
                  <span className="flex items-center gap-2">
                    <span className="text-fog-300">{a.score.toFixed(2)}</span>
                    <span className={`border px-1 text-[10px] ${
                      a.status === 'keep' ? 'border-good/40 text-good' : 'border-bad/40 text-bad'
                    }`}>
                      [{a.status}]
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </Panel>

          {attempt && (
            <Panel label="// eval_notes" defaultOpen={false}>
              <p className="font-mono text-[10px] uppercase tracking-wide text-fog-500">
                weakest · {attempt.weakest.split('(')[0]}
              </p>
              <ul className="mt-2 space-y-2">
                {attempt.topRevisions.map((r, i) => (
                  <li key={i} className="flex gap-2 text-xs leading-relaxed text-fog-300">
                    <span className="font-display text-accent">0{i + 1}</span>
                    {r}
                  </li>
                ))}
              </ul>
            </Panel>
          )}

          {attempt && (
            <Panel label="// canon_delta">
              <div className="flex gap-2 font-mono text-[10px]">
                <span className="border border-good/40 px-1.5 py-0.5 text-good">[new_canon: {attempt.newCanon}]</span>
                <span className="border border-bad/40 px-1.5 py-0.5 text-bad">[unexplained: {attempt.unexplained}]</span>
              </div>
            </Panel>
          )}
        </aside>
      </div>
    </div>
  )
}
