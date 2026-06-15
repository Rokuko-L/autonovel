# Changes Report - Milestone 2 Refactoring of utils.py

## Modified Files
- `utils.py` - Core utilities module updated to implement Milestone 2 requirements.

## Added Files
- `scratch/test_utils.py` - Unit test suite to verify the changes to `utils.py`.

## Summary of Changes

### 1. Root Directory Resolution (`get_root_dir`)
- Added `get_root_dir() -> Path` which resolves the root of the workspace by walking up parent directories starting from `__file__` until it finds either `pyproject.toml` or `.env`.
- Caches the resolved path in the module-level variable `_root_dir` for efficiency.
- Raises a `RuntimeError` if it reaches the file system root without finding `pyproject.toml` or `.env`.
- Replaced the hardcoded `BASE_DIR = Path(__file__).resolve().parent` definition with `BASE_DIR = get_root_dir()` for backward compatibility.

### 2. Project Name Configuration (`set_project_name` & `get_project_name`)
- Introduced `_project_name` global variable.
- Added `set_project_name(name: str)` to set `_project_name` value.
- Added `get_project_name() -> str` which returns `_project_name`, falling back to `AUTONOVEL_PROJECT` env var, and then defaulting to `"default"`.
- Added `get_project_dir() -> Path` helper to obtain `projects/<project_name>/` path.

### 3. Atomic Registry State Writer (`save_registry`)
- Added `save_registry(data: dict, path: Path)` to write the registry data atomically.
- Serialization and writing are done first to a `.tmp` file (e.g., `registry.json.tmp`).
- If serialization or writing fails, the `.tmp` file is unlinked in the `except` block and the exception is re-raised.
- Uses `os.replace` to perform an atomic swap/replace of the target path with the temporary file, ensuring compatibility on both POSIX and Windows.

### 4. Dynamic Folder Helpers (with side effects)
Added functions that return `Path` objects under `projects/<project_name>/` and call `.mkdir(parents=True, exist_ok=True)` to guarantee their existence:
- `get_chapters_dir() -> Path`
- `get_edit_logs_dir() -> Path`
- `get_eval_logs_dir() -> Path`
- `get_briefs_dir() -> Path`
- `get_typeset_dir() -> Path`

### 5. Pure File Helpers (without side effects)
Added functions that return `Path` objects without mutating the filesystem (no creation side effects):
- `get_outline_path() -> Path` -> `projects/<project_name>/outline.md`
- `get_state_path() -> Path` -> `projects/<project_name>/state.json`
- `get_results_path() -> Path` -> `projects/<project_name>/results.tsv`
- `get_registry_path() -> Path` -> `projects/registry.json`
- `get_world_path() -> Path` -> `projects/<project_name>/world.md`
- `get_voice_path() -> Path` -> `projects/<project_name>/voice.md`
- `get_characters_path() -> Path` -> `projects/<project_name>/characters.md`
- `get_canon_path() -> Path` -> `projects/<project_name>/canon.md`
- `get_manuscript_path() -> Path` -> `projects/<project_name>/manuscript.md`
- `get_reviews_path() -> Path` -> `projects/<project_name>/reviews.md`
- `get_arc_summary_path() -> Path` -> `projects/<project_name>/arc_summary.md`

### 6. Refactored `get_novel_title`
- Updated `get_novel_title()` to read the state path dynamically using `get_state_path()` instead of a hardcoded parent directory.
- Imported `json` globally for consistent use across the file.

---

## Verification Results

1. **Compilation Check**:
   ```bash
   python -m py_compile utils.py
   ```
   *Result*: Compiled without warnings or errors.

2. **Basic Import Check**:
   ```bash
   python -c "import utils; print(utils.get_root_dir()); print(utils.get_chapters_dir())"
   ```
   *Result*:
   ```
   D:\Tugas\LLM\autonovel
   D:\Tugas\LLM\autonovel\projects\default\chapters
   ```

3. **Robust Unit Tests**:
   Ran the newly created unit test suite `scratch/test_utils.py`:
   ```bash
   python -m unittest scratch/test_utils.py
   ```
   *Result*:
   ```
   .......
   ----------------------------------------------------------------------
   Ran 7 tests in 0.025s

   OK
   ```
   All tests covering root directory resolution, configuration getter/setters, atomic write with rollback, folder helper side-effects, pure path helper side-effect absence, and refactored title resolution passed cleanly.
