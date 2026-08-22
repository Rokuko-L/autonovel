import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

function fmtTokens(n) {
  if (n >= 1_000_000) return `${(n / 1e6).toFixed(2)}M`
  if (n >= 1_000) return `${(n / 1e3).toFixed(1)}k`
  return String(n)
}

function Tile({ label, value, sub }) {
  return (
    <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
      <p className="text-xs uppercase tracking-wide text-fog-500">{label}</p>
      <p className="mt-1 font-mono text-3xl text-paper">{value}</p>
      {sub && <p className="mt-1 font-mono text-xs text-fog-500">{sub}</p>}
    </div>
  )
}

export default function Stats() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    api.getStats('bells-second-son').then(setStats)
  }, [])

  const totalMs = stats?.durationMsTotal ?? 0

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold tracking-tight text-paper">Stats</h1>

      {!stats ? (
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-ink-800" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
            <Tile label="Tokens in" value={fmtTokens(stats.tokensInTotal)}
              sub={`${fmtTokens(stats.callCount)} calls`} />
            <Tile label="Tokens out" value={fmtTokens(stats.tokensOutTotal)} />
            <Tile label="Failed calls" value={String(stats.failedCount)}
              sub={stats.failedCount > 0 ? undefined : 'clean'} />
            <Tile label="Time in LLM" value={`${Math.round(totalMs / 60000)}m`}
              sub={`${Math.round(totalMs / 1000)}s total`} />
          </div>

          <h2 className="mb-3 mt-8 text-sm font-medium text-fog-400">By role</h2>
          <table className="w-full overflow-hidden rounded-xl border border-ink-700 bg-ink-900 text-left">
            <thead>
              <tr className="border-b border-ink-700 text-xs uppercase tracking-wide text-fog-500">
                <th className="px-4 py-3 font-medium">role</th>
                <th className="px-4 py-3 font-medium">model</th>
                <th className="px-4 py-3 text-right font-medium">tokens in</th>
                <th className="px-4 py-3 text-right font-medium">tokens out</th>
                <th className="px-4 py-3 text-right font-medium">calls</th>
              </tr>
            </thead>
            <tbody className="font-mono text-sm">
              {stats.byModel.map((r) => (
                <tr key={r.modelKey} className="border-b border-ink-800 last:border-b-0">
                  <td className="px-4 py-3 text-fog-200">{r.modelKey}</td>
                  <td className="px-4 py-3 text-fog-500">{r.model}</td>
                  <td className="px-4 py-3 text-right text-fog-200">{r.tokensIn.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-fog-200">{r.tokensOut.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-fog-400">{r.calls}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
