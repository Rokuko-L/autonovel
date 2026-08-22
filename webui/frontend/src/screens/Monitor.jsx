import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'

const PHASES = ['foundation', 'drafting', 'revision', 'export']

function Stepper({ phase }) {
  const activeIdx = PHASES.indexOf(phase)
  return (
    <ol className="flex items-center gap-2">
      {PHASES.map((p, i) => (
        <li key={p} className="flex items-center gap-2">
          {i > 0 && <span className="h-px w-5 bg-ink-600" />}
          <span
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs lowercase ${
              i === activeIdx
                ? 'border-accent/50 bg-accent/10 text-accent'
                : i < activeIdx
                  ? 'border-ink-600 bg-ink-850 text-fog-300'
                  : 'border-ink-700 bg-ink-900 text-fog-500'
            }`}
          >
            {i === activeIdx && (
              <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-accent border-t-transparent" />
            )}
            {i < activeIdx && <span className="text-good">✓</span>}
            {p}
          </span>
        </li>
      ))}
    </ol>
  )
}

function BurnStrip({ running }) {
  const [burn, setBurn] = useState({ tin: 1_284_301, tout: 96_204 })
  useEffect(() => {
    if (!running) return
    const t = setInterval(() => {
      setBurn((b) => ({
        tin: b.tin + Math.floor(Math.random() * 9000) + 2000,
        tout: b.tout + Math.floor(Math.random() * 900) + 100,
      }))
    }, 800)
    return () => clearInterval(t)
  }, [running])

  const cost = (burn.tin / 1e6) * 3 + (burn.tout / 1e6) * 15

  return (
    <div className="flex flex-wrap gap-x-10 gap-y-2 rounded-xl border border-ink-700 bg-ink-900 px-5 py-3 font-mono text-sm">
      <p className="text-fog-300">
        <span className="mr-1.5 text-fog-500">tok in</span>▲ {burn.tin.toLocaleString()}
      </p>
      <p className="text-fog-300">
        <span className="mr-1.5 text-fog-500">tok out</span>▼ {burn.tout.toLocaleString()}
      </p>
      <p className="ml-auto text-paper">
        <span className="mr-1.5 text-fog-500">est spend</span>${cost.toFixed(2)}
      </p>
      {running && <span className="self-center h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />}
    </div>
  )
}

function ScoreChart({ points, threshold }) {
  if (!points.length) return null
  const W = 560
  const H = 120
  const pad = 8
  const min = Math.min(...points.map((p) => p.score), threshold - 0.5)
  const max = Math.max(...points.map((p) => p.score), threshold + 0.3)
  const x = (i) => pad + (i / Math.max(points.length - 1, 1)) * (W - 2 * pad)
  const y = (s) => H - pad - ((s - min) / (max - min)) * (H - 2 * pad)
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(p.score)}`).join(' ')
  const lastKept = [...points].reverse().find((p) => p.kept)?.score ?? points[0].score

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
      <line x1={pad} x2={W - pad} y1={y(threshold)} y2={y(threshold)}
        stroke="var(--color-fog-500)" strokeDasharray="4 4" strokeWidth="1" />
      <text x={W - pad} y={y(threshold) - 4} textAnchor="end"
        fill="var(--color-fog-500)" fontFamily="var(--font-mono)" fontSize="9">
        gate {threshold}
      </text>
      <path d={path} fill="none" stroke="var(--color-accent)" strokeWidth="1.5" />
      {points.map((p, i) => (
        <circle key={i} cx={x(i)} cy={y(p.score)} r="3"
          fill={p.kept ? 'var(--color-accent)' : 'transparent'}
          stroke={p.kept ? 'none' : 'var(--color-fog-500)'} strokeWidth="1" />
      ))}
      <text x={pad} y={H - 1} fill="var(--color-fog-500)" fontFamily="var(--font-mono)" fontSize="9">
        best kept {lastKept.toFixed(1)}
      </text>
    </svg>
  )
}

const LEVEL_MARK = { banner: '[==]', step: '❯', warn: '[!]', raw: ' ' }
const LEVEL_STYLE = {
  banner: 'text-paper',
  step: 'text-fog-200',
  warn: 'text-accent',
  raw: 'text-fog-500',
}

export default function Monitor() {
  const [runState, setRunState] = useState(null)
  const [scores, setScores] = useState([])
  const [lines, setLines] = useState([])
  const logRef = useRef(null)
  const running = runState?.running

  useEffect(() => {
    api.getRunState().then(setRunState)
    api.getScoreHistory().then(setScores)
    const unsub = api.subscribeLogs('bells-second-son', (line) =>
      setLines((prev) => [...prev.slice(-200), line]))
    return unsub
  }, [])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight })
  }, [lines])

  return (
    <div className="flex flex-col gap-6">
      <header className="flex items-end justify-between">
        <div>
          <p className="section-head">04 · watch it write</p>
          <h1 className="mt-1 font-display text-xl lowercase tracking-tight text-paper">live run</h1>
          <p className="mt-1 font-mono text-xs text-fog-500">
            bells-second-son · started {runState?.startedAt.slice(11, 16) ?? '—'} utc
          </p>
        </div>
        {running && (
          <button className="rounded-lg border border-bad/40 px-4 py-2 text-xs lowercase text-bad transition-colors hover:bg-bad/10 active:scale-[0.98]">
            stop run
          </button>
        )}
      </header>

      <Stepper phase={runState?.phase ?? 'foundation'} />
      <BurnStrip running={!!running} />

      <section>
        <h2 className="section-head mb-2">foundation scores — keep vs discard</h2>
        <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
          <ScoreChart points={scores} threshold={7.5} />
        </div>
      </section>

      <section>
        <h2 className="section-head mb-2">activity feed</h2>
        <div
          ref={logRef}
          className="h-72 overflow-y-auto rounded-xl border border-ink-700 bg-ink-950 p-4 font-mono text-xs leading-relaxed"
        >
          {lines.map((l, i) => (
            <p key={i} className={LEVEL_STYLE[l.level]}>
              <span className="mr-2 select-none text-ink-600">{l.ts.slice(11, 19)}</span>
              <span className="mr-2 select-none text-fog-500">{LEVEL_MARK[l.level]}</span>
              {l.text}
            </p>
          ))}
        </div>
      </section>
    </div>
  )
}
