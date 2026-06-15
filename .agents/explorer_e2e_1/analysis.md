# E2E Test Strategy Plan for Autonovel Project Isolation

This document outlines a comprehensive, 4-tier end-to-end (E2E) testing strategy for the Autonovel isolated project refactoring. The testing strategy is designed to validate features **F1 through F7** under various scenarios, including normal execution, boundary conditions, cross-feature combinations, and real-world failure states.

---

## 1. Overview of Features to Test

*   **F1: Workspace Root Detection (`get_root_dir()`)** — Dynamically walk parent folders of `__file__` to find `pyproject.toml` or `.env`. Cache the result. Raise `RuntimeError` if missing.
*   **F2: Active Project Configuration (`set_project_name()` / `get_project_name()`)** — Retrieve active project name from memory, fallback to `AUTONOVEL_PROJECT` environment variable, then default to `"default"`.
*   **F3: Path Helpers (Dynamic Folder & Pure File)** — Folder helpers (e.g. `get_chapters_dir()`) create subdirectories; pure file helpers (e.g. `get_outline_path()`) return paths without side effects.
*   **F4: Atomic Registry Writes (`save_registry()`)** — Serialize and write registry JSON data via `.tmp` file and rename (`os.replace`). Clean up `.tmp` on serialization failure.
*   **F5: Pipeline Command-line Interface (`--project` & State Lifecycle)** — CLI propagation of active project name, registration in `projects/registry.json`, and handling of `from-scratch` vs `resume` states.
*   **F6: Git Guards (Root Exclusion & Project-Level Git)** — Root `.gitignore` ignores `projects/` directory; project directories initialize independent Git repositories (`git init`) and write local `.gitignore` files.
*   **F7: Script Routing & Sandboxed Typesetting** — Child processes inherit `AUTONOVEL_PROJECT` to route paths dynamically. Tectonic runs sandboxed inside the project's typesetting directory.

---

## 2. 4-Tier Testing Strategy

### Tier 1: Feature Coverage (>=5 test cases per feature)

#### Feature 1: Workspace Root Detection (`get_root_dir()`)
1.  **Case 1.1 (Standard Resolution):** Call `get_root_dir()` from the default script directory and verify it resolves to the workspace root directory.
2.  **Case 1.2 (Nested Script Resolution):** Call `get_root_dir()` from a deeply nested script location (e.g., inside `typeset/build_tex.py` or a custom subfolder) and verify it resolves to the same root.
3.  **Case 1.3 (Caching Verification):** Verify that consecutive calls to `get_root_dir()` return the cached path without executing additional file searches (can be verified by mocking `Path.exists` and checking call count).
4.  **Case 1.4 (Env Marker Fallback):** Delete `pyproject.toml` in a mock folder structure, leaving only `.env`, and verify `get_root_dir()` still successfully resolves the root.
5.  **Case 1.5 (Toml Marker Fallback):** Delete `.env` in a mock folder structure, leaving only `pyproject.toml`, and verify `get_root_dir()` still successfully resolves the root.

#### Feature 2: Active Project Configuration State
1.  **Case 2.1 (Default State):** Call `get_project_name()` when no memory or environment variable is set and verify it returns `"default"`.
2.  **Case 2.2 (Memory Setter):** Call `set_project_name("custom_proj")` and verify `get_project_name()` returns `"custom_proj"`.
3.  **Case 2.3 (Env Variable Fallback):** Set `AUTONOVEL_PROJECT="env_proj"`, keep memory unset, and verify `get_project_name()` returns `"env_proj"`.
4.  **Case 2.4 (Priority Order):** Set `AUTONOVEL_PROJECT="env_proj"` and call `set_project_name("memory_proj")`. Verify `get_project_name()` returns `"memory_proj"` (memory overrides environment).
5.  **Case 2.5 (State Reset):** Call `set_project_name(None)`, set `AUTONOVEL_PROJECT="fallback"`, and verify it falls back to the environment variable.

#### Feature 3: Path Helpers (Dynamic Folder & Pure File)
1.  **Case 3.1 (Folder Creation):** Call `get_chapters_dir()` and verify it creates `projects/default/chapters/` on disk.
2.  **Case 3.2 (Pure File Safety):** Call `get_outline_path()` and verify that it returns a valid path string but does **not** create any directory or file on-disk.
3.  **Case 3.3 (Dynamic Interpolation):** Switch active project name from `"default"` to `"proj_x"` and verify path helper outputs dynamically update (e.g., `get_chapters_dir()` now returns `projects/proj_x/chapters/`).
4.  **Case 3.4 (Parent Creation):** Call a folder helper (e.g., `get_typeset_dir()`) in a project where the `projects/<project_name>/` folder does not exist, and verify it automatically creates the intermediate parent folder.
5.  **Case 3.5 (Registry Path Resolution):** Verify `get_registry_path()` always returns `projects/registry.json` regardless of the currently active project name.

