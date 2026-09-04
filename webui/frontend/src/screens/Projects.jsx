import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

const PHASE_STYLE = {
  foundation: 'text-paper',
  drafting: 'text-accent',
  revision: 'text-good',
  export: 'text-fog-300',
  idle: 'text-fog-500',
}

/** 5-segment quality meter, filled = score/10 * 5 */
function QualitySig({ score }) {
  if (score == null) return <span className="font-mono text-xs text-fog-500">—</span>
  const filled = Math.round((score / 10) * 5)
  return (
    <span className="inline-flex items-center gap-2">
      <span className={`font-mono text-xs ${score >= 6.5 ? 'text-good' : 'text-fog-200'}`}>
        {score.toFixed(1)}
      </span>
      <span className="flex gap-0.5">
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} className={`h-3 w-1.5 ${i < filled ? 'bg-accent' : 'bg-ink-600'}`} />
        ))}
      </span>
    </span>
  )
}

function Row({ p, onOpen }) {
  return (
    <li className="group relative border-t border-ink-700 first:border-t-0">
      <span className="absolute inset-y-0 left-0 w-0.5 bg-accent opacity-0 transition-opacity group-hover:opacity-100" />
      <button
        onClick={() => onOpen(p)}
        className="grid w-full grid-cols-[1fr_10rem_9rem_9rem_9rem_6rem] items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-ink-900"
      >
        <div className="min-w-0">
          <p className="truncate font-prose text-[15px] leading-snug text-paper">
            {p.title === 'Untitled' ? <span className="text-fog-500">untitled</span> : p.title}
          </p>
          <p className="mt-0.5 truncate font-mono text-[10px] text-fog-500">{p.name}</p>
        </div>

        <span className="truncate font-mono text-xs text-fog-400">{p.genre ?? '—'}</span>

        <span className="font-mono text-xs text-fog-300">
          {p.words ? `${(p.words / 1000).toFixed(1)}k` : '—'}
          <span className="text-fog-500"> / {p.chaptersTotal || '—'}ch</span>
        </span>

        <span className={`font-mono text-xs ${PHASE_STYLE[p.phase] ?? 'text-fog-500'}`}>
          [ {p.running && <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent align-middle" />}
          {p.phase} ]
          {p.revisionCycle > 0 && (
            <span className="ml-1 text-[10px] text-fog-500">cycle {String(p.revisionCycle).padStart(2, '0')}</span>
          )}
        </span>

        <QualitySig score={p.novelScore || p.foundationScore || null} />

        <span className="col-span-1 text-right font-mono text-xs text-fog-500 transition-colors group-hover:text-accent">
          open ›
        </span>
      </button>
    </li>
  )
}

const SEG = {
  wrapper: 'flex border border-ink-600',
  btn: (active) =>
    `flex-1 px-3 py-1.5 font-mono text-xs transition-colors ${
      active ? 'bg-accent text-ink-950' : 'text-fog-400 hover:text-fog-200'
    }`,
}

function InitiationPanel() {
  const [form, setForm] = useState({
    id: '', genre: '', source: '', chapters: 24, notesType: 'file_path', framework: true,
  })
  const input =
    'w-full bg-ink-950 px-3 py-2 font-mono text-xs text-fog-200 outline-none border border-ink-600 focus:border-accent/60'

  return (
    <aside className="w-96 shrink-0 border-l border-ink-700 bg-ink-900 p-6">
      <p className="section-head text-accent">// initiate</p>
      <p className="mt-1 font-mono text-[11px] text-fog-500">spawn_new_narrative_instance</p>

      <div className="mt-6 space-y-4">
        <label className="block">
          <span className="mb-1 block font-mono text-[10px] text-fog-500">project_id</span>
          <div className="flex items-center border border-ink-600 bg-ink-950 focus-within:border-accent/60">
            <span className="pl-3 font-mono text-xs text-accent">&gt;</span>
            <input className="w-full bg-transparent px-2 py-2 font-mono text-xs text-fog-200 outline-none"
              placeholder="untitled_instance"
              value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value })} />
          </div>
        </label>

        <label className="block">
          <span className="mb-1 block font-mono text-[10px] text-fog-500">genre_classification</span>
          <input className={input} placeholder="e.g. comedy fantasy misunderstanding"
            value={form.genre} onChange={(e) => setForm({ ...form, genre: e.target.value })} />
        </label>

        <label className="block">
          <span className="mb-1 block font-mono text-[10px] text-fog-500">source_input</span>
          <div className="flex items-center border border-ink-600 bg-ink-950 focus-within:border-accent/60">
            <span className="pl-3 font-mono text-xs text-fog-500">/</span>
            <input className="w-full bg-transparent px-2 py-2 font-mono text-xs text-fog-200 outline-none"
              placeholder="./seed.txt"
              value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
          </div>
        </label>

        <div>
          <div className="mb-1 flex items-baseline justify-between">
            <span className="font-mono text-[10px] text-fog-500">chapter_count</span>
            <span className="font-mono text-[10px] text-fog-500">target_architecture</span>
          </div>
          <div className={SEG.wrapper}>
            {[12, 24, 30].map((n) => (
              <button key={n} onClick={() => setForm({ ...form, chapters: n })} className={SEG.btn(form.chapters === n)}>
                {n}
              </button>
            ))}
          </div>
        </div>

        <div>
          <span className="mb-1 block font-mono text-[10px] text-fog-500">notes_source_type</span>
          <div className={SEG.wrapper}>
            {['raw_text', 'file_path'].map((t) => (
              <button key={t} onClick={() => setForm({ ...form, notesType: t })} className={SEG.btn(form.notesType === t)}>
                [{t}]
              </button>
            ))}
          </div>
        </div>

        <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-fog-300">
          <span
            onClick={() => setForm({ ...form, framework: !form.framework })}
            className={`flex h-4 w-4 items-center justify-center border ${
              form.framework ? 'border-accent' : 'border-ink-600'
            }`}
          >
            {form.framework && <span className="h-2 w-2 bg-accent" />}
          </span>
          generate_framework
        </label>
      </div>

      <button className="mt-8 w-full border border-accent/50 py-2.5 font-mono text-xs uppercase tracking-widest text-accent transition-colors hover:bg-accent hover:text-ink-950">
        commit_instance
      </button>
    </aside>
  )
}

