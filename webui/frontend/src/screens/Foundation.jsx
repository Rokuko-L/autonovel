import { useEffect, useState } from 'react'
import data from '../fixtures/foundation.json'

const DOCS = ['world', 'characters', 'canon']

const KIND_COLOR = {
  character: 'var(--color-accent)',
  location: 'var(--color-fog-300)',
  faction: 'var(--color-fog-500)',
}

function EntityGraph({ nodes, edges }) {
  const [hover, setHover] = useState(null)
  const pos = Object.fromEntries(nodes.map((n) => [n.id, n]))
  const connected = (id) =>
    hover === null ||
    hover === id ||
    edges.some((e) => (e.from === hover && e.to === id) || (e.to === hover && e.from === id))

  return (
    <div className="relative overflow-hidden rounded-xl border border-ink-700 bg-ink-950">
      <svg viewBox="0 0 100 100" className="aspect-[10/6] w-full" preserveAspectRatio="none">
        {edges.map((e, i) => {
          const a = pos[e.from]
          const b = pos[e.to]
          if (!a || !b) return null
          const lit =
            hover !== null && (e.from === hover || e.to === hover)
          return (
            <g key={i}>
              <line
                x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke={lit ? 'var(--color-accent)' : 'var(--color-ink-600)'}
                strokeWidth={lit ? 0.35 : 0.2}
              />
              {lit && (
                <text
                  x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 0.8}
                  textAnchor="middle" fontSize="2"
                  fill="var(--color-accent)"
                >
                  {e.label}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      {/* HTML nodes over the SVG so labels stay crisp */}
      {nodes.map((n) => (
        <button
          key={n.id}
          onMouseEnter={() => setHover(n.id)}
          onMouseLeave={() => setHover(null)}
          className={`absolute -translate-x-1/2 -translate-y-1/2 rounded-md border px-2 py-1 text-left transition-opacity ${
            connected(n.id) ? 'opacity-100' : 'opacity-25'
          } ${hover === n.id ? 'border-accent bg-ink-800' : 'border-ink-600 bg-ink-900'}`}
          style={{ left: `${n.x}%`, top: `${n.y}%` }}
        >
          <span className="flex items-center gap-1.5 text-xs text-paper">
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ background: KIND_COLOR[n.kind] }}
            />
            {n.label}
          </span>
          {n.status && (
            <span className={`font-mono text-[10px] ${n.status.includes('DEAD') || n.status.includes('dead') ? 'text-bad' : 'text-fog-500'}`}>
              [{n.status}]
            </span>
          )}
        </button>
      ))}
      <p className="absolute bottom-3 right-4 font-mono text-[10px] text-fog-500">
        hover a node to trace its debts
      </p>
    </div>
  )
}

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
