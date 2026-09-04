import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client.js'

function Stars({ n }) {
  if (n == null) return null
  const full = Math.floor(n)
  const half = n - full >= 0.5
  return (
    <span className="text-accent">
      {'★'.repeat(full)}{half ? '½' : ''}{'☆'.repeat(5 - full - (half ? 1 : 0))}
    </span>
  )
}

/** First line of a markdown blob, for card teasers. */
const firstLine = (md) =>
  md.split('\n').find((l) => l.trim() && !l.startsWith('#'))?.trim() ?? ''

function CutCard({ cut }) {
  const isCut = cut.action === 'CUT'
  return (
    <div className="border border-ink-700 bg-ink-850 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="border border-ink-600 px-1.5 py-0.5 font-mono text-[10px] text-fog-400">
          [{cut.type.toLowerCase()}]
        </span>
        <button className={`border px-2 py-0.5 font-mono text-[10px] transition-colors ${
          isCut
            ? 'border-bad/40 text-bad hover:bg-bad/10'
            : 'border-good/40 text-good hover:bg-good/10'
        }`}>
          [{cut.action.toLowerCase()}]
        </button>
      </div>
      <p className="font-prose text-[13px] leading-relaxed text-fog-300">
        <span className={`line-through decoration-bad/50 ${isCut ? 'opacity-70' : ''}`}>
          “{cut.quote}”
        </span>
        {cut.rewrite && (
          <span className="mt-1 block not-italic text-good">→ {cut.rewrite}</span>
        )}
      </p>
      <p className="mt-2 font-mono text-[10px] leading-relaxed text-fog-500">reason: {cut.reason}</p>
    </div>
  )
}

