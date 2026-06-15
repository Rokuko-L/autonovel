## Challenge Summary

**Overall risk assessment**: MEDIUM (due to global state concurrency risk and lack of case/reserved-name sanitization on Windows)

## Challenges

### [High] Challenge 1: Concurrency Risk via Global Module State
- **Assumption challenged**: Multiple projects can be run concurrently within a single process (e.g. multi-threaded or multi-agent execution) using `utils.py`.
- **Attack scenario**: Two concurrent threads/agents call `utils.set_project_name()` to process different novels. Because `_project_name` is stored in a single global variable (`utils._project_name`), they overwrite each other's configuration. File writes and reads are misdirected, causing severe data contamination/corruption.
- **Blast radius**: HIGH. Files for one project are written to another project's directory.
- **Mitigation**: Store the active project name in thread-local storage (`threading.local()`) or context variables (`contextvars.ContextVar`), rather than a global module-level variable.

### [Medium] Challenge 2: Case-Insensitivity Collisions on Windows
- **Assumption challenged**: Projects with names differing only in casing (e.g. "Novel" vs "novel") are isolated.
- **Attack scenario**: On Windows, the filesystem is case-insensitive. Creating project folders for "Novel" and "novel" points to the same physical directory. If they run concurrently or sequentially, they will overwrite each's files.
- **Blast radius**: MEDIUM. Silent data overwriting.
- **Mitigation**: Canonicalize all project names to lowercase, or check if folders exist with case-insensitive matches and reject if they collide.

### [Low] Challenge 3: Windows Reserved Device Names
- **Assumption challenged**: Any relative path that remains within the `projects/` directory is safe to use as a project name.
- **Attack scenario**: On Windows, names like `CON`, `PRN`, `AUX`, `NUL`, `COM1`, `LPT1` are reserved device names. Setting a project name to `CON` will cause directory creation or file operations to fail with OS errors.
- **Blast radius**: LOW/MEDIUM. Application crash during project initialization.
- **Mitigation**: Validate the project name against Windows reserved device names and raise a `ValueError` if matched.

## Stress Test Results

- **Concurrency test (`test_concurrent_project_names`)** → Interleaving threads setting distinct project names → Global state pollution and name mismatch detected (successes < 5) → **PASS** (reproduced limitation)
- **File blocking helper directory (`test_directory_existence_checks_file_blocking`)** → File `chapters` blocks directory creation → Throws `FileExistsError` → **PASS**
- **Registry directory block (`test_save_registry_directory_blocking`)** → Directory `registry.json` blocks file saving → Throws Exception and cleans up `.tmp` file → **PASS**
- **Format prompt ordering dependency (`test_format_prompt_order_dependency`)** → Kwargs insertion order affects recursive formatting output → Output depends on order → **PASS** (confirmed dependency)
- **Get novel title malformed JSON (`test_get_novel_title_malformed_json`)** → Invalid JSON in `state.json` → Gracefully falls back to `"the novel"` → **PASS**
- **Path traversal prevention (`test_project_name_path_traversal`)** → Project name `../traversal_test` → Throws `ValueError` → **PASS**

## Unchallenged Areas

- **Anthropic API Call (`call_anthropic`)** — Out of scope. Requires live network and API keys, which are not available under the CODE_ONLY network mode constraint.