#### Feature 4: Atomic Registry Writes (`save_registry()`)
1.  **Case 4.1 (Successful Write):** Call `save_registry()` with valid dictionary data and verify that the target JSON file is created with the exact matching contents.
2.  **Case 4.2 (Temporary File Cleanup):** Verify that after a successful write, no temporary `.tmp` file remains in the directory.
3.  **Case 4.3 (Serialization Error Guard):** Call `save_registry()` with a non-serializable object (e.g., containing Python functions or sets). Assert that:
    *   An exception is raised.
    *   Any created `.tmp` file is deleted.
    *   The original registry file (if it existed) remains unchanged.
4.  **Case 4.4 (Directory Bootstrap):** Call `save_registry()` on a file path within a non-existent directory and verify the directory is automatically created and the file is written.
5.  **Case 4.5 (Atomic Swap Validation):** Verify that the swap utilizes `os.replace` (atomic file swap) to prevent partial read/write cycles.

#### Feature 5: Pipeline CLI & State Lifecycle
1.  **Case 5.1 (CLI Argument Parsing):** Execute `run_pipeline.py` with `--project test_project` and verify `utils.get_project_name()` resolves to `"test_project"`.
2.  **Case 5.2 (Registry Inclusion):** Launch a project and verify it is registered in `projects/registry.json`.
3.  **Case 5.3 (From-Scratch Clean State):** Run the pipeline with `--from-scratch` on an existing project directory and verify that all previous chapters and `state.json` are deleted, and execution restarts from the `foundation` phase.
4.  **Case 5.4 (Resume Lifecycle):** Run the pipeline without `--from-scratch` on a project with an existing state file indicating it is at the `drafting` phase. Verify it skips the `foundation` phase and resumes drafting.
5.  **Case 5.5 (Finished Lifecycle Exits):** Run the pipeline on a project with `state.json` having phase set to `"complete"` and verify it exits immediately with a completion notice without running any pipeline tools.

#### Feature 6: Git Guards
1.  **Case 6.1 (Root Ignore Rule):** Verify that the root `.gitignore` file contains a line ignoring the global `projects/` directory.
2.  **Case 6.2 (Project Git Initialization):** Launch a new project and verify that the directory contains a `.git` subdirectory.
3.  **Case 6.3 (Project Gitignore Template):** Verify that a `.gitignore` is created in `projects/<project_name>/.gitignore` containing standard project-specific ignore patterns.
4.  **Case 6.4 (Commit Isolation):** Perform a Git commit in the project directory and verify it does not appear in the root Git history.
5.  **Case 6.5 (Exclude Execution Logs):** Verify that log directories or temp files specified in the project `.gitignore` template are ignored by the local Git repository.

#### Feature 7: Script Routing & Sandboxed Typesetting
1.  **Case 7.1 (Subprocess Environment Propagation):** Verify that `run_pipeline.py` passes the `AUTONOVEL_PROJECT` environment variable to all spawned child script processes (e.g. `gen_world.py`).
2.  **Case 7.2 (Script Output Redirection):** Execute a routed script (e.g. `gen_world.py`) with `AUTONOVEL_PROJECT="routed_proj"` and verify it writes its output to `projects/routed_proj/world.md` instead of the root directory.
3.  **Case 7.3 (Typeset Working Directory):** Verify that Tectonic typesetting runs with its subprocess working directory (`cwd`) set to `projects/<project_name>/typeset/`.
4.  **Case 7.4 (LaTeX Sandbox Verification):** Verify that compiling `novel.tex` creates auxiliary files (like `.aux`, `.log`, and `.pdf`) only within `projects/<project_name>/typeset/` and does not pollute the root directory.
5.  **Case 7.5 (Routing Fail-safe):** Verify that child processes exit with a non-zero code and log a clear error if the project configuration is invalid.

---

### Tier 2: Boundary & Corner Cases (>=5 test cases per feature)