export default function Revision() {
  const [rev, setRev] = useState(null)
  const [sel, setSel] = useState(0)

  useEffect(() => {
    api.getRevision().then(setRev)
  }, [])

  const brief = rev?.briefs[sel]
  const cuts = useMemo(() => {
    if (!brief || !rev) return []
    return rev.cuts[`ch_${String(brief.chapter).padStart(2, '0')}`] ?? []
  }, [brief, rev])

  if (!rev) {
    return (
      <div className="grid grid-cols-[16rem_1fr_20rem] gap-6">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-96 animate-pulse rounded-xl bg-ink-800" />
        ))}
      </div>
    )
  }

  const worst = rev.reviews.reduce(
    (w, r) => (r.stars != null && (w == null || r.stars < w) ? r.stars : w), null)

  return (
    <div className="-m-8 flex h-[calc(100vh-1px)]">
      {/* column 1 — cycles */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-ink-700 bg-ink-900">
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <p className="section-head mb-3">// revision_briefs</p>
          <ol className="relative space-y-1 border-l border-ink-600 pl-4">
            {rev.briefs.map((b, i) => (
              <li key={`${b.chapter}-${b.kind}`} className="relative">
                <button
                  onClick={() => setSel(i)}
                  className={`block w-full py-1.5 text-left transition-colors ${
                    i === sel ? 'text-accent' : 'text-fog-400 hover:text-fog-200'
                  }`}
                >
                  <span className={`absolute -left-[21px] top-3 h-1.5 w-1.5 rounded-full ${
                    i === sel ? 'bg-accent shadow-[0_0_6px_var(--color-accent)]' : 'bg-ink-600'
                  }`} />
                  <p className="font-mono text-xs">
                    {i === sel && '> '}ch_{String(b.chapter).padStart(2, '0')}{' '}
                    <span className="text-[10px] text-fog-500">[{b.kind}]</span>
                  </p>
                  <p className="truncate font-mono text-[10px] text-fog-500">{b.title}</p>
                </button>
              </li>
            ))}
          </ol>
        </div>

        <div className="max-h-64 shrink-0 overflow-y-auto border-t border-ink-700 p-4">
          <p className="section-head mb-3">// full_reviews</p>
          <ul className="space-y-3">
            {rev.reviews.map((r, i) => (
              <li key={i} className="border border-ink-700 bg-ink-850 p-2.5">
                <div className="flex items-center justify-between font-mono text-[10px] text-fog-500">
                  <span>{r.ts.slice(0, 8)}</span>
                  <Stars n={r.stars} />
                </div>
                <p className="mt-1 line-clamp-3 font-prose text-xs italic leading-relaxed text-fog-300">
                  “{firstLine(r.summary).replace(/\*\*/g, '')}”
                </p>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      {/* column 2 — brief */}
      <main className="min-w-0 flex-1 overflow-y-auto">
        {!brief ? (
          <p className="p-10 font-mono text-sm text-fog-500">[ no revision briefs on disk ]</p>
        ) : (
          <div className="mx-auto max-w-3xl p-8">
            <p className="font-mono text-xs text-fog-500">
              ch_{String(brief.chapter).padStart(2, '0')} <span className="opacity-50">//</span> revision_brief
              <span className="ml-3 text-[10px]">compiled from reader_panel × 4</span>
            </p>
            <h1 className="mt-1 font-display text-xl lowercase tracking-tight text-paper">{brief.title}</h1>

            <section className="mt-8">
              <p className="section-head mb-2"><span className="text-bad">!</span> problem_statement</p>
              <div className="border border-ink-700 bg-ink-900 p-4 font-mono text-xs leading-relaxed text-fog-300">
                <pre className="whitespace-pre-wrap font-mono">{brief.problem}</pre>
              </div>
            </section>

            {brief.keep && (
              <section className="mt-6">
                <p className="section-head mb-2 text-good">// what_to_keep</p>
                <blockquote className="border-l-2 border-good/50 bg-ink-900 p-4 font-prose text-sm leading-relaxed text-fog-200">
                  <pre className="whitespace-pre-wrap font-prose">{brief.keep}</pre>
                </blockquote>
              </section>
            )}

            {brief.directives && (
              <section className="mt-6">
                <p className="section-head mb-2">// execution_directives</p>
                <div className="border border-ink-700 bg-ink-900 p-4">
                  <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-fog-300">
                    {brief.directives}
                  </pre>
                </div>
              </section>
            )}
          </div>
        )}
      </main>

      {/* column 3 — adversarial cuts */}
      <aside className="flex w-80 shrink-0 flex-col border-l border-ink-700 bg-ink-900">
        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <p className="section-head mb-3">// adversarial_cuts</p>
          {cuts.length ? (
            <>
              <div className="mb-4">
                <div className="flex items-baseline justify-between font-mono text-xs">
                  <span className="text-fog-500">cut_ratio</span>
                  <span className="text-paper">
                    {cuts.length} marks · {cuts.filter((c) => c.action === 'CUT').length} cuts · {cuts.filter((c) => c.action === 'REWRITE').length} rewrites
                  </span>
                </div>
                <div className="mt-1.5 h-1 bg-ink-700">
                  <div
                    className="h-full bg-bad/70"
                    style={{ width: `${(cuts.filter((c) => c.action === 'CUT').length / cuts.length) * 100}%` }}
                  />
                </div>
              </div>
              <div className="space-y-3">
                {cuts.map((c, i) => <CutCard key={i} cut={c} />)}
              </div>
            </>
          ) : (
            <p className="font-mono text-xs text-fog-500">[ no cut log for this chapter ]</p>
          )}
        </div>
        <footer className="shrink-0 border-t border-ink-700 bg-ink-850 p-4">
          <p className="section-head mb-1">// one_sentence_verdict</p>
          <p className="font-prose text-sm italic leading-relaxed text-fog-200">
            {worst != null
              ? `hardest review pass: ${worst}★ of 5 — see // full_reviews for the takedown.`
              : 'no review verdicts on disk.'}
          </p>
        </footer>
      </aside>
    </div>
  )
}
