import { useEffect, useState } from 'react'
import data from '../fixtures/foundation.json'

const DOCS = ['world', 'characters', 'canon']

import EntityGraph from '../components/EntityGraph.jsx'

export default function Foundation() {
  const [doc, setDoc] = useState('characters')
  const [view, setView] = useState('graph')

  return (
    <div>
      <header className="mb-6 flex items-end justify-between">
        <div>
          <p className="section-head">02 · what the machine believes</p>
          <h1 className="mt-1 font-display text-xl lowercase tracking-tight text-paper">
            foundation — the second son of the house of bells
          </h1>
          <p className="mt-1 font-mono text-xs text-fog-500">
            score 7.6 · lore 7.2 · frozen at iter 8 — readable even after export
          </p>
        </div>
        <div className="flex gap-1">
          {['graph', ...DOCS].map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`rounded-md px-3 py-1.5 text-xs lowercase transition-colors ${
                view === v ? 'bg-accent/15 text-accent' : 'text-fog-400 hover:text-fog-200'
              }`}
            >
              {v === 'graph' ? '[ entity graph ]' : v}
            </button>
          ))}
        </div>
      </header>

      {view === 'graph' ? (
        <>
          <EntityGraph {...data.entities} />
          <div className="mt-4 flex gap-5 font-mono text-[11px] text-fog-400">
            <span><span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-accent align-middle" />character</span>
            <span><span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-fog-300 align-middle" />location</span>
            <span><span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-fog-500 align-middle" />faction</span>
          </div>
        </>
      ) : (
        <article className="max-w-[70ch] whitespace-pre-wrap rounded-xl border border-ink-700 bg-ink-900 p-6 font-prose text-[15px] leading-relaxed text-fog-200">
          {data.docs[view]}
        </article>
      )}
    </div>
  )
}
