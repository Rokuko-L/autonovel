# Handoff Report: Milestone 2 Core Path & Config Refactoring (utils.py)

This report details the findings and designs for refactoring `utils.py` to support dynamic paths and project configurations.

---

## 1. Observation

*   **Current State of `utils.py`**:
    *   File Path: `d:\Tugas\LLM\autonovel\utils.py`
    *   Observed that `utils.py` contains basic Anthropic API calls, prompt formatting, and a title resolver `get_novel_title()`.
    *   `get_novel_title()` has a hardcoded path relative to `__file__`:
        ```python
        92:     state_path = __import__("pathlib").Path(__file__).parent / "state.json"
        ```
    *   No dynamic paths or active project name configuration currently exist in `utils.py`.

*   **Requirements**:
    *   File Path: `d:\Tugas\LLM\autonovel\PROJECT.md` and `d:\Tugas\LLM\autonovel\.agents\ORIGINAL_REQUEST.md` (Lines 12-18).
    *   "R1. Core Path & Configuration Refactoring (`utils.py`):
        *   Implement a robust `get_root_dir()` function that walks up parent folders from `__file__` to find `pyproject.toml` or `.env`. Raise `RuntimeError` if not found.
        *   Implement explicit active project configuration state (`utils.set_project_name(name)` and `utils.get_project_name()`) with `AUTONOVEL_PROJECT` env variable fallback.
        *   Define dynamic path helpers for all folders (`get_chapters_dir()`, `get_edit_logs_dir()`, etc.) which ensure the directories exist.
        *   Define dynamic path helpers for all file paths (`get_outline_path()`, `get_state_path()`, etc.) that are pure functions returning `Path` objects with no file creation side effects.
        *   Implement an atomic write function `save_registry(data, path)` which writes to `.tmp` and renames atomically, cleaning up the `.tmp` file *only* if the JSON serialization fails."

*   **Project Root Sentinel**:
    *   `pyproject.toml` exists in the root directory: `d:\Tugas\LLM\autonovel\pyproject.toml`.

---

## 2. Logic Chain

1.  **Finding Project Root**:
    *   Starting at `__file__` (which resolves to `utils.py` inside the root folder) and walking up through directory parents will encounter `pyproject.toml` at the project root `d:\Tugas\LLM\autonovel`.
    *   Caching the resolved directory in `_root_dir` prevents redundant filesystem lookups for every subsequent call.

2.  **Configuring Active Project Name**:
    *   An in-memory module-level global variable `_project_name` is appropriate for managing session state in a single execution pipeline.
    *   The retrieval logic checks `_project_name`, then `os.environ.get("AUTONOVEL_PROJECT")`, and falls back to `"default"`.

3.  **Dynamic Paths Resolution**:
    *   All project files and folders resolve under `projects/<project_name>/`.
    *   A common `get_project_dir() -> Path` helper resolving to `get_root_dir() / "projects" / get_project_name()` simplifies path building.
    *   **Folder helpers** must ensure existence, so calling `.mkdir(parents=True, exist_ok=True)` on the paths before returning them satisfies the side-effect constraint.
    *   **File helpers** must be pure, so returning the `Path` object without calling any file/folder creation methods satisfies the pure function constraint.
    *   The registry file itself is located at `get_root_dir() / "projects" / "registry.json"` (shared across all projects).

4.  **Atomic Writing**:
    *   Using `.tmp` files and then performing an atomic rename via `os.replace` prevents partial or corrupted writes.
    *   If `json.dump` fails (raises an exception during serialization), a `try...except` block catches the error, deletes the `.tmp` file using `.unlink()`, and propagates the error.

5.  **Internal Dependency**:
    *   `get_novel_title()` currently uses `__file__` to read `state.json`. To prevent path contamination and ensure project isolation, it must be refactored to use the new `get_state_path()`.

---

## 3. Caveats

*   **Concurrency**: Global in-memory variables are not thread-safe if multiple project sessions are run concurrently within the *same* Python process. Since the Autonovel orchestrator (`run_pipeline.py`) runs as a single-threaded CLI tool, thread-safety is currently not a concern.
*   **Target Filesystem**: The atomic rename relies on `os.replace`. Both `projects/` and the temporary file must reside on the same filesystem volume. This is standard behavior as both are written inside the `projects/` directory hierarchy.

---

## 4. Conclusion

The design for refactoring `utils.py` completely satisfies the specifications for Milestone 2. Implementing the proposed contract (as documented in `analysis.md`) will enable isolated project sessions and prevent any contamination of the root directory.

---

## 5. Verification Method

To verify the refactored `utils.py`, the implementer should create a temporary test script (e.g. `scratch/test_utils_refactor.py`) containing the following assertions:

1.  **Root Directory**: Assert that `utils.get_root_dir()` returns the path containing `pyproject.toml` and does not raise an error.
2.  **Project State**: Assert that `utils.get_project_name()` defaults to `"default"`. Call `utils.set_project_name("test_project")` and assert that `utils.get_project_name()` returns `"test_project"`.
3.  **Environment Fallback**: Clear `_project_name` to `None`, set `os.environ["AUTONOVEL_PROJECT"] = "env_project"`, and assert that `utils.get_project_name()` returns `"env_project"`.
4.  **Folder Helpers**: Assert that calling folder helpers (like `get_chapters_dir()`) creates the corresponding directory under `projects/test_project/` if it does not exist.
5.  **File Helpers**: Assert that calling file helpers (like `get_outline_path()`) returns the correct `Path` object but does *not* create the file or directory.
6.  **Atomic Registry Update**: Call `utils.save_registry()` with valid data and verify the file is created. Call it with non-serializable data (e.g., containing a `set`), assert that an exception is raised, and verify that no `.tmp` file remains in the directory.
