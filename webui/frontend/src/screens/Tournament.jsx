import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'

function ProsePanel({ variant, elo, words, prose, selected, onSelect }) {
  return (
    <div
      onClick={onSelect}
      className={`flex min-w-0 flex-1 cursor-default flex-col border-t ${
        selected ? 'border-accent/60' : 'border-transparent'
      }`}
    >
      <div className={`flex h-9 shrink-0 items-center justify-between border-b px-4 ${
        selected ? 'border-accent/50' : 'border-ink-700'
      } bg-ink-900`}>
        <p className={`font-mono text-xs ${selected ? 'text-accent' : 'text-fog-400'}`}>
          &gt;[{variant}]
        </p>
        <p className="font-mono text-[10px] text-fog-500">
          elo: {elo} · ~{words}w
        </p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto bg-ink-950/60">
        <div className="mx-auto max-w-prose space-y-5 px-8 py-8 font-prose text-[16px] leading-[1.8] text-fog-200">
          {prose.split(/\n\s*\n/).filter((p) => p.trim()).map((p, i) => (
            <p key={i} className="whitespace-pre-wrap">{p.replace(/^#.*\n?/, '').trim()}</p>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function Tournament() {
  const [matches, setMatches] = useState(null)
  const [idx, setIdx] = useState(0)
  const [pick, setPick] = useState(null) // 'a' | 'tie' | 'b'
  const [history, setHistory] = useState([])
  const histRef = useRef(null)

  useEffect(() => {
    api.listMatches().then(setMatches)
  }, [])

  useEffect(() => {
    histRef.current?.scrollTo({ top: 0 })
  }, [history])

  if (!matches) {
    return <div className="h-96 animate-pulse rounded-xl bg-ink-800" />
  }
  if (!matches.length) {
    return (
      <p className="rounded-xl border border-ink-700 p-10 font-mono text-sm text-fog-500">
        [ no tournaments — chapters need a discarded + kept attempt pair ]
      </p>
    )
  }

  const m = matches[idx]
  const total = m.a.elo + m.b.elo
  const wrA = (m.a.elo / total) * 100

  const vote = (choice) => {
    if (pick) return
    setPick(choice)
    const delta = { a: '+12', b: '-12', tie: '±0' }[choice]
    const verdict =
      choice === 'a' ? 'a_defeated_b' : choice === 'b' ? 'b_defeated_a' : 'tie_recorded'
    setHistory((h) => [
      { ts: new Date().toISOString().slice(11, 19), verdict, delta, fresh: true },
      ...h.slice(-19),
    ])
    setTimeout(() => {
      setHistory((h) => h.map((e) => ({ ...e, fresh: false })))
      setPick(null)
      setIdx((i) => (i + 1) % matches.length)
    }, 1600)
  }

  return (
    <div className="-m-8 flex h-[calc(100vh-1px)] flex-col">
      {/* header */}
      <header className="flex shrink-0 items-center justify-between border-b border-ink-700 px-6 py-4">
        <div>
          <p className="font-mono text-xs text-fog-500">match_{String(idx + 1).padStart(3, '0')} // chapter {String(m.chapter).padStart(2, '0')}</p>
          <h1 className="mt-0.5 font-display text-xl lowercase tracking-tight text-paper">
            chapter arena <span className={pick ? 'text-good' : 'text-accent'}>{pick ? '· vote locked' : '· awaiting verdict'}</span>
          </h1>
        </div>
        <div className="w-64">
          <div className="flex justify-between font-mono text-[10px] text-fog-500">
            <span>var_a [{m.a.elo}]</span>
            <span>var_b [{m.b.elo}]</span>
          </div>
          <div className="mt-1 flex h-1.5 divide-x divide-ink-950">
            <div className="bg-accent" style={{ width: `${wrA}%` }} />
            <div className="bg-fog-500/60 flex-1" />
          </div>
          <div className="mt-1 flex justify-between font-mono text-[10px]">
            <span className="text-accent">wr: {wrA.toFixed(1)}%</span>
            <span className="text-fog-400">wr: {(100 - wrA).toFixed(1)}%</span>
          </div>
        </div>
      </header>

      {/* variants */}
      <div className="flex min-h-0 flex-1 divide-x divide-ink-700">
        <ProsePanel
          variant="variant_a" elo={m.a.elo} words={m.a.words} prose={m.a.prose}
          selected={pick === 'a'} onSelect={() => !pick && vote('a')}
        />
        <ProsePanel
          variant="variant_b" elo={m.b.elo} words={m.b.words} prose={m.b.prose}
          selected={pick === 'b'} onSelect={() => !pick && vote('b')}
        />
      </div>

      {/* dock */}
      <footer className="shrink-0 border-t border-ink-700 bg-ink-900">
        <div className="grid grid-cols-3 divide-x divide-ink-700 border-b border-ink-700">
          {[
            ['a_wins', 'select variant a', 'a', 'hover:bg-accent/10 hover:text-accent'],
            ['tie', 'negligible difference', 'tie', 'hover:bg-ink-800 hover:text-paper'],
            ['b_wins', 'select variant b', 'b', 'hover:bg-good/10 hover:text-good'],
          ].map(([label, cap, choice, style]) => (
            <button
              key={choice}
              onClick={() => vote(choice)}
              disabled={!!pick}
              className={`group py-3 text-center font-mono text-sm transition-colors disabled:opacity-50 ${style} ${
                pick === choice ? 'bg-accent/15 text-accent' : 'text-fog-300'
              }`}
            >
              [{label}]
              <span className="ml-2 text-[10px] text-fog-500">{cap}</span>
            </button>
          ))}
        </div>
        <div ref={histRef} className="h-20 overflow-y-auto px-6 py-2 font-mono text-[11px] leading-relaxed">
          <p className="float-right text-[10px] text-fog-500">// recent_ops</p>
          {history.length === 0 && <p className="text-fog-500">[ no verdicts yet — pick a winner ]</p>}
          {history.map((h, i) => (
            <p key={i} className={h.fresh ? 'text-accent' : 'text-fog-500'}>
              <span className="mr-2 text-ink-600">{h.ts}</span>
              [sys] {h.verdict} // {h.delta} elo
            </p>
          ))}
        </div>
      </footer>
    </div>
  )
}
