import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

const PHASE_STYLE = {
  foundation: 'text-paper',
  drafting: 'text-accent',
  revision: 'text-good',
  export: 'text-fog-300',
  idle: 'text-fog-500',
}

function Row({ p, onOpen }) {
  return (
    <li className="border-t border-ink-700 first:border-t-0">
      <button
        onClick={() => onOpen(p)}
        className="group flex w-full items-center gap-6 px-4 py-5 text-left transition-colors hover:bg-ink-900"
      >
        <span className={`font-mono text-xs ${PHASE_STYLE[p.phase]}`}>
          {p.running ? <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent align-middle" /> : null}
          [{p.phase}]
        </span>

        <div className="min-w-0 flex-1">
          <p className="truncate font-prose text-lg leading-snug text-paper">
            {p.title === 'Untitled' ? <span className="text-fog-500">untitled</span> : p.title}
          </p>
          <p className="mt-0.5 font-mono text-[11px] text-fog-500">{p.name}</p>
        </div>

        <div className="hidden shrink-0 items-baseline gap-8 text-right font-mono text-sm md:flex">
          <div>
            <p className="text-[10px] uppercase tracking-wide text-fog-500">score</p>
            <p className={p.foundationScore >= 7.5 ? 'text-good' : 'text-fog-200'}>
              {p.foundationScore ? p.foundationScore.toFixed(1) : '—'}
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide text-fog-500">words</p>
            <p className="text-fog-200">{p.words.toLocaleString()}</p>
          </div>
          <div className="w-24">
            <p className="text-[10px] uppercase tracking-wide text-fog-500">chapters</p>
            <p className="text-fog-200">
              {p.chaptersDone}/{p.chaptersTotal || '—'}
            </p>
          </div>
        </div>

        <span className="shrink-0 font-mono text-xs text-fog-500 transition-colors group-hover:text-accent">
          open ›
        </span>
      </button>
    </li>
  )
}

export default function Projects() {
  const [projects, setProjects] = useState(null)

  useEffect(() => {
    api.listProjects().then(setProjects)
  }, [])

  return (
    <div>
      <header className="mb-6 flex items-end justify-between">
        <div>
          <p className="section-head">01 · your shelf</p>
          <h1 className="mt-1 font-display text-xl lowercase tracking-tight text-paper">projects</h1>
        </div>
        <button className="rounded-lg border border-accent/50 px-4 py-2 text-xs lowercase text-accent transition-transform hover:bg-accent/10 active:scale-[0.98]">
          + new novel
        </button>
      </header>

      {!projects ? (
        <ul className="rounded-xl border border-ink-700">
          {[0, 1, 2].map((i) => (
            <li key={i} className="h-20 animate-pulse border-t border-ink-700 bg-ink-900 first:border-t-0"
              style={{ animationDelay: `${i * 120}ms` }} />
          ))}
        </ul>
      ) : (
        <ul className="overflow-hidden rounded-xl border border-ink-700 bg-ink-850">
          {projects.map((p) => (
            <Row key={p.name} p={p} onOpen={() => {}} />
          ))}
        </ul>
      )}
    </div>
  )
}