export default function Projects() {
  const [projects, setProjects] = useState(null)

  useEffect(() => {
    api.listProjects().then(setProjects)
  }, [])

  return (
    <div className="-m-8 flex h-[calc(100vh-1px)]">
      <main className="min-w-0 flex-1 overflow-y-auto p-6">
        <header className="mb-6">
          <p className="section-head">01 · your shelf</p>
          <h1 className="mt-1 font-display text-xl lowercase tracking-tight text-paper">projects</h1>
        </header>

        <div className="overflow-hidden rounded-xl border border-ink-700 bg-ink-850">
          <div className="grid grid-cols-[1fr_10rem_9rem_9rem_9rem_6rem] gap-4 bg-ink-900 px-5 py-2.5 font-mono text-[10px] text-fog-500">
            <span>project_id</span><span>genre</span><span>word_count</span>
            <span>phase</span><span>quality_sig</span><span className="text-right">sys_ops</span>
          </div>
          {!projects ? (
            <>
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-16 animate-pulse border-t border-ink-700 bg-ink-800"
                  style={{ animationDelay: `${i * 120}ms` }} />
              ))}
            </>
          ) : (
            <ul>
              {projects.map((p) => (
                <Row key={p.name} p={p} onOpen={() => {}} />
              ))}
              <li className="border-t border-ink-700 py-3 text-center font-mono text-[10px] text-fog-500">
                [ end_of_records ]
              </li>
            </ul>
          )}
        </div>
      </main>

      <InitiationPanel />
    </div>
  )
}
