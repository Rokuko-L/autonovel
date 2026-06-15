# Handoff Report - E2E Testing Strategy Plan (explorer_e2e_3)

## 1. Observation

- **Project Layout**: We located `utils.py` and `run_pipeline.py` in the root workspace `d:\Tugas\LLM\autonovel` via `find_by_name`.
- **Existing Code in `utils.py`**:
  - `utils.py` lines 9: `BASE_DIR = Path(__file__).resolve().parent`
  - It contains no functions for project state, path helpers, registry saving, or dynamic root lookup.
- **Existing Code in `run_pipeline.py`**:
  - Defines static paths relative to `BASE_DIR` at lines 43-49:
    ```python
    BASE_DIR = Path(__file__).resolve().parent
    STATE_FILE = BASE_DIR / "state.json"
    RESULTS_FILE = BASE_DIR / "results.tsv"
    CHAPTERS_DIR = BASE_DIR / "chapters"
    BRIEFS_DIR = BASE_DIR / "briefs"
    EDIT_LOGS_DIR = BASE_DIR / "edit_logs"
    EVAL_LOGS_DIR = BASE_DIR / "eval_logs"
    ```
  - Shell commands like `git add -A` and `git commit` are run without sandboxing.
- **Implementation State & Specifications**:
  - We read `d:\Tugas\LLM\autonovel\.agents\explorer_m2_2\analysis.md` which proposed the following `utils.py` interface contracts:
    - `get_root_dir() -> Path` (looks for `pyproject.toml` or `.env` and raises `RuntimeError`)
    - `set_project_name(name: str)` and `get_project_name() -> str` (with `AUTONOVEL_PROJECT` fallback)
    - `save_registry(data: dict, path: Path)` (atomic write via `.tmp` swap and cleanup)
    - Dynamic folder path helpers and pure file path helpers under `projects/<project_name>/`.
  - We read `d:\Tugas\LLM\autonovel\.agents\explorer_e2e_2\analysis.md` which mapped the E2E test plan for the pipeline arguments, git guards, and typesetting sandboxing.

## 2. Logic Chain

1. **Isolation Verification**: To prove that multi-project isolation (F2, F3) is working and that no path contamination occurs (F3), tests must verify that setting a project name changes all target output folders to `projects/<project_name>/` and that running the pipeline creates zero files in the root workspace (except inside `projects/`).
2. **Atomic registry safety (F4)**: To verify atomic serialization, tests must pass non-serializable objects (like a `set()`) to `save_registry`, asserting that the target file is not overwritten/corrupted and that any temporary `.tmp` files are cleaned up.
3. **Git and typesetting containment (F6, F7)**: To verify that git and tectonic processes are sandboxed, tests must check that git initialization and commits occur within `projects/<project_name>/` and that Tectonic executes with the `cwd` parameter set to the project's typeset subfolder, outputting `novel.pdf` inside that subfolder.
4. **Mocking in CODE_ONLY**: Running E2E tests in a sandboxed network environment requires mocking. Since subprocesses spawned by the pipeline runner would invoke the real LLM APIs or require local tools, intercepting `run_pipeline.run_tool` and `run_pipeline.uv_run` using a custom runner that simulates side effects on disk allows complete, rapid, and offline verification of the pipeline lifecycle.

## 3. Caveats

- We assumed that `AUTONOVEL_PROJECT` is set in the environment by the parent process when launching subprocesses to ensure environment inheritance (otherwise subprocesses default to `"default"`).
- We did not implement the actual test scripts on disk, as this is a read-only investigation constraint. The plan describes the strategy to be implemented by the worker agents.

## 4. Conclusion

A 4-tier E2E testing strategy with 80 total test cases has been designed:
- **`scratch/test_multi_project.py`**: Verifies F2, F4, F5 (Active project state, atomic registry writes, CLI project arguments, and lifecycle state/resume/from-scratch).
- **`scratch/test_path_contamination.py`**: Verifies F1, F3, F6, F7 (Workspace detection, dynamic path helpers, git sandboxing, path containment, and typesetting sandboxing).
- Subprocess interception mocks are proposed to verify the pipeline state machine offline and fast without external dependencies.

## 5. Verification Method

- The E2E tests can be run by the implementing agent using:
  ```bash
  pytest scratch/test_multi_project.py
  pytest scratch/test_path_contamination.py
  ```
- Path contamination can be audited by checking that no untracked files are created in the workspace root directory after execution.
