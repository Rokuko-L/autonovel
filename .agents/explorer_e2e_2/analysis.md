# E2E Test Strategy Analysis for Autonovel Refactoring

This document outlines a comprehensive 4-tier E2E testing strategy to verify the multi-project refactoring of the Autonovel novel generation pipeline.

---

## 1. Summary of Findings & Gaps

After analyzing the current codebase (specifically `utils.py` and `run_pipeline.py`), we identified the following architectural details:
- **Hardcoded Paths**: The current pipeline runs with paths resolved relative to `BASE_DIR = Path(__file__).resolve().parent` (e.g. `state.json`, `results.tsv`, `chapters/`, etc.). This prevents concurrent project execution and isolates files.
- **Git Operations**: Git commands (`git add -A`, `git commit`, `git reset`) currently execute at the root repository, which poses a risk of contaminating the main codebase history with project drafts.
- **Typesetting**: LaTeX typesetting via Tectonic runs by executing `tectonic typeset/novel.tex` directly from the project root instead of sandboxing it inside the project's typesetting subdirectory.
- **Lack of CLI Isolation**: The pipeline currently does not accept a `--project` parameter and does not register projects in a central `projects/registry.json`.

---

## 2. 4-Tier E2E Testing Strategy

### Tier 1: Feature Coverage (>=5 test cases per feature)

#### F1: `get_root_dir()` Dynamic Workspace Root Detection
1. **`test_root_detection_via_pyproject`**: Verifies `get_root_dir()` returns the parent path containing `pyproject.toml`.
2. **`test_root_detection_via_dotenv`**: Verifies `get_root_dir()` returns the parent path containing `.env` if `pyproject.toml` is missing.
3. **`test_root_detection_both_present`**: Verifies root resolution when both files exist.
4. **`test_root_detection_nested_dir`**: Verifies that calling `get_root_dir()` from a nested subdirectory (e.g., `projects/proj/typeset/`) correctly walks up to find the root.
5. **`test_root_detection_raises_error`**: Verifies that a `RuntimeError` is raised if neither `pyproject.toml` nor `.env` can be found in any ancestor directory.

#### F2: Active Project Configuration State (`set_project_name` / `get_project_name`)
1. **`test_project_name_default`**: Verifies that `get_project_name()` returns `"default"` when no active name is set and no environment variables exist.
2. **`test_project_name_explicit_set`**: Verifies that `set_project_name("my_novel")` sets the active project name, and `get_project_name()` returns it.
3. **`test_project_name_env_fallback`**: Verifies fallback to `AUTONOVEL_PROJECT` environment variable.
4. **`test_project_name_explicit_overrides_env`**: Verifies that setting the project name explicitly overrides `AUTONOVEL_PROJECT`.
5. **`test_project_name_reset`**: Verifies that clearing the project name causes it to revert to the fallback env var or `"default"`.

#### F3: Dynamic Folder Path & Pure File Path Helpers
1. **`test_folder_helper_creation`**: Verifies that calling folder path helpers (e.g., `get_chapters_dir()`) creates the respective directories automatically if they do not exist.
2. **`test_pure_file_helper_no_creation`**: Verifies that calling pure file path helpers (e.g., `get_state_path()`) returns the correct `Path` object but does *not* create any file on disk.
3. **`test_path_helpers_dynamic_on_project_change`**: Verifies that changing the active project name immediately changes the output paths of all helpers.
4. **`test_registry_path_resolves_externally`**: Verifies that `get_registry_path()` points to `projects/registry.json`, which sits outside individual project directories but inside the `projects/` root.
5. **`test_all_directories_exist`**: Call all 5 folder path helpers (`chapters`, `edit_logs`, `eval_logs`, `briefs`, `typeset`) and verify that all 5 exist on disk.

