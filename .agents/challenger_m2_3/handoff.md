# Handoff Report

## 1. Observation
- **Unit test suite `scratch/test_utils.py`**:
  Ran using `python -m unittest scratch/test_utils.py`.
  Output:
  ```
  Ran 12 tests in 0.125s
  OK
  ```
- **Stress test suite `scratch/test_utils_stress.py`**:
  Ran using `python -m unittest scratch/test_utils_stress.py`.
  Output:
  ```
  Ran 6 tests in 0.069s
  OK
  ```
- **File list verification**:
  No files were created directly under the root codebase directory (e.g. `d:\Tugas\LLM\autonovel`) during the execution of the tests.
- **Path isolation implementation (`utils.py` lines 36-47 and 61-71)**:
  Uses `.resolve()` to normalize paths, then validates relative status to `projects_root`:
  ```python
  try:
      is_rel = proposed_dir.is_relative_to(projects_root)
  except AttributeError:
      is_rel = proposed_dir == projects_root or projects_root in proposed_dir.parents
  if not is_rel or proposed_dir == projects_root:
      raise ValueError("Invalid project name: path isolation violation")
  ```
- **E2E/Integration test suites (`test_path_contamination.py` and `test_multi_project.py`)**:
  Showed 4 failures in `test_path_contamination.py` and 17 failures in `test_multi_project.py` because the orchestrator script `run_pipeline.py` has not yet been fully refactored for Milestones 3/4, causing the mock test shims to fail under Windows or when direct module variables (e.g. `STATE_FILE`) are not synchronized before run.

## 2. Logic Chain
- **All tests in `test_utils.py` and `test_utils_stress.py` pass**: Handled by executing the unittest runner which returned exit code 0 (OK).
- **No root pollution**: Verified by the `setUp`/`tearDown` in `test_utils_stress.py` that compares root contents before and after runs, excluding `projects` and `scratch`. No unexpected file creation was observed in the root.
- **Path isolation is strictly preserved**:
  - `utils.set_project_name()` and `utils.get_project_dir()` resolve the target path relative to `projects_root`.
  - A path traversal input (e.g., `../traversal`) resolves outside `projects_root`, setting `is_rel` to `False` and triggering `ValueError`.
  - Absolute path inputs (`C:/Windows`, `/etc`) override the left operand in `Path` joining, resolving outside `projects_root`, setting `is_rel` to `False` and triggering `ValueError`.
  - Empty string (`""`) or dot (`"."`) resolve exactly to `projects_root`, triggering the `proposed_dir == projects_root` guard, which raises `ValueError`.

## 3. Caveats
- Concurrency issues: The global state memory of project name (`_project_name`) is NOT thread-safe. Concurrent invocations in multi-threaded workflows will corrupt settings (as demonstrated by `test_concurrent_project_names` in `test_utils_stress.py`).
- Case-insensitivity: On Windows, `Novel` and `novel` refer to the same folder, but python `Path` objects might compare unequal/equal depending on how they are created. `test_f3_boundary_case_sensitivity` assumes case-sensitive path comparison which fails on Windows due to `WindowsPath` case-insensitive equality rules.

## 4. Conclusion
The updated `utils.py` successfully fulfills its Milestone 2 contracts: all unit and stress tests pass, path isolation is strictly enforced through `ValueError` raising on traversal attempts, and there is no root pollution caused by the utility functions.

## 5. Verification Method
To independently verify the observations:
1. Run:
   ```cmd
   python -m unittest scratch/test_utils.py
   python -m unittest scratch/test_utils_stress.py
   ```
2. Inspect the codebase root directory (`d:\Tugas\LLM\autonovel`) to ensure no temp files were written there.
3. Validate that a path traversal attempt raises `ValueError` by running:
   ```cmd
   python -c "import utils; utils.set_project_name('../outside')"
   ```
   This command must exit with a `ValueError`.
