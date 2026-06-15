# Handoff Report — Milestone 2: Core Path & Config Refactoring (utils.py)

This handoff report is prepared by `explorer_m2_1` for the implementation team to proceed with Milestone 2 refactoring.

---

## 1. Observation
1. **Original `utils.py` Path Variable**:
   In `d:\Tugas\LLM\autonovel\utils.py` line 9, the base directory is hardcoded:
   ```python
   BASE_DIR = Path(__file__).resolve().parent
   ```
2. **Hardcoded State Path in `get_novel_title()`**:
   In `d:\Tugas\LLM\autonovel\utils.py` line 92, the state file is resolved as:
   ```python
   state_path = __import__("pathlib").Path(__file__).parent / "state.json"
   ```
3. **Registry and Path requirements from `PROJECT.md`**:
   `d:\Tugas\LLM\autonovel\PROJECT.md` line 39-64 details the interface contract of folder helpers (ensuring directories exist) and file helpers (pure functions).
4. **Syntax Check**:
   The proposed implementation in `d:\Tugas\LLM\autonovel\.agents\explorer_m2_1\proposed_utils.py` compiles successfully:
   ```powershell
   python -m py_compile d:\Tugas\LLM\autonovel\.agents\explorer_m2_1\proposed_utils.py
   ```
   returned successfully with no stderr output.

---

## 2. Logic Chain
1. **Observation 1 & 2** show that pathing in `utils.py` is currently hardcoded and assumes files reside in the root codebase directory.
2. To resolve this and isolate project sessions, all paths must be computed dynamically relative to a root directory (`get_root_dir()`) and the active project session name (`get_project_name()`), which falls back to environment variables and defaults (as described in **Observation 3**).
3. Therefore, implementing `get_root_dir()`, `set_project_name()`, `get_project_name()`, dynamic folder helpers (with side effects), and pure file helpers in `utils.py` (as done in `proposed_utils.py`) satisfies the Milestone 2 design contracts.

---

## 3. Caveats
- The `scratch/` test directory does not exist yet (Milestone 1 is concurrently IN_PROGRESS), so dynamic behavior could not be validated against E2E test runs.
- Assumptions are made that files such as `results.tsv` in `run_pipeline.py` correspond to `get_results_path()` helper.

---

## 4. Conclusion
The proposed refactored structure in `proposed_utils.py` successfully designs and implements all Milestone 2 interface contracts and path helper requirements. This implementation is ready to be written to `utils.py` once Milestone 1 tests are set up or as decided by the implementer.

---

## 5. Verification Method
- **Syntax Check**: Compile the proposed script:
  ```powershell
  python -m py_compile d:\Tugas\LLM\autonovel\.agents\explorer_m2_1\proposed_utils.py
  ```
- **Inspect File**: Verify the interface definitions in `proposed_utils.py` match those in `PROJECT.md`.
- **Invalidation Condition**: If dynamic folder helpers fail to create parent directories on demand or file helpers create files/folders (violating pure function contract), this design is invalidated.
