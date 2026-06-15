# Changes Report

## Files Modified
- `utils.py`:
  - Added path isolation guards in `set_project_name(name)` and `get_project_dir()`. The guards resolve the projects root directory (`get_root_dir() / "projects"`) and the proposed project directory, verifying that the proposed directory is relative to the projects root and not equal to it. If these checks fail, a `ValueError` is raised.
  - In `get_novel_title()`, updated the check from `state_path.exists()` to `state_path.is_file()` and caught `OSError` (along with `json.JSONDecodeError` and `KeyError`) to return the fallback title `"the novel"` gracefully.
- `scratch/test_utils.py`:
  - Updated `test_get_novel_title_directory_error` to assert that `utils.get_novel_title()` returns `"the novel"` instead of raising an exception when `state.json` is a directory.
- `scratch/test_utils_stress.py`:
  - Updated `test_project_name_path_traversal` to assert that calling `utils.set_project_name("../traversal_test")` raises a `ValueError`.

## Verification Status
- Run commands:
  - `python -m unittest scratch/test_utils.py`
  - `python -m unittest scratch/test_utils_stress.py`
- Result: **All tests passed (18/18)**
