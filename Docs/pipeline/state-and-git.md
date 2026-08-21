# State, Registry & Git Plumbing (`pipeline/pipeline_infra.py`)

Infrastructure extracted from the orchestrator. `run_pipeline.py` keeps the
phase functions and CLI; this module holds everything they share.

## Constants

| Constant | Meaning |
|---|---|
| `FOUNDATION_THRESHOLD = 7.5` | Foundation loop exits above this |
| `CHAPTER_THRESHOLD = 6.5` | Chapter retry gate |
| `MAX_FOUNDATION_ITERS / MAX_CHAPTER_ATTEMPTS / MAX_OUTLINE_ATTEMPTS` | Retry budgets |
| `MIN/MAX_REVISION_CYCLES`, `PLATEAU_DELTA` | Revision loop bounds + plateau sensitivity |
| `PHASE_ORDER` | `["foundation", "drafting", "revision", "export"]` |

## State & Registry

- `load_state / default_state / save_state` — `projects/<name>/state.json`
  checkpointing; written after every phase/step so crashes resume cleanly
  (rerun without `--from-scratch`).
- `load_registry / update_registry` — `projects/registry.json` session
  registry (atomic writes via `paths.save_registry`).
- `log_result(commit, phase, score, words, verdict, note)` — appends to
  `results.tsv`; one row per attempt (`keep`/`discard`/`forced`/`cycle`).

## Git Keep/Discard

The pipeline treats git as an undo system:

- `git_add_commit(msg)` → commit staged work, return short hash
- `git_commit_staged(msg)` → commit only what's staged
- `git_reset_hard(ref)` → revert a rejected attempt
- `ensure_gitignore_projects()` / `ensure_project_git(dir)` → root repo
  ignores `projects/`; each project gets its own `.git`

## Score Parsing

- `parse_score(stdout, key)` — parses `key: N` lines from evaluator output.
  **Raises ValueError when missing** — a silently absent score must never
  reach keep/discard decisions.
- `parse_score_any(stdout, *keys)` — explicit multi-key fallback
  (e.g. novel evals print `novel_score`, older ones `overall_score`).
- `get_historical_best_for_chapter(n)` — best score+commit for chapter N
  from results.tsv; used as the revert target for regressed revisions.

## Subprocess Helpers

- `run_tool(cmd, timeout, cwd)` — capture-output runner returning
  `CompletedProcess`.
- `uv_run(script, timeout)` — `run_tool("uv run python <script>")`.
- `Tee` — duplicates stdout/stderr into per-run log files under
  `projects/<name>/logs/`.

Related: [spec.md](spec.md) · [scoring-engine.md](scoring-engine.md) ·
[../core/path-resolution.md](../core/path-resolution.md)
