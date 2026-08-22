import { useState } from 'react'
import Projects from './screens/Projects.jsx'
import Monitor from './screens/Monitor.jsx'
import Inspector from './screens/Inspector.jsx'
import Stats from './screens/Stats.jsx'
import Settings from './screens/Settings.jsx'

const NAV = [
  { id: 'projects', label: 'Projects' },
  { id: 'monitor', label: 'Run Monitor' },
  { id: 'inspector', label: 'LLM Inspector' },
  { id: 'stats', label: 'Stats' },
  { id: 'settings', label: 'Settings' },
]

export default function App() {
  const [screen, setScreen] = useState('projects')

  return (
    <div className="flex h-screen">
      <nav className="flex w-56 shrink-0 flex-col border-r border-ink-700 bg-ink-900 py-5">
        <div className="mb-8 px-5">
          <span className="font-display text-lg font-semibold tracking-tight text-paper">
            autonovel
          </span>
        </div>
        <ul className="flex flex-col gap-0.5 px-3">
          {NAV.map(({ id, label }) => (
            <li key={id}>
              <button
                onClick={() => setScreen(id)}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  screen === id
                    ? 'bg-ink-700 text-paper'
                    : 'text-fog-400 hover:bg-ink-800 hover:text-fog-200'
                }`}
              >
                {label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <main className="min-w-0 flex-1 overflow-y-auto p-8">
        {screen === 'projects' && <Projects />}
        {screen === 'monitor' && <Monitor />}
        {screen === 'inspector' && <Inspector />}
        {screen === 'stats' && <Stats />}
        {screen === 'settings' && <Settings />}
      </main>
    </div>
  )
}
