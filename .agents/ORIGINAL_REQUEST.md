# Original User Request

## Initial Request — 2026-06-16T06:34:33Z

Refactor the Autonovel pipeline to support isolated project sessions (housed in dynamic subfolders under `projects/`), dynamic path resolution helpers in `utils.py`, atomic registry state updates, and robust Git guards.

Working directory: D:\Tugas\LLM\autonovel
Integrity mode: development

## Requirements

### R1. Core Path & Configuration Refactoring (`utils.py`)
- Implement a robust `get_root_dir()` function that walks up parent folders from `__file__` to find `pyproject.toml` or `.env`. Raise `RuntimeError` if not found.
- Implement explicit active project configuration state (`utils.set_project_name(name)` and `utils.get_project_name()`) with `AUTONOVEL_PROJECT` env variable fallback.
- Define dynamic path helpers for all folders (`get_chapters_dir()`, `get_edit_logs_dir()`, etc.) which ensure the directories exist.
- Define dynamic path helpers for all file paths (`get_outline_path()`, `get_state_path()`, etc.) that are pure functions returning `Path` objects with no file creation side effects.
- Implement an atomic write function `save_registry(data, path)` which writes to `.tmp` and renames atomically, cleaning up the `.tmp` file *only* if the JSON serialization fails.

### R2. Pipeline Orchestration & Registry (`run_pipeline.py`)
- Add the `--project` command-line argument. Remove top-level path variable assignments and evaluate paths dynamically inside functions at runtime.
- Maintain a metadata project registry in `projects/registry.json` utilizing the atomic `save_registry` function.
- Implement project lifecycle: resume from saved `state.json` by default if it exists, and require `--from-scratch` to reset and overwrite.
- **Option B Git Guards:** 
  - On project startup, verify that the root directory's `.gitignore` contains a rule ignoring `projects/` to prevent nested repository collisions. Append `projects/` to `.gitignore` if it is not present.
  - Run `git init` inside each new project folder upon creation, protected by an idempotence check (only if `projects/<project_name>/.git/` is missing) and write a project-level `.gitignore` template.

### R3. Codebase Scripts Routing
- Refactor all pipeline scripts (`evaluate.py`, `adversarial_edit.py`, `apply_cuts.py`, `build_outline.py`, `build_arc_summary.py`, `gen_brief.py`, reader/review panels, etc.) to use `utils` dynamic path helpers.
- Configure Tectonic/LaTeX compilation to execute with the subprocess working directory (`cwd`) set to the project's `typeset/` folder to prevent auxiliary file contamination in the root.

---

## Acceptance Criteria

### Directory and Session Isolation
- [ ] All chapter files (`ch_*.md`) are written to `projects/<project_name>/chapters/`.
- [ ] All planning documents (`world.md`, `voice.md`, `characters.md`, `outline.md`, `canon.md`) are written to `projects/<project_name>/`.
- [ ] All intermediate logs (`edit_logs/`, `eval_logs/`) and briefs (`briefs/`) are written under `projects/<project_name>/`.
- [ ] Tectonic auxiliary files (`.aux`, `.log`, `.toc`, `.pdf`) are generated inside `projects/<project_name>/typeset/`.

### Registry Integrity & Lifecycle
- [ ] `projects/registry.json` is updated atomically and lists each project with metadata (`title`, `genre`, `created_at`, `last_modified`, `phase`, `novel_score`, `word_count`).
- [ ] If a project exists, running `--project name` resumes from its saved `state.json`. Running with `--from-scratch` overwrites the saved state and project files.

### Git & Root Protection
- [ ] The root codebase's `.gitignore` file ignores `projects/` to protect against accidental commits of nested sub-repositories.
- [ ] Every active project folder has its own isolated `.git` repository, initialized without resetting or overriding existing repository state.

### Path Safety
- [ ] Running any phase of the pipeline does not create any new files or directories in the root workspace directory (excluding the `projects/` subfolder).

### Verification Suite
- [ ] Scratch test script `scratch/test_multi_project.py` successfully validates registry management, project directory isolation, and scratch reset behavior.
- [ ] Scratch test script `scratch/test_path_contamination.py` successfully mocks LLM calls via `unittest.mock.patch` on `utils.call_anthropic`, runs an end-to-end mock pipeline, and recursively asserts that zero files were created in the root codebase directory.
