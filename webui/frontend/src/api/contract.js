/**
 * API CONTRACT — the exact shapes the FastAPI backend will serve.
 *
 * The mock client (client.js) returns objects of these shapes from fixtures.
 * On wiring day, only client.js changes. If a screen needs a field that is
 * not in these types, add it HERE first, then to fixtures, then to screens —
 * and check core/llm.py telemetry + state.json actually produce it.
 *
 * Producers today:
 *  - Project        → projects/<name>/state.json + registry JSONL + word counts
 *  - RunState       → state.json (+ subprocess liveness in RunManager)
 *  - LogLine        → run_pipeline stdout stream (step/banner already emit)
 *  - LlmEvent       → <project>/llm_events.jsonl via core/llm._emit_llm_event
 *  - ScorePoint     → registry JSONL rows written by pipeline_infra.log_result
 *  - Settings       → .env (ANTHROPIC_API_KEY/BASE_URL, AUTONOVEL_*_MODEL)
 */

/**
 * @typedef {Object} Project
 * @property {string} name              // directory name under projects/
 * @property {string} title             // novel title from state.json ("Untitled" ok)
 * @property {"foundation"|"drafting"|"revision"|"export"|"idle"} phase
 * @property {number} foundationScore   // best-so-far foundation score (0 if none)
 * @property {number} chaptersTotal
 * @property {number} chaptersDone      // chapters with an accepted draft
 * @property {number} words             // total words across chapter files
 * @property {string|null} updatedAt    // ISO timestamp of last state change
 * @property {boolean} running          // does an active subprocess exist
 */

/**
 * @typedef {Object} RunState
 * @property {string} project
 * @property {Project["phase"]} phase
 * @property {number} iteration         // foundation iteration or chapter number
 * @property {number} foundationScore
 * @property {number} loreScore
 * @property {number} stallCount        // foundation_stall_count (plateau detector)
 * @property {string} startedAt         // ISO
 * @property {boolean} running
 */

/**
 * @typedef {Object} LogLine
 * @property {string} ts                // ISO
 * @property {"step"|"banner"|"warn"|"raw"} level
 * @property {string} text
 */

/**
 * Mirrors core/llm.py llm_events.jsonl exactly.
 * @typedef {Object} LlmEvent
 * @property {string} ts
 * @property {"writer"|"judge"|"review"} modelKey
 * @property {string} model
 * @property {boolean} ok
 * @property {number} attempt
 * @property {number|null} tokensIn
 * @property {number|null} tokensOut
 * @property {number} durationMs
 * @property {string|null} stopReason
 * @property {number} promptChars
 * @property {number} responseChars
 * @property {string} promptHead        // first 300 chars
 * @property {string} [error]
 */

/**
 * One keep/discard decision from the registry.
 * @typedef {Object} ScorePoint
 * @property {number} iteration
 * @property {number} score
 * @property {boolean} kept
 * @property {string} phase             // "foundation" | "chapter" | ...
 */

/**
 * @typedef {Object} Settings
 * @property {string} baseUrl           // ANTHROPIC_BASE_URL
 * @property {string} apiKeyMasked      // e.g. "sk-ant-…f4d2"; never the raw key
 * @property {{writer: string, judge: string, review: string}} models
 * @property {{foundation: number, chapter: number}} thresholds
 */
