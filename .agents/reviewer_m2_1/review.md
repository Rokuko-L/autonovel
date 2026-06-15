# Quality and Adversarial Review — utils.py Refactoring

## Review Summary

**Verdict**: REQUEST_CHANGES

The refactored `utils.py` implements the interface contracts and baseline features required for Milestone 2. The unit tests in `scratch/test_utils.py` and stress tests in `scratch/test_utils_stress.py` run and pass. However, there are significant robustness issues and a critical path isolation vulnerability that must be resolved. Specifically, `utils.py` lacks validation to prevent path traversal, allowing a project name to escape the `projects/` directory. Furthermore, the unit and stress tests assert that these vulnerabilities/limitations exist rather than verifying that the system guards against them.

---

## Findings

### [Critical] Finding 1: Path Isolation Boundary Violation via Path Traversal

- **What**: `utils.set_project_name` allows arbitrary string inputs, including those with path traversal sequences (e.g., `../` or absolute paths).
- **Where**: `utils.py`, lines 36-39 (`set_project_name`) and lines 53-55 (`get_project_dir`). Also see `scratch/test_utils_stress.py`, lines 155-165 (`test_project_name_path_traversal`).
- **Why**: If a project name containing path traversal sequences is provided (e.g., `../../leaked_project`), `get_project_dir()` resolves to a path outside the `projects/` directory. This allows writing, reading, and creating folders and files directly in the root workspace or arbitrary directory paths. This directly violates the requirement: "Path isolation and no leaking files outside projects/."
- **Suggestion**: Sanitize and validate the project name in `set_project_name()` to ensure the resolved project directory remains strictly a subdirectory of `projects/`. E.g.:
  ```python
  def set_project_name(name: str):
      """Set the active project name in global configuration memory with path isolation guards."""
      projects_root = (get_root_dir() / "projects").resolve()
      proposed_dir = (projects_root / name).resolve()
      if not proposed_dir.is_relative_to(projects_root):
          raise ValueError(f"Path isolation violation: project name '{name}' escapes projects/ directory")
      global _project_name
      _project_name = name
  ```
  The test `test_project_name_path_traversal` in `scratch/test_utils_stress.py` must be updated to expect a `ValueError` rather than asserting that the traversal succeeds.

### [Major] Finding 2: Unhandled OS Exceptions in get_novel_title()

- **What**: `get_novel_title()` throws uncaught `PermissionError` or `OSError` if `state.json` is a directory instead of a file.
- **Where**: `utils.py`, lines 232-242 (`get_novel_title`).
- **Why**: The helper `get_novel_title()` catches only `json.JSONDecodeError` and `KeyError`. If `state.json` exists but is a directory (or has permission issues), calling `state_path.read_text()` throws an unhandled OS error, causing the pipeline helper to crash.
- **Suggestion**: Use `is_file()` to check if the path points to a file, and catch `OSError` to fall back to the default title `"the novel"` gracefully. E.g.:
  ```python
  def get_novel_title():
      state_path = get_state_path()
      if state_path.is_file():
          try:
              state = json.loads(state_path.read_text(encoding="utf-8"))
              if "title" in state:
                  return state["title"]
          except (json.JSONDecodeError, KeyError, OSError):
              pass
      return "the novel"
  ```
  Update `test_get_novel_title_directory_error` in `scratch/test_utils.py` to expect `"the novel"` instead of expecting a raised exception.

### [Minor] Finding 3: Template Replacement Ordering Dependency in format_prompt

- **What**: `format_prompt` performs sequential string replacement on placeholders, causing ordering-dependent replacement outputs.
- **Where**: `utils.py`, lines 245-250 (`format_prompt`).
- **Why**: Replacing placeholders one by one using a loop can lead to incorrect results if replacement values themselves contain placeholder braces matching other keys.
- **Suggestion**: Use a single-pass regex-based formatter to substitute all placeholders in a single pass to eliminate keyword ordering dependencies.

---

## Adversarial Stress Test Challenges

### [High] Challenge 1: Concurrency and Thread-Safety Limitation

- **Assumption challenged**: Multiple pipeline sessions can be safely run concurrently within the same Python process.
- **Attack scenario**: Two threads set different active project names concurrently. Since `_project_name` is stored in a single module-level global variable, the threads overwrite each other's project configuration memory.
- **Blast radius**: Low-Medium (if run in separate OS processes, it is safe; if run within a multithreaded daemon, it results in cross-project data pollution).
- **Mitigation**: Recommend documenting that concurrent runs must occur in separate OS processes (e.g., CLI commands), or refactoring `utils.py` to store configuration in context-local variables (e.g., `contextvars.ContextVar`).

---

## Verified Claims

- **Syntax correctness of utils.py** → verified via `python -m py_compile utils.py` → **PASS**
- **Unit test suite completion** → verified via `python -m unittest scratch/test_utils.py` → **PASS** (12/12 tests passed)
- **Stress test suite completion** → verified via `python -m unittest scratch/test_utils_stress.py` → **PASS** (6/6 tests passed, though test asserts path isolation escapes)

---

## Coverage Gaps

- **pytest Environment** — `scratch/test_multi_project.py` depends on `pytest`, which is not installed in the environment. Thus, multi-project E2E path routing could not be fully run via unittest.
  - Risk Level: Medium
  - Recommendation: Ensure that dependencies like `pytest` are either installed or rewritten to use standard `unittest` framework to verify multi-project integration.

---

## Unverified Items

- **E2E Pipeline Execution** — Running the entire pipeline `run_pipeline.py` with multi-project CLI arguments was out of scope for the utility file review.
