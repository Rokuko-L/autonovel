import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client.js'

const PHASES = [
  { id: 'foundation', meta: () => `t: —` },
  { id: 'drafting', meta: (s) => `ch: ${s?.chaptersDone ?? 0}/${s?.chaptersTotal ?? '—'}` },
  { id: 'revision', meta: (s) => `cycles: ${s?.revisionCycle ?? 0}/3` },
  { id: 'export', meta: () => `fmt: pdf` },
]

function PipelineStatus({ runState, scores }) {
  const activeIdx = PHASES.findIndex((p) => p.id === runState?.phase)
  const lastKept = [...scores].reverse().find((p) => p.kept)
  return (
    <section className="rounded-xl border border-ink-700 bg-ink-900 p-5">
      <p className="section-head mb-4">// pipeline_status</p>
      <ol className="relative space-y-5 border-l border-ink-600 pl-5">
        {PHASES.map((p, i) => {
          const done = i < activeIdx
          const active = i === activeIdx
          return (
            <li key={p.id} className={`relative ${active || done ? '' : 'opacity-50'}`}>
              <span className={`absolute -left-[26px] top-0.5 flex h-4 w-4 items-center justify-center rounded-full text-[9px] ${
                done ? 'bg-good/20 text-good' : active ? 'bg-accent/20' : 'bg-ink-700'
              }`}>
                {done ? '✓' : active && <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />}
              </span>
              <p className={`font-mono text-xs ${active ? 'text-accent' : done ? 'text-fog-200 line-through decoration-fog-500' : 'text-fog-400'}`}>
                [0{i + 1}] {p.id}
              </p>
              <p className="mt-0.5 font-mono text-[10px] text-fog-500">
                {active ? 'status: in_progress' : done ? 'status: complete' : 'status: pending'}
                {' · '}{p.meta(runState)}
              </p>
              {active && p.id === 'drafting' && runState?.chaptersTotal > 0 && (
                <div className="mt-1.5 h-1 max-w-48 bg-ink-700">
                  <div className="h-full bg-accent" style={{ width: `${(runState.chaptersDone / runState.chaptersTotal) * 100}%` }} />
                </div>
              )}
            </li>
          )
        })}
      </ol>
      {lastKept && (
        <p className="mt-4 font-mono text-[10px] text-fog-500">
          last kept score: <span className="text-good">{lastKept.score.toFixed(2)}</span>
        </p>
      )}
    </section>
  )
}

