import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

const PHASE_STYLE = {
  foundation: 'bg-warn/10 text-warn border-warn/30',
  drafting: 'bg-accent/10 text-accent border-accent/30',
  revision: 'bg-fog-400/10 text-fog-300 border-fog-500/40',
  export: 'bg-paper/10 text-paper border-fog-500/40',
  idle: 'bg-ink-700 text-fog-500 border-ink-600',
}

function PhaseBadge({ phase, running }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs ${PHASE_STYLE[phase]}`}>
      {running && (
        <span className={`h-1.5 w-1.5 animate-pulse rounded-full bg-current`} />
      )}
      {phase}
    </span>
  )
}

function ProjectCard({ project, onOpen }) {
  const progress = project.chaptersTotal
    ? Math.round((project.chaptersDone / project.chaptersTotal) * 100)
    : 0

  return (
    <button
      onClick={() => onOpen(project)}
      className="group flex flex-col gap-3 rounded-xl border border-ink-700 bg-ink-900 p-5 text-left transition-colors hover:border-ink-600 hover:bg-ink-800"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-base font-semibold leading-snug text-paper">
          {project.title}
        </h2>
        <PhaseBadge phase={project.phase} running={project.running} />
      </div>

      <p className="font-mono text-xs text-fog-500">{project.name}</p>

      <div className="mt-auto grid grid-cols-3 gap-3 font-mono text-sm">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-fog-500">score</p>
          <p className="text-fog-200">
            {project.foundationScore ? project.foundationScore.toFixed(1) : '—'}
          </p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-fog-500">words</p>
          <p className="text-fog-200">{project.words.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-fog-500">chapters</p>
          <p className="text-fog-200">
            {project.chaptersDone}/{project.chaptersTotal || '—'}
          </p>
        </div>
      </div>

      {project.chaptersTotal > 0 && (
        <div className="h-1 overflow-hidden rounded-full bg-ink-700">
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </button>
  )
}

export default function Projects() {
  const [projects, setProjects] = useState(null)

  useEffect(() => {
    api.listProjects().then(setProjects)
  }, [])

  if (!projects) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-44 animate-pulse rounded-xl bg-ink-800" />
        ))}
      </div>
    )
  }

  return (
    <div>
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-paper">Projects</h1>
        <button className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-ink-950 transition-transform active:scale-[0.98]">
          New novel
        </button>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {projects.map((p) => (
          <ProjectCard key={p.name} project={p} onOpen={() => {}} />
        ))}
      </div>
    </div>
  )
}
