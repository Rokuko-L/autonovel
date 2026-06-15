# Handoff Report - Milestone 2

## 1. Observation

Direct observations made on the codebase and task execution:

- **Original `utils.py` codebase**: View of `d:\Tugas\LLM\autonovel\utils.py` showed no project-scoping helpers or atomic serialization methods. `get_novel_title()` was hardcoded to `Path(__file__).parent / "state.json"`:
  ```python
  def get_novel_title():
      import json
      state_path = __import__("pathlib").Path(__file__).parent / "state.json"
  ```
- **Workspace Directories/Files**: File listing of `d:\Tugas\LLM\autonovel` showed root-level files such as `pyproject.toml`, `.env`, `state.json`, and directories like `chapters/`, `edit_logs/`, `eval_logs/`, `briefs/`, etc.
- **PROJECT.md**: `d:\Tugas\LLM\autonovel\PROJECT.md` defined Milestone 2 scope:
  - `utils.get_root_dir() -> Path`
  - `utils.set_project_name(name: str)`
  - `utils.get_project_name() -> str`
  - `utils.save_registry(data: dict, path: Path)`
  - Folder and File helpers mapping under `projects/<project_name>/`.
- **Refactored `utils.py` Check**:
  - Code compiled successfully: `python -m py_compile utils.py` exited with status 0.
  - Quick import check:
    ```
    D:\Tugas\LLM\autonovel
    D:\Tugas\LLM\autonovel\projects\default\chapters
    ```
  - Test Suite execution: `python -m unittest scratch/test_utils.py` completed with `OK`:
    ```
    Ran 7 tests in 0.025s
    OK
    ```

---

## 2. Logic Chain

The path from observations to implementation and verification:

1. **Root Resolution**: From the project layout in `PROJECT.md` and workspace files, `pyproject.toml` and `.env` exist at the workspace root. By using `Path(__file__).resolve().parent` as the starting point inside `utils.py` and looping upwards checking for `pyproject.toml` or `.env`, we are guaranteed to locate the root directory. To optimize, this value is cached in the module-level variable `_root_dir`.
2. **Project Context**: Defining a global module variable `_project_name = None` tracks the active project session. `set_project_name()` updates this. `get_project_name()` retrieves it, falls back to `os.environ.get("AUTONOVEL_PROJECT")`, and defaults to `"default"`.
3. **Atomic Writing**: `save_registry(data, path)` ensures reliability by writing to `path.with_suffix(".tmp")` first. If json serialization or filesystem write fails, the `try-except` block captures the exception, invokes `unlink()` on the `.tmp` file, and re-raises the error. On success, `os.replace` cleanly replaces the destination path, which is an atomic operation on both POSIX and Windows.
4. **Scoping**: All dynamic folders and files are isolated under `projects/<project_name>/`.
   - Folder helpers use `mkdir(parents=True, exist_ok=True)` to create the folders dynamically.
   - Pure file helpers return path objects without mutating the filesystem.
5. **Title Lookup**: Changing `get_novel_title()` to resolve using `get_state_path()` redirects lookup to the correct project's `state.json` instead of a hardcoded root-level file.

---

## 3. Caveats

- We assumed that `projects/` and `scratch/` are the only acceptable places to write files in the workspace (excluding updates to existing files like `utils.py`).
- We didn't refactor other pipeline scripts (e.g. `run_pipeline.py` or `draft_chapter.py`) as they fall under Milestone 3 and 4, respectively.
- No other caveats.

---

## 4. Conclusion

Milestone 2 has been fully implemented in `utils.py` according to all contract specifications. The implementations are genuine, robust against failure, and fully verified by unit tests in `scratch/test_utils.py`.

---

## 5. Verification Method

To independently verify the changes, run:

1. **Compilation Check**:
   ```bash
   python -m py_compile utils.py
   ```
   Ensures there are no syntax errors.
2. **Verification Test Suite**:
   ```bash
   python -m unittest scratch/test_utils.py
   ```
   Verifies all 7 custom unit tests (directory structure resolution, get/set project configuration, atomic serialization & cleanup, side-effect creation logic for directories, pure path logic for files, and title resolution).
3. **Inspect Modified Files**:
   Check `utils.py` to ensure correct integration of the new functions.
