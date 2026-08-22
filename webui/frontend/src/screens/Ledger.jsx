import data from '../fixtures/ledger.json'

const TOTAL = 24

function ThreadRow({ t }) {
  const paid = t.status === 'paid off'
  return (
    <li className="border-t border-ink-700 py-3 first:border-t-0">
      <div className="mb-1.5 flex items-baseline justify-between gap-4">
        <p className="text-sm text-fog-200 lowercase">
          {paid && <span className="mr-2 text-good">[paid]</span>}
          {t.thread}
        </p>
        <p className="shrink-0 font-mono text-[11px] text-fog-500">
          planted ch{t.planted} → harvested ch{t.harvest}
        </p>
      </div>
      <div className="relative h-1 rounded-full bg-ink-800">
        {/* full span */}
        <div
          className={`absolute h-full rounded-full ${paid ? 'bg-good/60' : 'bg-accent-dim'}`}
          style={{ left: `${((t.planted - 1) / TOTAL) * 100}%`, width: `${((t.harvest - t.planted + 1) / TOTAL) * 100}%` }}
        />
        <span className="absolute top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-paper"
          style={{ left: `calc(${((t.planted - 1) / TOTAL) * 100}% - 4px)` }} />
        <span className={`absolute top-1/2 h-2 w-2 -translate-y-1/2 rotate-45 border ${paid ? 'border-good bg-good' : 'border-accent bg-ink-950'}`}
          style={{ left: `calc(${(t.harvest / TOTAL) * 100}% - 4px)` }} />
      </div>
    </li>
  )
}

export default function Ledger() {
  return (
    <div>
      <header className="mb-8">
        <p className="section-head">03 · nothing planted goes unpaid</p>
        <h1 className="mt-1 font-display text-xl lowercase tracking-tight text-paper">
          beats &amp; harvests
        </h1>
      </header>

      <div className="grid grid-cols-1 gap-10 xl:grid-cols-[1fr_1.4fr]">
        <section>
          <h2 className="section-head mb-3">premise beats — chapter one</h2>
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

          <h2 className="section-head mb-3 mt-8">chapter beat sheets</h2>
          <div className="space-y-4">
            {data.roadmap.map((ch) => (
              <div key={ch.chapter} className="rounded-xl border border-ink-700 bg-ink-900 p-4">
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

        <section>
          <h2 className="section-head mb-3">global plot threads ledger</h2>
          <ul className="rounded-xl border border-ink-700 bg-ink-900 px-4">
            {data.threads.map((t) => (
              <ThreadRow key={t.thread} t={t} />
            ))}
          </ul>
          <div className="mt-3 flex items-center gap-4 font-mono text-[10px] text-fog-500">
            <span>● plant</span>
            <span><span className="mr-1 inline-block h-2 w-2 rotate-45 border border-accent align-middle" />harvest</span>
            <span><span className="mr-1 inline-block h-2 w-2 rotate-45 border border-good bg-good align-middle" />paid off</span>
            <span className="ml-auto">24 chapters</span>
          </div>
        </section>
      </div>
    </div>
  )
}
