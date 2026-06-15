# Handoff Report — explorer_e2e_2

## 1. Observation
We observed the following relevant details from the Autonovel codebase:
- In `utils.py` (line 9):
  ```python
  BASE_DIR = Path(__file__).resolve().parent
  ```
  And in `run_pipeline.py` (lines 43-49):
  ```python
  BASE_DIR = Path(__file__).resolve().parent
  STATE_FILE = BASE_DIR / "state.json"
  RESULTS_FILE = BASE_DIR / "results.tsv"
  CHAPTERS_DIR = BASE_DIR / "chapters"
  BRIEFS_DIR = BASE_DIR / "briefs"
  EDIT_LOGS_DIR = BASE_DIR / "edit_logs"
  EVAL_LOGS_DIR = BASE_DIR / "eval_logs"
  ```
  These constants are currently static and hardcoded to the codebase root, rather than being determined dynamically based on an active project configuration.
- In `run_pipeline.py` (lines 166-174):
  ```python
  def git_add_commit(message: str) -> str:
      """Stage all changes and commit. Returns short hash or empty string."""
      run_tool("git add -A")
      result = run_tool(f'git commit -m "{message}" --allow-empty')
  ```
  Git commands currently target the root repository, which risks contaminating the main codebase history with local project changes.
- In `run_pipeline.py` (lines 845-851):
  ```python
  if shutil.which("tectonic"):
      step("Typesetting PDF with tectonic...")
      result = run_tool("tectonic typeset/novel.tex", timeout=300)
  ```
  Tectonic is run from the workspace root directory rather than within the specific typesetting subfolder of the project.
- In `run_pipeline.py` (lines 1081-1097):
  The command-line arguments do not contain a `--project` parameter, and there is no registry logic.

---

## 2. Logic Chain
1. **Multi-Project Isolation**: Because paths are hardcoded to the workspace root, multiple novels/sessions cannot run concurrently without overwriting files. Thus, we need tests to verify that setting different project names isolates all generated files. This is mapped to `scratch/test_multi_project.py` under the CLI, registry, and concurrency tests.
2. **Path Containment & Security**: Because git operations and typesetting currently run in the workspace root, they can leak file changes or contaminate the main repository. Thus, we need tests to verify that no files are written outside of `projects/<project_name>/` (except `projects/registry.json`), that Tectonic execution occurs in a sandboxed `cwd`, and that git repos are initialized and committed locally within each project. This is mapped to `scratch/test_path_contamination.py`.
3. **Robust Lifecycle**: Resuming and starting from scratch are critical behaviors. Tests must verify that `--from-scratch` correctly wipes and resets only the targeted project's state, and that omitting it correctly loads state from the project's `state.json` to resume the pipeline. This is mapped to `scratch/test_multi_project.py`.

---

## 3. Caveats
- **Pending Implementation**: The features F1-F7 are not yet implemented in the codebase. Therefore, running the proposed tests on the current code will result in test failures.
- **CODE_ONLY Testing Constraints**: In a network-isolated environment, calls to the Anthropic API (e.g. `utils.call_anthropic`) will fail or hang. The test scripts must mock these calls to return mock strings.
- **External Dependencies**: The tests must mock the presence or behavior of `tectonic` and `git` command outputs if they are missing or unconfigured on the testing machine.

---

## 4. Conclusion
We have formulated a comprehensive 4-tier testing strategy consisting of:
- **Tier 1 (Feature Coverage)**: 35 tests (5 per feature F1-F7).
- **Tier 2 (Boundary & Corner Cases)**: 35 tests (5 per feature F1-F7).
- **Tier 3 (Cross-feature Combinations)**: 5 pairwise integration scenarios.
- **Tier 4 (Real-World Scenarios)**: 5 end-to-end user workflows.

This strategy is split between two test scripts:
1. `scratch/test_multi_project.py`: Project CLI, state lifecycle, atomic registry, and multi-project concurrency.
2. `scratch/test_path_contamination.py`: Workspace root detection, folder/file path helpers, git guards, and sandboxed typesetting.

The detailed blueprints and plans are written to `d:\Tugas\LLM\autonovel\.agents\explorer_e2e_2\analysis.md`.

---

## 5. Verification Method
To verify the E2E testing strategy:
1. Inspect the detailed plan and code blueprints in `analysis.md`.
2. Once the implementer implements features F1-F7 and writes `scratch/test_multi_project.py` and `scratch/test_path_contamination.py` as described in `analysis.md`, run:
   ```powershell
   pytest scratch/test_multi_project.py
   pytest scratch/test_path_contamination.py
   ```
3. The tests should pass and confirm absolute multi-project isolation and path containment.
