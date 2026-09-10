import { useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import { EmptyState, Skel } from '../../components/ui.jsx'

/**
 * Beats & Harvests (inspection tool): premise beats, chapter beat sheets,
 * and the global plot-thread ledger — nothing planted goes unpaid.
 */
export default function LedgerView({ project }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    document.title = `autonovel · ${project} · ledger`
    api.getLedger(project).then(setData).catch(() => {})
  }, [project])

  if (!data) return <Skel className="h-[60vh]" />
  if (!data.threads.length && !data.premiseBeats.length) {
    return (
      <EmptyState icon="⌘" title="no ledger on file">
        once the outline exists, every planted setup and its payoff chapter are tracked here — the promise sheet
        the pipeline holds itself to while drafting.
      </EmptyState>
    )
  }

  const TOTAL = Math.max(data.chaptersTotal ?? 0, ...data.threads.map((t) => t.harvest ?? t.planted ?? 0), 1)

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-8">
        <p className="section-head">nothing planted goes unpaid</p>
        <h1 className="mt-1 font-display text-2xl font-semibold lowercase tracking-tight text-paper">beats &amp; harvests</h1>
      </header>

      <div className="grid grid-cols-1 gap-10 xl:grid-cols-[1fr_1.4fr]">
        <section className="min-w-0">
          <h2 className="section-head mb-3">premise beats — chapter one</h2>
          {data.premiseBeats.length ? (
            <ol className="space-y-0">
              {data.premiseBeats.map((b, i) => (
                <li key={i} className={`flex items-baseline gap-3 border-l-2 py-2 pl-4 ${b.done ? 'border-accent' : 'border-ink-600'}`}>
                  <span className="font-mono text-xs text-fog-500">{String(i + 1).padStart(2, '0')}</span>
                  <span className={`text-sm lowercase ${b.done ? 'text-fog-200' : 'text-fog-500'}`}>
                    {b.label}
                    {!b.done && <span className="ml-2 font-mono text-[10px] text-accent">pending</span>}
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="font-mono text-xs text-fog-500">[ no premise beats on file ]</p>
          )}

          <h2 className="section-head mb-3 mt-8">chapter beat sheets</h2>
          {!data.roadmap.length && (
            <p className="font-mono text-xs text-fog-500">[ no beat sheets on file for this project ]</p>
          )}
          <div className="space-y-4">
            {data.roadmap.map((ch) => (
              <div key={ch.chapter} className="border border-line bg-ink-900 p-4">
                <p className="font-mono text-xs text-accent">ch {ch.chapter}</p>
                <p className="mt-0.5 font-prose text-base text-paper">{ch.title}</p>
                <ul className="mt-2 space-y-1">
                  {ch.beats.map((b, i) => (
                    <li key={i} className="flex gap-2 text-xs text-fog-300">
                      <span className="select-none text-fog-500">·</span>{b}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section className="min-w-0">
          <h2 className="section-head mb-3">
            global plot threads ledger — {data.threads.length} tracked ·{' '}
            {data.threads.filter((t) => t.status === 'paid off').length} paid ·{' '}
            {data.threads.filter((t) => t.status !== 'paid off').length} open
          </h2>
          <ul className="max-h-[480px] overflow-y-auto overflow-x-hidden border border-line bg-ink-850 px-4">
            {data.threads.map((t) => {
              const paid = t.status === 'paid off'
              const start = (t.planted ?? t.harvest ?? 1) - 1
              const end = paid ? t.harvest : TOTAL
              return (
                <li key={t.thread + start} className="border-t border-line py-3 first:border-t-0">
                  <div className="mb-1.5 flex items-baseline justify-between gap-4">
                    <p className="min-w-0 flex-1 truncate text-sm lowercase text-fog-200">
                      <span className={`mr-2 ${paid ? 'text-good' : 'text-accent'}`}>
                        [{paid ? 'paid' : 'open'}]
                      </span>
                      {t.thread}
                    </p>
                    <p className="shrink-0 font-mono text-[11px] text-fog-500">
                      {t.planted != null && <>planted ch{t.planted} → </>}
                      {paid ? `harvested ch${t.harvest}` : t.planted == null ? `recalled ch${t.harvest}` : 'open'}
                    </p>
                  </div>
                  <div className="relative h-1 bg-ink-800">
                    <div
                      className={`absolute h-full ${paid ? 'bg-good/60' : 'bg-accent-dim/70'}`}
                      style={{ left: `${(start / TOTAL) * 100}%`, width: `${((end - start) / TOTAL) * 100}%` }}
                    />
                    {t.planted != null && (
                      <span className="absolute top-1/2 h-2 w-2 -translate-y-1/2 bg-paper"
                        style={{ left: `calc(${(start / TOTAL) * 100}% - 4px)` }} />
                    )}
                    {paid && (
                      <span className="absolute top-1/2 h-2 w-2 -translate-y-1/2 rotate-45 border border-good bg-good"
                        style={{ left: `calc(${(end / TOTAL) * 100}% - 4px)` }} />
                    )}
                  </div>
                </li>
              )
            })}
            <li className="pb-1" aria-hidden="true" />
          </ul>
          <div className="mt-3 flex items-center gap-4 font-mono text-[10px] text-fog-500">
            <span>● plant</span>
            <span><span className="mr-1 inline-block h-2 w-2 rotate-45 border border-good bg-good align-middle" />harvest</span>
            <span><span className="mr-1 inline-block h-1 w-4 bg-accent-dim/70 align-middle" />open — payoff pending</span>
            <span className="ml-auto">{TOTAL} chapters</span>
          </div>
        </section>
      </div>
    </div>
  )
}