#### F4: Atomic Registry Writes (`save_registry`)
1. **`test_save_registry_success`**: Verifies that calling `save_registry` successfully writes JSON data to the target file.
2. **`test_save_registry_temp_file_creation`**: Verifies that during execution, a `.tmp` file is created and then swapped (rename operation).
3. **`test_save_registry_serialization_failure_preserves_original`**: Verifies that if serialization fails (e.g. attempting to serialize a `set`), the original registry file remains intact and is not corrupted.
4. **`test_save_registry_serialization_failure_cleans_temp`**: Verifies that upon serialization failure, the temporary file is deleted and not left behind.
5. **`test_save_registry_missing_parent_directory`**: Verifies that writing to a non-existent parent directory fails gracefully without leaving dangling temp files.

#### F5: Pipeline `--project` CLI Argument & Lifecycle
1. **`test_cli_project_argument_resolution`**: Verifies that `--project my_project` sets the project configuration state.
2. **`test_pipeline_registers_project`**: Verifies that executing the pipeline adds the project details to `projects/registry.json`.
3. **`test_pipeline_lifecycle_resume`**: Verifies that running without `--from-scratch` loads the existing project state and resumes execution from the saved phase.
4. **`test_pipeline_lifecycle_from_scratch`**: Verifies that running with `--from-scratch` clears previous state, deletes existing chapter files, and restarts from the foundation phase.
5. **`test_pipeline_multi_project_isolation`**: Runs the pipeline for two different project names and verifies their `state.json` and chapter files are independent.

#### F6: Git Guards
1. **`test_root_gitignore_contains_projects_rule`**: Verifies that the root `.gitignore` ignores the `projects/` directory.
2. **`test_project_git_init`**: Verifies that creating a new project automatically runs `git init` in `projects/<project_name>/`.
3. **`test_project_gitignore_creation`**: Verifies that a project-specific `.gitignore` file is created inside `projects/<project_name>/` using the template.
4. **`test_project_git_commits_sandboxed`**: Verifies that pipeline commits are recorded in the project-level Git repository and do *not* affect the root repository's git index/history.
5. **`test_git_guard_active_block`**: Verifies that any git commands executed within the pipeline do not propagate changes to the parent repository.

#### F7: Codebase Scripts Routing & Sandboxed Typesetting
1. **`test_script_routing_uses_project_paths`**: Verifies that sub-scripts (e.g., `gen_world.py`) are routed to use project-specific paths instead of root-level paths.
2. **`test_typesetting_subprocess_cwd`**: Verifies that typesetting (Tectonic) is executed with the subprocess `cwd` set to `projects/<project_name>/typeset/`.
3. **`test_typesetting_pdf_sandboxed`**: Verifies that the output `novel.pdf` is created inside the sandboxed `projects/<project_name>/typeset/` directory.
4. **`test_typesetting_temp_files_sandboxed`**: Verifies that all Tectonic auxiliary/log files are contained within the sandbox.
5. **`test_missing_typeset_tools_fallback`**: Verifies that if Tectonic is not available, the pipeline logs a warning and completes the export phase without crashing.

---

### Tier 2: Boundary & Corner Cases (>=5 test cases per feature)

