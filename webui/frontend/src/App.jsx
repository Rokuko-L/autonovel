import { useState } from 'react'
import Projects from './screens/Projects.jsx'
import Foundation from './screens/Foundation.jsx'
import Ledger from './screens/Ledger.jsx'
import Monitor from './screens/Monitor.jsx'
import Inspector from './screens/Inspector.jsx'
import Stats from './screens/Stats.jsx'
import Settings from './screens/Settings.jsx'

const NAV = [
  { id: 'projects', num: '01', label: 'projects' },
  { id: 'foundation', num: '02', label: 'foundation' },
  { id: 'ledger', num: '03', label: 'beats & harvests' },
  { id: 'monitor', num: '04', label: 'live run' },
  { id: 'inspector', num: '05', label: 'llm inspector' },
  { id: 'stats', num: '06', label: 'costs' },
  { id: 'settings', num: '07', label: 'settings' },
]

const SCREENS = {
  projects: Projects,
  foundation: Foundation,
  ledger: Ledger,
  monitor: Monitor,
  inspector: Inspector,
  stats: Stats,
  settings: Settings,
}

export default function App() {
  const [screen, setScreen] = useState('foundation')

  return (
    <div className="flex h-screen">
      <nav className="flex w-52 shrink-0 flex-col border-r border-ink-700 bg-ink-900 py-4">
        <div className="mb-6 px-5">
          <p className="font-display text-sm font-semibold tracking-tight text-paper lowercase">
            autonovel<span className="animate-pulse text-accent">_</span>
          </p>
          <p className="mt-0.5 font-mono text-[10px] text-fog-500">v0.3 · structured pipeline</p>
        </div>

        <ul>
          {NAV.map(({ id, num, label }) => (
            <li key={id}>
              <button
                onClick={() => setScreen(id)}
                className={`group flex w-full items-baseline gap-2 px-5 py-[7px] text-left text-[13px] transition-colors ${
                  screen === id
                    ? 'bg-ink-800 text-paper'
                    : 'text-fog-400 hover:text-fog-200'
                }`}
              >
                <span
                  className={`text-[10px] ${screen === id ? 'text-accent' : 'text-fog-500'}`}
                >
                  [{num}]
                </span>
                <span className="lowercase">{label}</span>
              </button>
            </li>
          ))}
        </ul>

        <div className="mt-auto px-5 pb-2">
          <p className="section-head">active</p>
          <p className="mt-1 truncate text-xs text-fog-300">bells-second-son</p>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-accent">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
            running
          </p>
        </div>
      </nav>

      <main className="min-w-0 flex-1 overflow-y-auto p-8">
        {/* render as ELEMENTS, never fn calls — fn calls break hook ownership */}
        {screen === 'projects' && <Projects />}
        {screen === 'foundation' && <Foundation />}
        {screen === 'ledger' && <Ledger />}
        {screen === 'monitor' && <Monitor />}
        {screen === 'inspector' && <Inspector />}
        {screen === 'stats' && <Stats />}
        {screen === 'settings' && <Settings />}
      </main>
    </div>
  )
}
