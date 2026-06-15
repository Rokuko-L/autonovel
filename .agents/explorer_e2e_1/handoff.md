# E2E Test Strategy Handoff Report

## 1. Observation
*   Analyzed `utils.py` located at `d:\Tugas\LLM\autonovel\utils.py` and saw that its path resolution is currently static and writes directly to the workspace root:
    ```python
    BASE_DIR = Path(__file__).resolve().parent
    ```
*   Analyzed `run_pipeline.py` at `d:\Tugas\LLM\autonovel\run_pipeline.py` and observed that it does not currently accept the `--project` argument or configure project isolation directories (lines 1081-1097):
    ```python
    parser.add_argument(
        "--from-scratch", action="store_true",
        help="Reset state and start from seed.txt")
    ...
    ```
*   Observed proposed contracts in `PROJECT.md` at `d:\Tugas\LLM\autonovel\PROJECT.md` (lines 38-64):
    ```markdown
    - `utils.get_root_dir() -> Path`
    - `utils.set_project_name(name: str)`
    - `utils.get_project_name() -> str`
    - `utils.save_registry(data: dict, path: Path)`
    ...
    ```
*   Verified that the `scratch` directory does not yet exist in `d:\Tugas\LLM\autonovel\`.

## 2. Logic Chain
1.  **Workspace Root Detection (F1)**: From `utils.py`'s imports and directory layout, walking up parent directories is necessary to find a root marked by `pyproject.toml` or `.env` and caching prevents redundant IO.
2.  **State Config and Fallback (F2)**: To ensure multiple concurrent runs, storing the project name in global memory with fallback to environment variables and defaults isolates session namespaces.
3.  **Path Resolution Helpers (F3)**: Pure helpers must return paths with zero side effects to prevent unwanted disk changes, whereas dynamic folder helpers must guarantee directory creation on demand.
4.  **Atomic Registry Writes (F4)**: Registry updates require writing to a `.tmp` file and renaming (`os.replace`) to ensure updates are atomic. Clean-up of `.tmp` upon JSON serialization errors prevents workspace clutter.
5.  **CLI argument & lifecycle (F5)**: The `--project` argument must configure `utils` project state and propagate it to all sub-generator scripts using environment variables. Lifecycle state (`state.json` resume and reset) is managed relative to `projects/<project_name>/`.
6.  **Git guards (F6)**: Isolating git repositories requires checking and initializing `.git` in the project subfolder and adding ignore rules to prevent pollution.
7.  **Script Routing & Typeset Sandbox (F7)**: Subprocess execution of `tectonic` must run with `cwd` set to the project typeset folder to sandbox auxiliary file outputs.

## 3. Caveats
*   The tests are designed against specifications before full code implementation. Minor adjustments may be needed once implementation details of `utils.py` and `run_pipeline.py` are finalized.
*   Assumes Tectonic is available on the system path for PDF compilation; if not, tests should log a warning and pass.

## 4. Conclusion
We have created a comprehensive, 4-tier E2E testing strategy plan in `analysis.md` inside our working directory (`d:\Tugas\LLM\autonovel\.agents\explorer_e2e_1/`). This plan details how to test all F1-F7 features in both `scratch/test_multi_project.py` (focusing on multi-project concurrency, lifecycle, and typesetting sandbox) and `scratch/test_path_contamination.py` (focusing on root detection, path contamination, atomic writes, and git guards).

## 5. Verification Method
1.  Inspect the testing plan file: `d:\Tugas\LLM\autonovel\.agents\explorer_e2e_1\analysis.md`.
2.  Verify that it defines test cases for all Tiers 1-4 with feature coverage >=5, boundary cases >=5, cross-feature combinations, and 5 real-world scenarios.
3.  Ensure the file maps the implementation of these test cases to `scratch/test_multi_project.py` and `scratch/test_path_contamination.py`.