#### F1: `get_root_dir()` Boundary Cases
1. **`test_root_dir_at_drive_root`**: Evaluates root detection when walking up to the filesystem root (e.g., `C:\` or `/`) where no parent exists.
2. **`test_root_dir_permission_denied`**: Verifies behavior when an ancestor directory cannot be read due to permissions.
3. **`test_root_dir_directory_sentinel`**: Verifies behavior if a directory (instead of a file) is named `.env` or `pyproject.toml` in the traversal path.
4. **`test_root_dir_symlink_traversal`**: Tests root resolution when the directory structure contains symlinks.
5. **`test_root_dir_empty_file_path`**: Verifies behavior when `__file__` is unset or empty, ensuring fallback to the current working directory.

#### F2: Active Project Name Boundary Cases
1. **`test_project_name_path_traversal_attempt`**: Verifies that setting a project name to a path-traversal payload (e.g., `../outside_project`) is rejected or sanitized.
2. **`test_project_name_empty_or_none`**: Tests that setting the project name to `""` or `None` raises a `ValueError` or falls back to default.
3. **`test_project_name_extreme_length`**: Tests project name behavior with names exceeding 255 characters (filesystem limit).
4. **`test_project_name_windows_reserved`**: Tests behavior with Windows reserved words (e.g., `CON`, `PRN`, `AUX`, `NUL`).
5. **`test_project_name_concurrent_threads`**: Verifies that setting project names in different threads is isolated (thread-local state).

#### F3: Folder Path & Pure File Helpers Boundary Cases
1. **`test_folder_helper_read_only_parent`**: Verifies behavior when attempting to create folders inside a read-only parent directory.
2. **`test_folder_helper_exist_ok`**: Verifies that folder path helpers do not raise errors when the directory already exists.
3. **`test_pure_file_helper_nested_parent_missing`**: Verifies that pure file path helpers return a valid Path even if the parent directory does not exist on disk.
4. **`test_path_helpers_path_case_sensitivity`**: Tests path resolution case-sensitivity across Windows/Linux environments.
5. **`test_path_helpers_unicode_project_name`**: Verifies that path helpers resolve paths correctly when the project name contains Unicode/emojis (e.g., `projects/✨novel✨`).

#### F4: Atomic Registry Writes Boundary Cases
1. **`test_save_registry_pre_existing_temp_file`**: Verifies that `save_registry` still succeeds even if a `.tmp` file already exists.
2. **`test_save_registry_target_locked`**: Tests behavior when the target file is open/locked by another process.
3. **`test_save_registry_large_data`**: Verifies performance and atomic replacement with very large JSON payloads.
4. **`test_save_registry_disk_full_simulation`**: Simulates a write failure (e.g., disk full) to ensure the original registry remains uncorrupted.
5. **`test_save_registry_empty_data`**: Verifies writing empty dictionary `{}` or null value behavior.

#### F5: Pipeline CLI & Lifecycle Boundary Cases
1. **`test_pipeline_args_invalid_project_characters`**: Verifies CLI parser rejects invalid project names.
2. **`test_pipeline_corrupted_state_json`**: Verifies that if `state.json` is corrupted, the pipeline fails with a warning instead of resuming bad data.
3. **`test_pipeline_from_scratch_non_existent_project`**: Verifies that `--from-scratch` initializes a new project successfully.
4. **`test_pipeline_state_contains_invalid_phase`**: Verifies validation of loaded state phase (e.g., if phase in `state.json` is invalid).
5. **`test_pipeline_resume_missing_chapters`**: Verifies behavior when resuming a project where the state says 3 chapters are drafted, but some chapter files are missing.

#### F6: Git Guards Boundary Cases
1. **`test_git_guard_pre_existing_project_git`**: Tests behavior when `git init` is called on a project folder that is already a Git repository.
2. **`test_git_guard_git_not_installed`**: Verifies the pipeline logs warnings and bypasses Git operations gracefully if git is missing.
3. **`test_git_guard_outside_file_containment`**: Confirms that local project commits never stage or commit files located in the root directory.
4. **`test_git_guard_corrupt_project_git`**: Verifies behavior when the local project `.git` folder becomes corrupted.
5. **`test_git_guard_missing_global_git_config`**: Verifies git commands succeed (e.g. by using local author config) even if `user.name`/`user.email` are not set globally.

#### F7: Subprocess Routing & Typesetting Boundary Cases
1. **`test_typesetting_missing_typeset_dir`**: Verifies that the typesetting sandbox is created if the folder is missing before execution.
2. **`test_typesetting_latex_compile_fail`**: Verifies that if Tectonic compilation fails, the pipeline logs a warning and exits the export phase without crashing.
3. **`test_typesetting_extremely_large_manuscript`**: Tests typesetting limits with very large files.
4. **`test_typesetting_concurrent_builds`**: Verifies that concurrent project compilations do not lock files or clash.
5. **`test_script_routing_broken_sys_executable`**: Verifies fallback routing logic if python interpreter routing fails.

---

### Tier 3: Cross-Feature Combinations

1. **Root Detection + Active Project Config + Path Resolution (F1 + F2 + F3)**:
   - Call path helpers from within a nested script where `get_root_dir()` is dynamically determined, under a custom project name set via environment variables. Verify that all paths resolve to the correct isolated project structure.
2. **Project CLI + Lifecycle + Git Guards (F2 + F5 + F6)**:
   - Run the pipeline with `--project new_git_project --from-scratch`. Check that the project folder is created, registered in `registry.json`, initialized as a Git repo, and has a `.gitignore` template.
3. **Path Helpers + Atomic Registry Writes (F3 + F4)**:
   - Save the registry using the path returned by `get_registry_path()` during project registration. Verify atomic swap on the actual registry path.
4. **Pipeline CLI + Sandboxed Typesetting (F5 + F7)**:
   - Run the pipeline with `--project build_pdf` to the export phase, ensuring that the typesetting subprocess runs with the correct `cwd` and output path.
5. **Active Project Config + Path Helpers + Script Routing (F2 + F3 + F7)**:
   - Set the active project via environment variable `AUTONOVEL_PROJECT`, run a subprocess script, and verify that the subprocess resolves its paths to that environment-variable project folder.

---

### Tier 4: Real-World Scenarios (>=5 scenarios)

1. **Scenario 1: End-to-End Fresh Pipeline Execution**
   - **Flow**: User runs `python run_pipeline.py --project sci_fi_novel --genre "Sci-Fi" --from-scratch --notes "Premise info"`.
   - **Verification**: Verify that the project is registered, `projects/sci_fi_novel/` is initialized, a local git repository is set up, planning files are generated, chapters are drafted, and the final manuscript is compiled.
2. **Scenario 2: Resuming an Interrupted Novel Generation**
   - **Flow**: A pipeline execution for `projects/my_novel/` is interrupted midway (e.g., at Chapter 3). The user restarts the pipeline using `python run_pipeline.py --project my_novel`.
   - **Verification**: The pipeline reads the state file, skips the foundation phase, skips chapters 1-3, and resumes drafting from Chapter 4.
3. **Scenario 3: Concurrent Novel Generation**
   - **Flow**: Two separate terminal sessions run `python run_pipeline.py --project horror_story` and `python run_pipeline.py --project fantasy_epic` simultaneously.
   - **Verification**: Verify that there is zero path contamination: no fantasy files end up in the horror folder, and the registry correctly lists both projects.
4. **Scenario 4: Recovery from Corrupted State File**
   - **Flow**: During a pipeline run, the system crashes and `state.json` is partially written (corrupt JSON). The user re-runs the pipeline.
   - **Verification**: The pipeline detects the corrupted state file, fails gracefully with a warning, and allows the user to restore the last clean state from the project-specific Git repository.
5. **Scenario 5: Typeset Compilation with Present vs. Missing Tectonic**
   - **Flow**: Run the export phase first in an environment where Tectonic is not installed, then in one where Tectonic is installed.
   - **Verification**: Confirm that in the first run, the pipeline completes without crashing and warns the user. In the second run, it generates `novel.pdf` inside `projects/<project_name>/typeset/` without cluttering the root directory.

---

## 3. Test Files Blueprint Design

### `scratch/test_multi_project.py`
This test file will target testing multi-project management, isolation, CLI commands, and registry operations.

```python
import os
import json
import pytest
import shutil
from pathlib import Path
import utils
import run_pipeline

@pytest.fixture
def temp_workspace(tmp_path):
    # Setup temporary directory simulating get_root_dir()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]")
    
    # Mock get_root_dir to point to this temp workspace
    original_get_root_dir = utils.get_root_dir
    utils.get_root_dir = lambda: tmp_path
    
    yield tmp_path
    
    # Restore original function
    utils.get_root_dir = original_get_root_dir

def test_cli_project_arg(temp_workspace, monkeypatch):
    """F5: Test that the --project CLI argument sets the active project."""
    import argparse
    parser = argparse.ArgumentParser()
    # Mock command line parse
    args = run_pipeline.main_parse_args(["--project", "test_proj"])
    assert args.project == "test_proj"

def test_multi_project_isolation(temp_workspace):
    """F2, F3: Test that multiple projects are completely isolated."""
    utils.set_project_name("project_a")
    path_a = utils.get_state_path()
    
    utils.set_project_name("project_b")
    path_b = utils.get_state_path()
    
    assert path_a != path_b
    assert "project_a" in str(path_a)
    assert "project_b" in str(path_b)

def test_project_registry_write(temp_workspace):
    """F4, F5: Test that project registry lists active projects."""
    utils.set_project_name("project_registered")
    registry_path = utils.get_registry_path()
    
    # Save a mockup project list
    data = {"projects": {"project_registered": {"status": "active"}}}
    utils.save_registry(data, registry_path)
    
    # Read and verify
    assert registry_path.exists()
    with open(registry_path) as f:
        read_data = json.load(f)
    assert "project_registered" in read_data["projects"]

def test_save_registry_atomic(temp_workspace):
    """F4: Test atomic registry save with temp swap."""
    registry_path = temp_workspace / "projects" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text('{"existing": true}')
    
    # Serializing a set will fail JSON parsing
    with pytest.raises(Exception):
        utils.save_registry({"invalid": {1, 2, 3}}, registry_path)
        
    # Check that original registry is untouched and tmp is cleaned up
    assert registry_path.read_text() == '{"existing": true}'
    assert not registry_path.with_suffix(".tmp").exists()
```

### `scratch/test_path_contamination.py`
This test file will target testing directory containment, path routing, git security, and sandboxing.

```python
import os
import pytest
import shutil
from pathlib import Path
import utils
import run_pipeline

@pytest.fixture
def temp_workspace(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.poetry]")
    
    original_get_root_dir = utils.get_root_dir
    utils.get_root_dir = lambda: tmp_path
    
    yield tmp_path
    
    utils.get_root_dir = original_get_root_dir

def test_root_detection_missing(tmp_path):
    """F1: Test that get_root_dir raises RuntimeError if sentinel is missing."""
    # Run in a directory with no pyproject.toml or .env
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    
    # We must mock __file__ or temporarily change cwd / resolution
    # to check that it raises RuntimeError
    with pytest.raises(RuntimeError):
        utils.resolve_root_from_path(empty_dir)

def test_git_guard_root_isolation(temp_workspace):
    """F6: Verify project-level git commands are sandboxed."""
    project_dir = temp_workspace / "projects" / "my_git_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Run mock git init in project folder
    import subprocess
    subprocess.run(["git", "init"], cwd=str(project_dir), check=True)
    
    # Verify that project has a local .git directory
    assert (project_dir / ".git").exists()
    
    # Verify root git repository index is unaffected by commits inside the project folder
    # (Checking path containment)

def test_typesetting_sandbox(temp_workspace, monkeypatch):
    """F7: Test that typesetting runs in projects/<name>/typeset/ cwd."""
    project_name = "pdf_project"
    utils.set_project_name(project_name)
    typeset_dir = utils.get_typeset_dir()
    
    # Mock tectonic execution to log its cwd to a file
    mock_script = typeset_dir / "mock_tectonic.py"
    mock_script.write_text("import os; print(os.getcwd())")
    
    # Run compilation and verify cwd was set to typeset_dir
    # (By checking the captured stdout of the run_tool call)
```

---

## 4. Mocking Strategies (CODE_ONLY Environment)

Since the agent is executing in a strictly network-isolated (`CODE_ONLY`) environment, the following mocking strategies must be applied in the test files:
- **Anthropic API calls**: `utils.call_anthropic` must be mocked to return static template strings (e.g. simulated planning files or drafted chapters). This prevents the pipeline from failing on sanity check or hanging on API calls.
- **Tectonic/LaTeX**: Since Tectonic may not be installed locally, `shutil.which("tectonic")` should be mocked or tectonic subprocesses should be intercepted/mocked to output dummy `.pdf` files.
- **Git command execution**: In environments where Git is not installed or configured, `subprocess.run` calls containing `git` arguments should be mocked to return successful `CompletedProcess` objects with mock hashes (e.g., `abcdef0`).
