# Handoff Report — 2026-06-16T13:38:11+07:00

## 1. Observation
- `utils.py` is located at `d:\Tugas\LLM\autonovel\utils.py`.
- On line 9, `BASE_DIR = Path(__file__).resolve().parent` is defined.
- On line 92, `get_novel_title` uses hardcoded path `state_path = __import__("pathlib").Path(__file__).parent / "state.json"`.
- The current implementation of `utils.py` lacks active project name storage (`set_project_name`, `get_project_name`), root discovery (`get_root_dir`), atomic updates (`save_registry`), folder path helpers, and file path helpers.
- The requirements in `.agents/ORIGINAL_REQUEST.md` (R1) specify:
  - `utils.get_root_dir() -> Path`
  - `utils.set_project_name(name: str)`
  - `utils.get_project_name() -> str`
  - `utils.save_registry(data: dict, path: Path)`
  - Folder helpers: `get_chapters_dir()`, `get_edit_logs_dir()`, `get_eval_logs_dir()`, `get_briefs_dir()`, `get_typeset_dir()`.
  - File helpers: `get_outline_path()`, `get_state_path()`, `get_results_path()`, `get_registry_path()`, `get_world_path()`, `get_voice_path()`, `get_characters_path()`, `get_canon_path()`, `get_manuscript_path()`, `get_reviews_path()`, `get_arc_summary_path()`.

## 2. Logic Chain
- To implement isolated project sessions, path helpers must resolve dynamic paths under `projects/<project_name>/`.
- `get_root_dir()` is designed to walk up parent directories of `__file__` (which resides in the root codebase) until `pyproject.toml` or `.env` is found, ensuring a robust lookup.
- `set_project_name()` and `get_project_name()` use a module-level global variable (`_active_project`) along with `os.environ.get("AUTONOVEL_PROJECT")` as fallback and `"default"` as default.
- Folder helpers return `Path` objects and call `.mkdir(parents=True, exist_ok=True)` to guarantee they exist.
- File helpers return pure `Path` objects to prevent side-effects during route planning or checking.
- `save_registry()` uses `tmp_path = path.parent / f"{path.name}.tmp"`, serializes using `json.dumps`, writes to the `.tmp` file, and uses `os.replace` to atomically swap. If any exception happens during serialization or writing, `tmp_path` is unlinked.

## 3. Caveats
- `get_novel_title()` should be updated to use the dynamic `get_state_path()`.
- Windows filesystem-level locks could theoretically interfere with `os.replace` if a file is open, but using standard file operations (and correct context managers/garbage collection) will prevent this.

## 4. Conclusion
- A design for the `utils.py` refactoring is completed and documented in `analysis.md`. It covers all 11 file helpers, 5 folder helpers, configuration state, root discovery, and atomic registry serialization.

## 5. Verification Method
1. Create a verification script `scratch/test_utils.py` to:
   - Verify `utils.get_root_dir()` returns the root codebase path.
   - Verify `utils.get_project_name()` responds correctly to `set_project_name` and the `AUTONOVEL_PROJECT` environment variable.
   - Verify that folder helpers (e.g. `get_chapters_dir()`) create directories under `projects/` subfolder.
   - Verify that file helpers (e.g. `get_outline_path()`) return correct paths but do not create any files.
   - Verify `utils.save_registry()` atomically writes valid JSON, and cleans up `.tmp` files if serialization fails (e.g. passing a non-serializable object like a set).
