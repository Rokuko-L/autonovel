import projects from '../fixtures/projects.json'
import runState from '../fixtures/run-state.json'
import scoreHistory from '../fixtures/score-history.json'
import llmEvents from '../fixtures/llm-events.json'
import settings from '../fixtures/settings.json'

/**
 * Mock API client — implements the contract in contract.js from fixtures.
 * THE swap point on wiring day: same function names, real fetch() calls.
 * Streaming endpoints (log tail, live events) are exposed as subscribe()
 * functions so screens never know the difference.
 */

const delay = (ms = 120) => new Promise((r) => setTimeout(r, ms))

export const api = {
  async listProjects() {
    await delay()
    return projects
  },

  async getRunState(_project) {
    await delay()
    return runState
  },

  async getScoreHistory(_project) {
    await delay()
    return scoreHistory
  },

  async listLlmEvents(_project) {
    await delay(200)
    return llmEvents
  },

  async getStats(project) {
    await delay()
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
    await delay()
    return settings
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
