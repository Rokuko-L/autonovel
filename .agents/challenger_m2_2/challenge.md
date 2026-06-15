# Challenge Report — utils.py

## Challenge Summary

**Overall risk assessment**: MEDIUM

While `utils.py` contains clean, well-refactored helpers for path operations and API integration, it exhibits some design and robustness limitations under stress conditions. The primary areas of concern are concurrent state access, filesystem collisions, and narrow exception handling during configuration parsing.

---

## Challenges

### [High] Challenge 1: Lack of Thread Safety for Project Context

- **Assumption challenged**: Sequential/single-threaded execution is guaranteed for project operations.
- **Attack scenario**: Multiple concurrent tasks or worker threads set the active project using `set_project_name(name)`. Because the active project name is stored in a simple global variable `_project_name`, setting it in one thread instantly overwrites the active project for all other concurrent threads.
- **Blast radius**: High. Direct data pollution where files belonging to one project (e.g. chapters, edit logs) are written into a different project directory.
- **Mitigation**: Store configuration context in thread-local storage (`threading.local()`) or context variables (`contextvars.ContextVar`).

### [Medium] Challenge 2: Incomplete Error Handling in `get_novel_title`

- **Assumption challenged**: The file `state.json` is either non-existent or a readable text file.
- **Attack scenario**: If a path or folder collision makes `state.json` a directory (or if the system revokes read permissions on the file), `state_path.exists()` is `True`, but `state_path.read_text()` throws a `PermissionError`/`OSError`. Since the `try/except` block only catches `(json.JSONDecodeError, KeyError)`, this unhandled error crashes the execution of `get_novel_title()`.
- **Blast radius**: Medium. Halts execution during title retrieval, which is frequently used across logging and reporting modules.
- **Mitigation**: Broaden the exception catching in `get_novel_title` to catch `OSError` and other filesystem-related exceptions.

### [Medium] Challenge 3: Unhandled Directory Creation Collisions

- **Assumption challenged**: Folder helpers (e.g. `get_chapters_dir()`) can always safely run `mkdir(exist_ok=True)`.
- **Attack scenario**: If a normal file already exists with the name of a folder helper (e.g., a file named `chapters` exists under the active project directory), the helper raises `FileExistsError` when trying to create the directory.
- **Blast radius**: Medium. Will crash execution paths that rely on setting up workspace directory paths.
- **Mitigation**: Verify if the path exists and is a file before running `mkdir`, raising a clean configuration error rather than a low-level filesystem crash.

### [Low] Challenge 4: Sequential Replacement Order Side-Effects in `format_prompt`

- **Assumption challenged**: Placeholder replacement is order-independent.
- **Attack scenario**: Placeholders are replaced sequentially in key-insertion order. If a value in `kwargs` contains placeholders belonging to another key (e.g. `a="{b}"` and `b="2"`), the order of keys in `kwargs` determines whether the inner placeholder is resolved.
- **Blast radius**: Low. Might cause unexpected prompts or templates.
- **Mitigation**: Use a single-pass regex replacement or standard Python formatting engines if nested replacements must be strictly avoided or resolved in a defined manner.

---

## Stress Test Results

- **`test_concurrent_project_name_modification`** → Verifies if concurrent modifications to the global `_project_name` are thread-safe. → Expected: Failure/Violation → Actual: Thread-safety violation caught successfully → **PASS** (Stress-test verified the vulnerability).
- **`test_get_novel_title_directory_error`** → Verifies that a directory at `state.json` raises an error instead of being caught gracefully. → Expected: Crash (`PermissionError`/`OSError`) → Actual: Crash correctly raised and caught by assertions → **PASS** (Stress-test verified the error-path vulnerability).
- **`test_directory_existence_checks_file_collision`** → Verifies collision behaviour when a file exists with the directory name. → Expected: `FileExistsError` raised → Actual: `FileExistsError` raised and caught by assertions → **PASS** (Stress-test verified the collision vulnerability).
- **`test_format_prompt_ordering_dependency`** → Verifies if prompt formatting output depends on the order of key-value insertion. → Expected: Outputs are different depending on `kwargs` ordering → Actual: Output mismatch verified successfully → **PASS** (Stress-test verified the replacement dependency).
- **`test_save_registry_target_is_directory`** → Verifies save registry behaviour when the destination target is a directory. → Expected: Exception raised and temp file cleaned up → Actual: Exception raised and temp file cleaned up → **PASS**.

---

## Unchallenged Areas

- **`call_anthropic` and `get_client`** — Network-dependent functions. These were not stress-tested with real HTTP requests due to the `CODE_ONLY` network constraint environment.
