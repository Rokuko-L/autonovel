# Path Resolution & Project Isolation (`core/paths.py`)

All file access in autonovel goes through `paths.py`. Nothing may hardcode
`projects/<name>/...` strings — multi-project isolation depends on every path
being derived from the active project name at call time.

## Key Types

| Function | Purpose |
|---|---|
| `get_root_dir() -> Path` | Walks up from `__file__` to find `pyproject.toml`/`.env`. Cached in `_root_dir`; raises `RuntimeError` if missing. |
| `set_project_name(name)` | Sets the active project. **Validates path isolation**: resolved dir must be inside `projects/` (blocks `../`, `.`, absolute escapes). Also sets `AUTONOVEL_PROJECT` env var so subprocesses inherit it. |
| `get_project_name() -> str` | Explicit set → `AUTONOVEL_PROJECT` env → `"default"`. |
| `get_project_dir() -> Path` | `projects/<name>/`, re-validated on every call. |
| `save_registry(data, path)` | Atomic JSON write: tmp file + `os.replace`, cleanup on failure. |

## Folder Helpers (side effects: mkdir)

`get_chapters_dir`, `get_edit_logs_dir`, `get_eval_logs_dir`, `get_logs_dir`,
`get_briefs_dir`, `get_typeset_dir` — each returns `projects/<name>/<dir>/`,
creating it if missing.

## File Path Helpers (pure)

`get_active_genre_path`, `get_seed_path`, `get_outline_path`,
`get_state_path`, `get_results_path`, `get_registry_path`, `get_world_path`,
`get_voice_path`, `get_characters_path`, `get_canon_path`,
`get_manuscript_path`, `get_reviews_path`, `get_arc_summary_path`.

Plus:
- `get_novel_title()` — title from state.json, fallback `"the novel"`
- `load_prompt(name)` — cached read of `prompts/<name>.md`
- `format_prompt(template, **kwargs)` — replaces `{key}` and `{{key}}`

## Rules

1. New file types get a helper here, not inline `Path` math in callers.
2. Any user-derived name must pass through `set_project_name`.
3. Tests may patch internals directly: `paths._root_dir`,
   `paths._project_name` (see `scratch/test_utils.py`).
4. Writes to shared JSON (registry, state) must be atomic.

Related: [llm-client.md](llm-client.md) ·
[../pipeline/state-and-git.md](../pipeline/state-and-git.md) ·
[../reference/test-suites.md](../reference/test-suites.md)
