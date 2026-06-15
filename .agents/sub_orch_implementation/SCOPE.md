# Scope: Implementation Track

## Architecture
- `utils.py`: Path helpers, active project state, Anthropic API interface.
- `run_pipeline.py`: Main entry point and lifecycle orchestrator, projects registry.
- Scripts: All generator, evaluation, and review scripts refactored to use dynamic path helpers.
- Typesetting: sandboxed tectonic build inside `projects/<project_name>/typeset/`.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 2 | Core Path & Config Refactoring (utils.py) | Refactor `utils.py` with dynamic path helpers, project state, and atomic save | none | DONE |
| 3 | Pipeline Orchestration & Registry (run_pipeline.py) | Refactor `run_pipeline.py` with registry management, CLI args, and Git guards | M2 | IN_PROGRESS (Subagents: 35fd481c, d56e3975, 95b9d94a) |
| 4 | Script Routing | Refactor all pipeline scripts and typeset helper | M2, M3 | PLANNED |
| 5 | Validation & Hardening | E2E Test Suite (Tiers 1-4) & Adversarial Hardening (Tier 5) | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
- `utils.get_root_dir() -> Path`
- `utils.set_project_name(name: str)`
- `utils.get_project_name() -> str`
- `utils.save_registry(data: dict, path: Path)`
- `utils.get_chapters_dir() -> Path`
- `utils.get_edit_logs_dir() -> Path`
- `utils.get_eval_logs_dir() -> Path`
- `utils.get_briefs_dir() -> Path`
- `utils.get_typeset_dir() -> Path`
- `utils.get_outline_path() -> Path`
- `utils.get_state_path() -> Path`
- `utils.get_results_path() -> Path`
- `utils.get_registry_path() -> Path`
- `utils.get_world_path() -> Path`
- `utils.get_voice_path() -> Path`
- `utils.get_characters_path() -> Path`
- `utils.get_canon_path() -> Path`
- `utils.get_manuscript_path() -> Path`
- `utils.get_reviews_path() -> Path`
- `utils.get_arc_summary_path() -> Path`
