import { useMemo, useState } from 'react'
import data from '../fixtures/foundation.json'
import EntityGraph from '../components/EntityGraph.jsx'

const TABS = [
  { id: 'graph', label: 'entity_graph' },
  { id: 'world', label: 'world_bible' },
  { id: 'characters', label: 'characters' },
  { id: 'canon', label: 'canon' },
  { id: 'voice', label: 'voice' },
]

export default function Foundation() {
  const [tab, setTab] = useState('graph')
  const [sel, setSel] = useState(null)

  const { nodes, edges } = data.entities
  const neighbours = useMemo(() => {
    if (!sel) return []
    return edges
      .filter((e) => e.from === sel.id || e.to === sel.id)
      .map((e) => {
        const otherId = e.from === sel.id ? e.to : e.from
        const other = nodes.find((n) => n.id === otherId)
        return other ? { ...other, rel: e.label } : null
      })
      .filter(Boolean)
  }, [sel, nodes, edges])

  return (
    <div className="-m-8 flex h-[calc(100vh-1px)]">
      {/* graph / docs area */}
      <main className="flex min-w-0 flex-1 flex-col p-6">
        <header className="mb-4 flex items-end justify-between">
          <div>
            <p className="section-head">02 · what the machine believes</p>
            <h1 className="mt-1 font-display text-xl lowercase tracking-tight text-paper">
              foundation — {data.meta.title.toLowerCase()}
            </h1>
            <p className="mt-1 font-mono text-xs text-fog-500">
              score {data.meta.score} · lore {data.meta.lore} · {data.meta.chaptersTotal} chapters · phase {data.meta.phase}
            </p>
          </div>
        </header>

        <div className="relative min-h-0 flex-1">
          {tab === 'graph' ? (
            <div className="flex h-full flex-col">
              <div className="pointer-events-none absolute left-6 top-6 z-10 flex items-center gap-6 rounded-lg border border-ink-700 bg-ink-950/80 px-4 py-2 font-mono text-xs backdrop-blur">
                <span className="text-fog-300"><span className="mr-1.5 text-accent">◉</span>nodes: {nodes.length}</span>
                <span className="text-fog-300"><span className="mr-1.5 text-accent">─</span>edges: {edges.length}</span>
              </div>
              <EntityGraph
                nodes={nodes}
                edges={edges}
                onSelect={(d) => setSel(d)}
                className="h-full min-h-[420px] flex-1"
              />
            </div>
          ) : (
            <article className="h-full overflow-y-auto whitespace-pre-wrap rounded-xl border border-ink-700 bg-ink-900 p-6 font-prose text-[15px] leading-relaxed text-fog-200">
              {data.docs[tab]}
            </article>
          )}
        </div>

        {/* bottom tab bar */}
        <nav className="mt-3 flex h-10 shrink-0 items-center gap-1">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`h-full border px-4 font-mono text-xs transition-colors ${
                tab === id
                  ? 'border-accent/50 bg-accent/10 text-accent'
                  : 'border-ink-700 text-fog-400 hover:text-fog-200'
              }`}
            >
              [{label}]
            </button>
          ))}
        </nav>
      </main>

      {/* entity inspector */}
      <aside className="flex w-80 shrink-0 flex-col border-l border-ink-700 bg-ink-900">
        {!sel ? (
          <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
            <p className="font-mono text-xs text-fog-500">entity_inspector</p>
            <p className="mt-2 font-mono text-[11px] leading-relaxed text-fog-500">
              [ click a node to inspect ]
            </p>
          </div>
        ) : (
          <>
            <header className="border-b border-ink-700 p-5">
              <p className="section-head">entity_inspector</p>
              <div className="mt-1 flex items-center justify-between gap-2">
                <h2 className="truncate font-display text-lg text-paper">{sel.label}</h2>
                <span className="shrink-0 border border-accent/50 px-1.5 py-0.5 font-mono text-[10px] text-accent">
                  {sel.kind}
                </span>
              </div>
              {sel.status && <p className="mt-1 font-mono text-[10px] text-bad">status: {sel.status}</p>}
            </header>

            <div className="min-h-0 flex-1 overflow-y-auto p-5">
              {sel.desc && (
                <section className="mb-5">
                  <p className="mb-1.5 font-mono text-[10px] uppercase tracking-widest text-fog-500">description</p>
                  <p className="font-prose text-[13px] leading-relaxed text-fog-200">{sel.desc}</p>
                </section>
              )}

              {sel.mentions?.length > 0 && (
                <section className="mb-5">
                  <p className="mb-1.5 font-mono text-[10px] uppercase tracking-widest text-fog-500">mentioned_in</p>
                  <div className="flex flex-wrap gap-1.5">
                    {sel.mentions.map((c) => (
                      <span key={c} className="border border-ink-600 px-1.5 py-0.5 font-mono text-[10px] text-fog-400">
                        {c}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {neighbours.length > 0 && (
                <section className="mb-5">
                  <p className="mb-1.5 font-mono text-[10px] uppercase tracking-widest text-fog-500">
                    relationships ({neighbours.length})
                  </p>
                  <ul>
                    {neighbours.map((n) => (
                      <li key={n.id}>
                        <button
                          onClick={() => setSel(n)}
                          className="flex w-full items-center gap-2 py-1 text-left hover:text-accent"
                        >
                          <span className={`h-1.5 w-1.5 rounded-full ${
                            n.kind === 'character' ? 'bg-accent' : n.kind === 'location' ? 'bg-fog-300' : 'bg-fog-500'
                          }`} />
                          <span className="font-mono text-xs text-fog-200">{n.label}</span>
                          <span className="ml-auto font-mono text-[10px] text-fog-500">{n.rel}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>

            <div className="flex shrink-0 border-t border-ink-700">
              <button className="flex-1 py-3 font-mono text-xs text-fog-300 transition-colors hover:bg-ink-800 hover:text-paper">
                edit_entity
              </button>
              <button
                onClick={() => setTab('characters')}
                className="flex-1 border-l border-ink-700 py-3 font-mono text-xs text-accent transition-colors hover:bg-accent/10"
              >
                locate_in_text
              </button>
            </div>
          </>
        )}
      </aside>
    </div>
  )
}