function Telemetry({ stats, scores }) {
  const cost = ((stats?.tokensInTotal ?? 0) / 1e6) * 3 + ((stats?.tokensOutTotal ?? 0) / 1e6) * 15
  const LIMIT = 5.0
  const kept = scores.filter((s) => s.kept).map((s) => s.score)
  const dropped = scores.filter((s) => !s.kept).map((s) => s.score)
  const avg = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0)
  const gate = 6.5

  return (
    <section className="rounded-xl border border-ink-700 bg-ink-900 p-5">
      <p className="section-head mb-4">// telemetry</p>
      <div className="space-y-4 font-mono text-xs">
        <div className="flex items-baseline justify-between">
          <span className="text-fog-500">token_spend</span>
          <span className="text-paper">{(stats?.tokensInTotal ?? 0).toLocaleString()} in / {(stats?.tokensOutTotal ?? 0).toLocaleString()} out</span>
        </div>
        <div>
          <div className="flex items-baseline justify-between">
            <span className="text-fog-500">est_cost (limit: ${LIMIT.toFixed(2)})</span>
            <span className={cost > LIMIT * 0.8 ? 'text-bad' : 'text-paper'}>${cost.toFixed(2)}</span>
          </div>
          <div className="mt-1.5 h-1 bg-ink-700">
            <div className={`h-full ${cost > LIMIT * 0.8 ? 'bg-bad' : 'bg-accent'}`} style={{ width: `${Math.min(100, (cost / LIMIT) * 100)}%` }} />
          </div>
        </div>
        <div>
          <p className="mb-1.5 text-fog-500">quality_gate (threshold: {gate})</p>
          {[['keep_score', avg(kept), 'var(--color-good)'], ['discard_score', avg(dropped), 'var(--color-bad)']].map(([label, v, color]) => (
            <div key={label} className="mb-1 flex items-center gap-2">
              <span className="w-20 text-fog-500">{label}</span>
              <div className="h-1 flex-1 bg-ink-700">
                <div className="h-full" style={{ width: `${Math.min(100, (v / 10) * 100)}%`, background: color }} />
              </div>
              <span className="w-8 text-right text-fog-300">{v ? v.toFixed(2) : '—'}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

const TAG_FOR = { banner: 'sys', step: 'run', warn: 'err', raw: 'llm' }
const TAG_STYLE = {
  sys: 'text-paper',
  run: 'text-fog-200',
  llm: 'text-fog-400',
  score: 'text-good',
  err: 'text-bad',
}

export default function Monitor() {
  const [runState, setRunState] = useState(null)
  const [scores, setScores] = useState([])
  const [stats, setStats] = useState(null)
  const [lines, setLines] = useState([])
  const [filter, setFilter] = useState('all')
  const [cmd, setCmd] = useState('')
  const logRef = useRef(null)
  const running = runState?.running

  useEffect(() => {
    api.getRunState().then(setRunState)
    api.getScoreHistory().then(setScores)
    api.getStats().then(setStats)
    const unsub = api.subscribeLogs('bells-second-son', (line) =>
      setLines((prev) => [...prev.slice(-200), line]))
    return unsub
  }, [])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight })
  }, [lines])

  const visible = useMemo(
    () => (filter === 'all' ? lines : lines.filter((l) => (filter === 'errors' ? TAG_FOR[l.level] === 'err' : TAG_FOR[l.level] === filter))),
    [lines, filter],
  )

  return (
    <div className="-m-8 flex h-[calc(100vh-1px)] flex-col">
      <header className="flex shrink-0 items-center justify-between border-b border-ink-700 px-6 py-3">
        <div className="flex items-baseline gap-4">
          <h1 className="font-display text-lg lowercase tracking-tight text-paper">live run</h1>
          <p className="flex items-center gap-2 font-mono text-[11px] text-fog-500">
            <span className={`h-1.5 w-1.5 ${running ? 'animate-pulse rounded-full bg-good' : 'bg-fog-500'}`} />
            process_id: run_84729a · uptime: 04:12:33
          </p>
        </div>
        <div className="flex gap-2">
          <button className="border border-ink-600 px-3 py-1 font-mono text-xs text-fog-400 transition-colors hover:border-accent/50 hover:text-accent">
            [ pause ]
          </button>
          <button className="border border-bad/40 px-3 py-1 font-mono text-xs text-bad transition-colors hover:bg-bad/10">
            [ terminate ]
          </button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-12">
        {/* left column */}
        <div className="col-span-4 space-y-4 overflow-y-auto border-r border-ink-700 p-5">
          <PipelineStatus runState={runState} scores={scores} />
          <Telemetry stats={stats} scores={scores} />
        </div>

        {/* right column — stdout */}
        <div className="col-span-8 flex min-h-0 flex-col">
          <div className="flex shrink-0 items-center justify-between border-b border-ink-700 px-5 py-2.5">
            <p className="section-head">// stdout_stream</p>
            <div className="flex gap-1">
              {['all', 'llm', 'score', 'errors'].map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`border px-2 py-0.5 font-mono text-[10px] transition-colors ${
                    filter === f ? 'border-accent/50 bg-accent/10 text-accent' : 'border-ink-700 text-fog-500 hover:text-fog-300'
                  }`}
                >
                  [{f}]
                </button>
              ))}
            </div>
          </div>

          <div ref={logRef} className="min-h-0 flex-1 overflow-y-auto bg-ink-950 p-5 font-mono text-xs leading-relaxed">
            {visible.map((l, i) => {
              const tag = TAG_FOR[l.level]
              return (
                <p key={i} className={TAG_STYLE[tag]}>
                  <span className="mr-3 inline-block w-16 select-none text-fog-500">{l.ts.slice(11, 19)}</span>
                  <span className="mr-2 select-none">[{tag}]</span>
                  {l.text}
                </p>
              )
            })}
            <p className="text-fog-300">
              <span className="mr-3 inline-block w-16 select-none text-fog-500" />
              <span className="mr-2 inline-block h-3.5 w-2 animate-pulse bg-accent align-middle" />
              awaiting_eval
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2 border-t border-ink-700 px-5 py-3">
            <span className="font-mono text-sm text-accent">&gt;</span>
            <input
              value={cmd}
              onChange={(e) => setCmd(e.target.value)}
              placeholder="inject instruction or override (e.g. /set threshold 6.0)"
              className="w-full bg-transparent font-mono text-xs text-fog-200 outline-none placeholder:text-fog-500"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
