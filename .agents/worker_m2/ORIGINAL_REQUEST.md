## 2026-06-16T13:40:14+07:00
Your identity is worker_m2.
Your working directory is: d:\Tugas\LLM\autonovel\.agents\worker_m2\

Task:
Refactor utils.py in place to implement the Milestone 2 requirements:
- Implement get_root_dir() -> Path: walk up from __file__ to find pyproject.toml or .env. Raise RuntimeError if missing. (Can cache in a module-level variable for efficiency).
- Implement set_project_name(name: str): sets the global _project_name.
- Implement get_project_name() -> str: returns _project_name, falls back to AUTONOVEL_PROJECT env var, and then defaults to "default".
- Implement save_registry(data: dict, path: Path): atomically writes registry JSON via .tmp file and rename, with cleanup of the .tmp file if JSON serialization/writing fails. Ensure it supports both POSIX and Windows (os.replace performs atomic replace on both).
- Dynamic folder helpers that ensure the directories exist (calling mkdir(parents=True, exist_ok=True)):
  - get_chapters_dir() -> Path
  - get_edit_logs_dir() -> Path
  - get_eval_logs_dir() -> Path
  - get_briefs_dir() -> Path
  - get_typeset_dir() -> Path
  All located under projects/<project_name>/ in the workspace root.
- Pure file helpers returning Path objects without file/directory creation side effects:
  - get_outline_path() -> Path
  - get_state_path() -> Path
  - get_results_path() -> Path
  - get_registry_path() -> Path
  - get_world_path() -> Path
  - get_voice_path() -> Path
  - get_characters_path() -> Path
  - get_canon_path() -> Path
  - get_manuscript_path() -> Path
  - get_reviews_path() -> Path
  - get_arc_summary_path() -> Path
- Update get_novel_title() to use get_state_path().

Ensure that no files are created in the root codebase directory (except projects/).
Validate by compiling utils.py and executing a quick import test to verify it resolves without error:
python -m py_compile utils.py
python -c "import utils; print(utils.get_root_dir()); print(utils.get_chapters_dir())"

MANDATORY INTEGRITY WARNING:
> DO NOT CHEAT. All implementations must be genuine. DO NOT
> hardcode test results, create dummy/facade implementations, or
> circumvent the intended task. A Forensic Auditor will independently
> verify your work. Integrity violations WILL be detected and your
> work WILL be rejected.

Write your changes report in d:\Tugas\LLM\autonovel\.agents\worker_m2\changes.md and handoff.md, then send a message back with the path when done.