#### Feature 1: Workspace Root Detection (`get_root_dir()`)
1.  **Case 1.b1 (Missing Root Markers):** Run the script inside a directory tree that has no `pyproject.toml` or `.env` files all the way to the drive root. Assert that `RuntimeError` is raised.
2.  **Case 1.b2 (Drive Root Execution):** Run the root resolver from the drive root (e.g., `C:\` or `/`). Verify that the folder traversal terminates gracefully without an infinite loop.
3.  **Case 1.b3 (Symlinked Directories):** Run the resolver inside a symlinked workspace directory and verify that it traverses parent directories relative to the real path to find the root.
4.  **Case 1.b4 (Duplicate Workspace Markers):** Place a mock `pyproject.toml` in a subdirectory of a project. Verify that calling the root resolver from that subdirectory resolves to the nearest parent containing the marker (nested workspace behavior).
5.  **Case 1.b5 (Read-Only Parent Directory):** Simulate a parent directory with restricted read permissions and verify that the resolver handles the `PermissionError` gracefully during its upward search.

#### Feature 2: Active Project Configuration State
1.  **Case 2.b1 (Path Traversal Prevention):** Call `set_project_name("../outside")` or pass it via CLI. Verify that the system sanitizes or rejects the name to prevent writing outside the `projects/` directory.
2.  **Case 2.b2 (Empty String Fallback):** Set `AUTONOVEL_PROJECT=""` (empty string) and verify that the config resolver treats it as unset, falling back to the `"default"` project name.
3.  **Case 2.b3 (Invalid Directory Characters):** Attempt to set the project name containing characters forbidden by the OS (e.g., `*`, `?`, `:`, `|`, `<`, `>` on Windows). Verify that the system handles this gracefully, either sanitizing the name or raising an informative error.
4.  **Case 2.b4 (Extreme Project Name Length):** Set a project name of 250 characters and verify that the system either raises a validation error or gracefully handles path length restrictions.
5.  **Case 2.b5 (Thread-Safe Isolation):** Call `set_project_name()` from multiple threads within the same process and verify that thread local context or isolation is maintained if multiple pipeline threads run concurrently (or document that the design is single-threaded).

#### Feature 3: Path Helpers
1.  **Case 3.b1 (Directory Creation Permissions):** Attempt to call a folder helper in a directory where creation fails (e.g. read-only permissions on `projects/`). Verify that a `PermissionError` is raised with a meaningful error message.
2.  **Case 3.b2 (File-Folder Name Collision):** Create a regular file named `projects/my_project/chapters` and then call `get_chapters_dir()`. Verify that the system raises `FileExistsError` and handles it without crashing or deleting the user's file.
3.  **Case 3.b3 (Case Sensitivity Conflicts):** On case-sensitive filesystems, verify that switching between project names differing only by case (e.g., `novel` and `Novel`) resolves to two distinct physical directories.
4.  **Case 3.b4 (Mid-Execution Project Swap):** Verify that if the active project name is changed programmatically mid-run, subsequent calls to path helpers immediately return the updated paths without caching outdated folders.
5.  **Case 3.b5 (Unicode Paths):** Use project names with non-ASCII or Unicode characters (e.g., `novel_✨_test` or `novel_日本語`). Verify that all path helpers resolve, create, and access these folders correctly.

#### Feature 4: Atomic Registry Writes (`save_registry()`)
1.  **Case 4.b1 (Read-Only Target File):** Make the target registry file read-only and invoke `save_registry()`. Verify that the operation raises `PermissionError` and cleans up the temporary `.tmp` file.
2.  **Case 4.b2 (Directory Collision):** Create a directory named `registry.json` at the target path and call `save_registry()`. Verify that the operation fails gracefully and does not delete the directory.
3.  **Case 4.b3 (Disk Full / Interrupted Write Simulation):** Mock file writing to raise an `OSError` (simulating disk full or write interruption) midway through writing. Verify that the target registry file is **not** modified or corrupted, and that the `.tmp` file is deleted.
4.  **Case 4.b4 (Stale Temp File Recovery):** Create a stale, conflicting `registry.json.tmp` file in the directory. Run `save_registry()` and verify that the writer successfully overwrites or removes the stale `.tmp` file and completes the atomic write.
5.  **Case 5.b5 (Empty/None Data Serialization):** Attempt to write `None` or an empty dictionary to the registry. Verify that the JSON output is serialized correctly and does not write empty or corrupted files.

#### Feature 5: Pipeline CLI & State Lifecycle
1.  **Case 5.b1 (Resume Missing Project):** Run `run_pipeline.py --project missing_proj` without `--from-scratch` when `missing_proj` has no state.json. Verify that the pipeline either automatically bootstraps a new project and begins from `foundation`, or errors out with a helpful message.
2.  **Case 5.b2 (Corrupted State JSON):** Create an invalid JSON file in `projects/test_proj/state.json`. Run the pipeline in resume mode. Verify that it reports the corruption and prompts the user or exits, rather than continuing with corrupted memory.
3.  **Case 5.b3 (State Save on Interruption):** Simulate a pipeline execution receiving a keyboard interrupt or termination signal during drafting. Verify that the current state is saved to `state.json` before the process exits.
4.  **Case 5.b4 (Conflict CLI Args):** Run `run_pipeline.py --from-scratch --phase export`. Verify that the pipeline detects the conflict (from-scratch requires notes/seed, and starting at export contradicts starting from scratch) and fails fast.
5.  **Case 5.b5 (Missing Notes and Seed in From-Scratch):** Run `run_pipeline.py --from-scratch` when neither `seed.txt` is present nor `--notes` is provided. Verify that it prints a clear error message and exits with code `1`.

#### Feature 6: Git Guards
1.  **Case 6.b1 (Missing Root Git Repository):** Run the pipeline in a directory tree that is not a Git repository. Verify that the pipeline warns the user or skips Git operations gracefully rather than crashing.
2.  **Case 6.b2 (Pre-Existing Git Folder):** Run the pipeline on a project folder that already has a `.git` folder (e.g., from a manually created repository). Verify that it does not attempt to overwrite or conflict, but uses the existing repository safely.
3.  **Case 6.b3 (Git Command Unavailability):** Mock the shell environment so that the `git` command is not found. Run the pipeline and verify that it falls back to non-git operations gracefully.
4.  **Case 6.b4 (Root Gitignore Read-Only):** Make the root `.gitignore` file read-only. Verify that the pipeline does not crash when trying to verify the `projects/` ignore rule, and logs a warning instead.
5.  **Case 6.b5 (Invalid Project Git Config):** Simulate a Git initialization failure (e.g. disk write failure in `.git/`). Verify that the pipeline catches the failure and logs the error without halting non-git pipeline operations.

#### Feature 7: Script Routing & Sandboxed Typesetting
1.  **Case 7.b1 (Missing Tectonic Executable):** Simulate a system where `tectonic` is not installed. Run the export phase and verify it logs a clear warning that tectonic is missing and skips PDF compilation without raising an unhandled exception.
2.  **Case 7.b2 (Tectonic Compilation Failure):** Introduce a syntax error into `novel.tex` (e.g. unescaped symbols). Run the typesetting phase and verify that tectonic exits with a non-zero code, the error is isolated inside the project typeset folder, and the pipeline registers the warning and proceeds.
3.  **Case 7.b3 (Child Process Timeout):** Mock a routed script (e.g., `evaluate.py`) to hang indefinitely. Verify that the pipeline's timeout handler kills the child process and resumes or exits cleanly.
4.  **Case 7.b4 (Directory Path with Spaces):** Create a project named `my novel project`. Run the pipeline and verify that all subprocesses handle the spaces in the directory paths correctly without shell splitting errors.
5.  **Case 7.b5 (Subprocess Return Code Detection):** Modify a child generator script to fail with exit code `1`. Verify that `run_pipeline.py` detects this non-zero exit code, stops the pipeline execution, and saves the state.

---

### Tier 3: Cross-Feature Combinations

*   **Combination Scenario 1 (Bootstrap & Route Integration):** Tests F2 + F3 + F5 + F6 + F7.
    *   *Steps:*
        1. Run `python run_pipeline.py --project combo_project --from-scratch --genre "Sci-Fi" --notes "A spaceship story"`.
        2. Verify CLI parsed `--project` (F5) and configured the name (F2).
        3. Verify folder helpers created directories under `projects/combo_project/` (F3).
        4. Verify a local `.git` repository and `.gitignore` template were initialized (F6).
        5. Verify that spawned generator scripts (F7) wrote their outputs (like `world.md`) to the project folder instead of the root.
*   **Combination Scenario 2 (Concurrency & Atomic State Consistency):** Tests F4 + F5.
    *   *Steps:*
        1. Launch two separate instances of the pipeline: one with `--project concurrent_a` and another with `--project concurrent_b` concurrently.
        2. During their foundation phases, have both write their state files and modify the registry `projects/registry.json`.
        3. Verify that `registry.json` is successfully updated with both projects atomically (F4) without lock contentions, file corruption, or state leakage.

---

### Tier 4: Real-World Scenarios (5 Scenarios)

#### Scenario 1: Multi-Project Parallel Execution
*   **Description:** Two pipelines run concurrently on separate novels to verify complete workspace isolation.
*   **Test Script:** `scratch/test_multi_project.py`
*   **Steps:**
    1. Spawn two subprocesses executing the pipeline:
       `python run_pipeline.py --project project_alpha --from-scratch --genre "Mystery" --notes "a detective in London"`
       `python run_pipeline.py --project project_beta --from-scratch --genre "Fantasy" --notes "a wizard in a tower"`
    2. Wait for both to complete or reach drafting.
    3. Verify that `projects/project_alpha/` contains mystery planning files (world, characters, outline) and no fantasy files.
    4. Verify that `projects/project_beta/` contains fantasy planning files and no mystery files.
    5. Verify `projects/registry.json` lists both `project_alpha` and `project_beta`.
    6. Verify no novel files were written to the workspace root directory.

#### Scenario 2: Interrupted Pipeline Resume
*   **Description:** A pipeline run is aborted mid-drafting and restarted to verify state preservation and seamless resume.
*   **Test Script:** `scratch/test_multi_project.py`
*   **Steps:**
    1. Run the pipeline with `--project resume_project` and a target of 3 chapters.
    2. Terminate the process (via mock exit or signal) after Chapter 1 is completed and committed.
    3. Verify `projects/resume_project/state.json` reflects `chapters_drafted: 1` and `phase: "drafting"`.
    4. Re-run `python run_pipeline.py --project resume_project` (without `--from-scratch`).
    5. Verify that the pipeline skips the foundation phase, skips drafting Chapter 1, and starts drafting Chapter 2.

#### Scenario 3: Contamination Audit under Failure Modes
*   **Description:** A pipeline run fails due to a sub-script failure, and we verify that the failure is isolated and does not contaminate the root or other projects.
*   **Test Script:** `scratch/test_path_contamination.py`
*   **Steps:**
    1. Inject a failure into `gen_characters.py` (e.g. throw an exception when a specific env var is set).
    2. Run the pipeline: `python run_pipeline.py --project fail_project --from-scratch --genre "Drama" --notes "failed run"`.
    3. Verify the pipeline exits with a non-zero code.
    4. Audit the workspace root: assert that no temporary files or draft files were written to the root folder.
    5. Verify that `projects/fail_project/state.json` exists and records the failure or remains in the planning focus.

#### Scenario 4: Sandboxed Typesetting Validation
*   **Description:** Run the export phase to verify that Tectonic compilation runs strictly in the project subfolder sandbox.
*   **Test Script:** `scratch/test_multi_project.py`
*   **Steps:**
    1. Place a mock `build_tex.py` and `novel.tex` into `projects/typeset_project/typeset/`.
    2. Run the export phase: `python run_pipeline.py --project typeset_project --phase export`.
    3. Verify the tectonic command is executed with the working directory set to `projects/typeset_project/typeset/`.
    4. Verify that all auxiliary LaTeX files (like `.aux`, `.log`) and the output `novel.pdf` are located in `projects/typeset_project/typeset/` and not in the root directory.

#### Scenario 5: Clean Slate Reset & Git Guard Audit
*   **Description:** Verify that reset operations do not bleed into the root repository and root git remains pristine.
*   **Test Script:** `scratch/test_path_contamination.py`
*   **Steps:**
    1. Run a project named `git_audit_project`.
    2. Check the root git history (`git status` and `git log`). Ensure no files in `projects/` are tracked.
    3. Verify that running `--from-scratch` reset inside `git_audit_project` re-initializes its local Git repository and commits files there.
    4. Run `git status` at the root and verify it remains completely unchanged (clean workspace status, ignoring `projects/`).

---

## 3. Scratch Test Suite Design

The E2E test suite will be implemented in two Python files under the `scratch/` directory:

### File 1: `scratch/test_multi_project.py`

This file focuses on the multi-project lifecycle, CLI argument behavior, concurrency, and typesetting sandbox (F2, F4, F5, F7).

```python
# Design outline for scratch/test_multi_project.py
import unittest
import subprocess
import json
import os
import shutil
from pathlib import Path

class TestMultiProject(unittest.TestCase):
    def setUp(self):
        # Set up a clean, isolated environment inside projects/ for testing
        self.root_dir = Path(__file__).resolve().parent.parent
        self.projects_dir = self.root_dir / "projects"
        # Back up existing registry if present
        self.registry_path = self.projects_dir / "registry.json"
        self.registry_backup = self.projects_dir / "registry.json.bak"
        if self.registry_path.exists():
            shutil.copy2(self.registry_path, self.registry_backup)

    def tearDown(self):
        # Clean up test projects created during runs
        test_projects = ["test_alpha", "test_beta", "test_resume", "test_typeset"]
        for proj in test_projects:
            proj_path = self.projects_dir / proj
            if proj_path.exists():
                shutil.rmtree(proj_path)
        # Restore registry backup
        if self.registry_backup.exists():
            shutil.move(self.registry_backup, self.registry_path)
        elif self.registry_path.exists():
            self.registry_path.unlink()

    def test_multi_project_concurrency(self):
        """Runs two pipeline instances concurrently and verifies separation."""
        # 1. Start project test_alpha
        # 2. Start project test_beta
        # 3. Assert separate directories exist
        # 4. Assert registry contains both entries
        pass

    def test_pipeline_resume_lifecycle(self):
        """Verifies that the pipeline can resume from a saved state."""
        # 1. Create a mock project 'test_resume' with state.json at 'drafting'
        # 2. Run run_pipeline.py without --from-scratch
        # 3. Assert foundation phase is skipped
        pass

    def test_sandboxed_typesetting(self):
        """Verifies tectonic runs in the project subfolder and output is isolated."""
        # 1. Run pipeline export phase on 'test_typeset'
        # 2. Assert no typeset/novel.pdf is written to the root typeset directory
        # 3. Assert PDF is written to projects/test_typeset/typeset/
        pass
```

### File 2: `scratch/test_path_contamination.py`

This file focuses on root detection, path contamination, atomic writes, and git guards (F1, F3, F4, F6).

```python
# Design outline for scratch/test_path_contamination.py
import unittest
import os
import json
import shutil
from pathlib import Path
from unittest.mock import patch
import utils

class TestPathContamination(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent.parent
        self.projects_dir = self.root_dir / "projects"

    def test_get_root_dir_resolution(self):
        """Validates that get_root_dir resolves correctly and caches output."""
        root = utils.get_root_dir()
        self.assertEqual(root, self.root_dir)
        # Verify caching
        with patch('pathlib.Path.exists') as mock_exists:
            utils.get_root_dir()
            mock_exists.assert_not_called()

    def test_pure_vs_dynamic_path_helpers(self):
        """Verifies pure helpers don't write to disk while dynamic helpers do."""
        utils.set_project_name("test_contam")
        # Pure helper
        state_path = utils.get_state_path()
        self.assertFalse(state_path.exists())
        
        # Dynamic folder helper
        chapters_dir = utils.get_chapters_dir()
        self.assertTrue(chapters_dir.exists())
        self.assertTrue(chapters_dir.is_dir())
        
        # Clean up
        shutil.rmtree(self.projects_dir / "test_contam")

    def test_save_registry_atomic_writes(self):
        """Validates atomic swap and cleanup on serialization failures."""
        registry_path = self.projects_dir / "test_reg.json"
        
        # Serialization failure
        bad_data = {"key": set([1, 2])} # Sets are not JSON serializable
        with self.assertRaises(Exception):
            utils.save_registry(bad_data, registry_path)
            
        # Assert no .tmp file left behind and registry file does not exist
        tmp_path = registry_path.with_suffix(".json.tmp")
        self.assertFalse(tmp_path.exists())
        self.assertFalse(registry_path.exists())

    def test_git_guards_and_gitignore(self):
        """Verifies root git protection and local git initialization."""
        # 1. Assert projects/ is ignored in root .gitignore
        root_gitignore = self.root_dir / ".gitignore"
        self.assertTrue(root_gitignore.exists())
        content = root_gitignore.read_text()
        self.assertTrue("projects/" in content or "projects" in content)
        
        # 2. Assert project git init
        # Run a brief pipeline setup and check projects/my_project/.git exists
        pass
```

---

## 4. Test Verification Command

Both test files are structured as standard Python `unittest` suites. They can be executed from the project root using `pytest` or the built-in python test runner:

```bash
# Run multi-project tests
python -m unittest scratch/test_multi_project.py

# Run path contamination tests
python -m unittest scratch/test_path_contamination.py

# Run all scratch tests together
python -m unittest discover -s scratch
```
