import projects from '../fixtures/projects.json'
import runState from '../fixtures/run-state.json'
import scoreHistory from '../fixtures/score-history.json'
import llmEvents from '../fixtures/llm-events.json'
import settings from '../fixtures/settings.json'
import chapters from '../fixtures/chapters.json'
import evals from '../fixtures/evals.json'
import revision from '../fixtures/revision.json'
import tournament from '../fixtures/tournament.json'

/**
 * API client — implements the contract in contract.js.
 * Talks to the FastAPI bridge (webui/server.py, port 8600 via the vite
 * proxy); if the server isn't up, falls back to the generated fixtures so
 * the console stays browsable offline.
 * Streaming endpoints (log tail, live events) are exposed as subscribe()
 * functions so screens never know the difference.
 */

async function live(path, fallback) {
  try {
    const res = await fetch(path)
    if (!res.ok) throw new Error(`${res.status} ${path}`)
    return await res.json()
  } catch {
    return fallback
  }
}

// Active project, set from the projects screen ([open]); empty string means
// "server decides" — the bridge defaults to the most recently touched project.
let activeProject = localStorage.getItem('autonovel_active_project') ?? ''

const q = (project) => {
  const name = project ?? activeProject
  return name ? `?project=${encodeURIComponent(name)}` : ''
}

export const api = {
  setActiveProject(name) {
    activeProject = name
    if (name) localStorage.setItem('autonovel_active_project', name)
    else localStorage.removeItem('autonovel_active_project')
  },

  getActiveProject() {
    return activeProject
  },

  async listProjects() {
    return live('/api/projects', projects)
  },

  async getRunState(project) {
    return live(`/api/run-state${q(project)}`, runState)
  },

  async getScoreHistory(project) {
    return live(`/api/score-history${q(project)}`, scoreHistory)
  },

  async listLlmEvents(project) {
    return live(`/api/llm-events${q(project)}`, llmEvents)
  },

  async getStats(project) {
    const evts = await this.listLlmEvents(project)
    const ok = evts.filter((e) => e.ok)
    const sum = (k) => ok.reduce((a, e) => a + (e[k] ?? 0), 0)
    return {
      tokensInTotal: sum('tokensIn'),
      tokensOutTotal: sum('tokensOut'),
      callCount: evts.length,
      failedCount: evts.length - ok.length,
      durationMsTotal: sum('durationMs'),
      byModel: Object.entries(
        ok.reduce((acc, e) => {
          acc[e.modelKey] ??= { model: e.model, tokensIn: 0, tokensOut: 0, calls: 0 }
          acc[e.modelKey].tokensIn += e.tokensIn ?? 0
          acc[e.modelKey].tokensOut += e.tokensOut ?? 0
          acc[e.modelKey].calls += 1
          return acc
        }, {}),
      ).map(([modelKey, v]) => ({ modelKey, ...v })),
    }
  },

  async getSettings() {
    return live('/api/settings', settings)
  },

  async listChapters(project) {
    return live(`/api/chapters${q(project)}`, chapters)
  },

  /** evals map is keyed by the pipeline's eval-log chapter key (`ch01`). */
  async getEvals(project, chapterId) {
    const map = await this.listEvals(project)
    return map[chapterId.replace('ch_', 'ch')] ?? []
  },

  async listEvals(project) {
    return live(`/api/evals${q(project)}`, evals)
  },

  async getRevision(project) {
    return live(`/api/revision${q(project)}`, revision)
  },

  async listMatches(project) {
    return live(`/api/tournament${q(project)}`, tournament)
  },

  /** Live log tail. Mock replays a scripted run; real impl subscribes to SSE. */
  subscribeLogs(_project, onLine) {
    const script = [
      ['step', 'Generating world bible...'],
      ['raw', '  [world] continents: 3, magic system: debt-based'],
      ['step', 'Evaluating foundation...'],
      ['step', 'Foundation score: 6.4  (lore: 5.9, prev best: 6.2)'],
      ['step', 'Foundation Iteration 7', 'banner'],
      ['step', 'Generating outline (part 1)...'],
    ]
    let i = 0
    const t = setInterval(() => {
      if (i >= script.length) return clearInterval(t)
      const [level, text] = script[i++]
      onLine({ ts: new Date().toISOString(), level, text })
    }, 900)
    return () => clearInterval(t)
  },

  /** Live LLM event feed. Real impl tails llm_events.jsonl over SSE. */
  subscribeLlmEvents(_project, onEvent) {
    let i = 0
    const t = setInterval(() => {
      const base = llmEvents[i % llmEvents.length]
      i += 1
      onEvent({ ...base, ts: new Date().toISOString(), durationMs: base.durationMs + i * 37 })
    }, 2500)
    return () => clearInterval(t)
  },
}
