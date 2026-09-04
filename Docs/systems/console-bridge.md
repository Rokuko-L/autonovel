# Operator Console Bridge (webui/server.py)

The webui is a React 19 + Vite single-page console (`webui/frontend/`) rendered
from real pipeline artifacts. This doc covers the FastAPI bridge that serves it.

## Run

```bash
uv run uvicorn server:app --app-dir webui --port 8600   # from repo root
cd webui/frontend && npm run dev                        # vite on :5175
```

The vite dev server proxies `/api -> http://127.0.0.1:8600`
(`webui/frontend/vite.config.js`). Interactive API docs at
`http://127.0.0.1:8600/api/docs`.

## Data flow

```
projects/<name>/ artifacts (state.json, results.tsv, eval_logs/, briefs/,
edit_logs/, chapters/, outline.md, world/characters/canon.md)
        │
        ▼
webui/server.py ── reuses scratch/gen_webui_fixtures.py generators ──> /api/*
        │
        ▼
webui/frontend/src/api/client.js ── fetch /api, fixture fallback ──> screens
```

`contract.js` is the source of truth for response shapes; the server must
satisfy it. Project names pass through `paths.set_project_name` (path-isolation
check). The default project is the most recently touched `state.json`; the
frontend can pin one via the projects screen ([open]), persisted in
`localStorage.autonovel_active_project`.

## Endpoints (read-only phase)

| Route | Serves |
|---|---|
| `GET /api/projects` | all projects under `projects/` with state |
| `GET /api/run-state?project=` | phase/score snapshot for the cockpit header |
| `GET /api/score-history?project=` | keep/discard points from `results.tsv` |
| `GET /api/llm-events?project=` | `llm_events.jsonl` in contract camelCase |
| `GET /api/foundation?project=` | entity graph nodes/edges + world/characters/canon/voice docs |
| `GET /api/ledger?project=` | premise beats, roadmap, foreshadowing threads |
| `GET /api/chapters?project=` | chapters + per-attempt history + full prose |
| `GET /api/evals?project=` | eval-log map keyed by eval-log chapter key (`ch01`) |
| `GET /api/revision?project=` | revision briefs, adversarial cuts, novel reviews |
| `GET /api/tournament?project=` | synthesized A/B matches from discard/keep pairs |
| `GET /api/settings` | masked `.env` values + `pipeline_infra` gate constants |

## Deferred (not in the bridge yet)

- **RunManager**: launching/pausing/terminating `run_pipeline.py` subprocesses;
  the live-run screen's stdout stream and liveness are still client-side mocks
  (`subscribeLogs` / `subscribeLlmEvents` in client.js).
- **Settings mutation** (`commit_changes`) and project initiation
  (`commit_instance`) — POST endpoints.
- **SSE streams** tailing `llm_events.jsonl` and pipeline stdout.

## Tests

`scratch/test_webui_server.py` — import smoke + pure helpers (`norm_phase`,
`_mask`). Full suite stays offline; endpoint behavior is exercised manually
against real projects.
