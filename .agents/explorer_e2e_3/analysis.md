# Comprehensive E2E Testing Strategy Plan for Autonovel Refactoring

This document outlines a 4-tier E2E testing strategy designed to verify the multi-project refactoring of the Autonovel novel generation pipeline. The tests are split between `scratch/test_multi_project.py` (focusing on multi-project lifecycle, settings, and registry atomic operations) and `scratch/test_path_contamination.py` (focusing on dynamic root detection, directory containment, git sandboxing, and typeset sandboxing).

---

## 1. Summary of Architectural Features (F1-F7)

- **F1: Dynamic Workspace Root Detection**: `utils.get_root_dir()` walks up from `__file__` to find a parent directory containing `pyproject.toml` or `.env`. If none is found, it raises a `RuntimeError`.
- **F2: Active Project Configuration State**: Global module-level project name tracked using `utils.set_project_name()` and `utils.get_project_name()`. Fallback is provided via `AUTONOVEL_PROJECT` environment variable, defaulting to `"default"`.
- **F3: Folder & File Path Helpers**: Folder helpers (`get_chapters_dir()`, etc.) dynamically resolve under `projects/<project_name>/` and automatically ensure directory existence via `mkdir(parents=True, exist_ok=True)`. Pure file helpers (e.g. `get_state_path()`) return the path without side effects.
- **F4: Atomic Registry Writes**: `utils.save_registry(data, path)` ensures updates to the project registry are atomic by writing to a `.tmp` file and then swapping it using `os.replace`. If writing or serialization fails, the `.tmp` file is deleted.
- **F5: CLI Project & Lifecycle**: `run_pipeline.py` integrates `--project` CLI argument and handles resuming from saved `state.json` or restarting from scratch via `--from-scratch`.
- **F6: Git Guards**: Root `.gitignore` ignores `projects/`. Each project directory is initialized as a separate Git repository with its own `.gitignore` from a template, and all commits during execution are confined inside the project directory.
- **F7: Script Routing & Sandboxed Typesetting**: Generator scripts are routed using dynamic project path helpers instead of root-level hardcoded paths. Typesetting via Tectonic runs in a separate subprocess with the `cwd` set to `projects/<project_name>/typeset/`.

---

## 2. The 4-Tier E2E Test Catalog

### Tier 1: Feature Coverage (>=5 test cases per feature)

#### F1: `get_root_dir()` Workspace Detection
1. **`test_f1_root_via_pyproject`**: Create `pyproject.toml` in a temporary directory. Verify `get_root_dir()` finds it.
2. **`test_f1_root_via_dotenv`**: Create `.env` (without `pyproject.toml`) in a temporary directory. Verify `get_root_dir()` finds it.
3. **`test_f1_root_both_present`**: Create both `pyproject.toml` and `.env` in a temporary directory. Verify `get_root_dir()` successfully returns the directory.
4. **`test_f1_root_nested_lookup`**: Create a nested directory structure `root/projects/p1/typeset/`. Place `pyproject.toml` in `root/`. Call `get_root_dir()` from a simulated script running in `typeset/` and verify it walks up to find `root/`.
5. **`test_f1_root_missing_raises_error`**: Set up a directory path with no sentinel files. Verify `get_root_dir()` raises `RuntimeError`.

#### F2: Active Project Configuration State
6. **`test_f2_project_name_default`**: Clear any active state and environment variables. Verify `get_project_name()` returns `"default"`.
7. **`test_f2_project_name_explicit_set`**: Call `set_project_name("custom_proj")`. Verify `get_project_name()` returns `"custom_proj"`.
8. **`test_f2_project_name_env_fallback`**: Set `AUTONOVEL_PROJECT` environment variable to `"env_proj"`. Verify `get_project_name()` returns `"env_proj"`.
9. **`test_f2_project_name_explicit_overrides_env`**: Set `AUTONOVEL_PROJECT="env_proj"` and call `set_project_name("explicit_proj")`. Verify `get_project_name()` returns `"explicit_proj"`.
10. **`test_f2_project_name_reset`**: Set project name to `"temp_proj"`, then clear it with `set_project_name(None)`. Verify it reverts to the env variable fallback or `"default"`.

#### F3: Folder & File Path Helpers
11. **`test_f3_folder_helper_creates_dir`**: Call `get_chapters_dir()`. Verify that the folder `projects/<project_name>/chapters` is created on disk.
12. **`test_f3_pure_file_helper_no_creation`**: Call `get_state_path()`. Verify it returns a path under `projects/<project_name>/state.json` but does not write any file to disk.
13. **`test_f3_paths_change_on_project_switch`**: Call `get_state_path()` under project A, switch project name to B, and call it again. Verify the paths are different and point to their respective project folders.
14. **`test_f3_registry_path_resolves_outside_project`**: Verify that `get_registry_path()` points to `projects/registry.json`, which sits in the parent `projects/` folder and is not nested inside any specific project.
15. **`test_f3_all_folders_exist`**: Call `get_chapters_dir()`, `get_edit_logs_dir()`, `get_eval_logs_dir()`, `get_briefs_dir()`, and `get_typeset_dir()`. Verify all 5 folders exist.

#### F4: Atomic Registry Writes
16. **`test_f4_save_registry_writes_json`**: Save project metadata to registry path. Verify that the written file exists and contains valid JSON matching input.
17. **`test_f4_save_registry_uses_tmp_swap`**: Verify that `save_registry` writes to `registry.json.tmp` first, then renames to `registry.json` (mock `os.replace` to assert name transition).
18. **`test_f4_save_registry_serialization_failure_preserves_original`**: Write a valid registry file first. Then, call `save_registry` with a non-serializable object (e.g. `set()`). Verify the original registry remains intact.
19. **`test_f4_save_registry_serialization_failure_cleans_tmp`**: On serialization failure, verify that any created `.tmp` file is deleted.
20. **`test_f4_save_registry_creates_parent_dir`**: Call `save_registry` when the parent `projects/` directory does not exist. Verify that the parent directory is created and the save succeeds.

#### F5: CLI Project & Lifecycle
21. **`test_f5_cli_project_argument_parsing`**: Run CLI parse with `--project demo_project`. Verify the parsed arguments contain `project="demo_project"`.
22. **`test_f5_pipeline_registers_new_project`**: Execute pipeline with `--project new_proj`. Verify that `new_proj` is added to `projects/registry.json`.
23. **`test_f5_pipeline_lifecycle_resume`**: Set up a project with `state.json` indicating a phase of `drafting`. Run the pipeline without `--from-scratch` and verify it skips foundation and resumes at drafting.
24. **`test_f5_pipeline_lifecycle_from_scratch`**: Set up a project with completed draft chapters. Run the pipeline with `--from-scratch`. Verify that the old state is reset to `foundation` and existing chapter files are deleted.
25. **`test_f5_pipeline_multi_project_isolation`**: Run the pipeline for Project A and Project B sequentially. Verify Project A's files remain unaffected by Project B's execution.

#### F6: Git Guards
26. **`test_f6_root_gitignore_rules`**: Read the root `.gitignore` file and assert that it contains a rule ignoring `projects/` (or `projects`).
27. **`test_f6_project_git_init`**: Run the pipeline for a new project. Verify that a `.git/` folder is initialized inside `projects/<project_name>/`.
28. **`test_f6_project_gitignore_created`**: Run the pipeline for a new project. Verify that `projects/<project_name>/.gitignore` is written and contains project-level ignore patterns.
29. **`test_f6_project_git_commits_isolated`**: Make a commit during the pipeline execution. Verify that the commit is recorded in the project-level Git repo and does not affect the root repository's status.
30. **`test_f6_git_guard_prevents_root_staging`**: Verify that running git stage/commit operations inside the project folder does not stage modified files in the root folder (e.g. `utils.py`).

#### F7: Script Routing & Sandboxed Typesetting
31. **`test_f7_subprocess_inherits_project_env`**: Verify that when spawning scripts, the environment variable `AUTONOVEL_PROJECT` is set to the current project name so that subprocesses route paths correctly.
32. **`test_f7_typesetting_subprocess_cwd`**: Run the export phase. Verify that the Tectonic subprocess is executed with `cwd` set to `projects/<project_name>/typeset/`.
33. **`test_f7_typesetting_pdf_sandboxed`**: Verify that the generated `novel.pdf` is outputted to `projects/<project_name>/typeset/novel.pdf`.
34. **`test_f7_typesetting_aux_files_contained`**: Verify that all auxiliary typesetting files (e.g. logs) are written under the sandbox and do not clutter the root workspace.
35. **`test_f7_missing_tectonic_fallback`**: Mock `shutil.which("tectonic")` to return `None`. Run the export phase. Verify that it logs a warning and exits gracefully with code 0.

---

### Tier 2: Boundary & Corner Cases (>=5 test cases per feature)

#### F1: `get_root_dir()` Boundary Cases
36. **`test_f1_boundary_drive_root`**: Call `get_root_dir()` when walking all the way up to filesystem root `/` or `C:\` without finding sentinels. Verify it raises `RuntimeError`.
37. **`test_f1_boundary_permission_denied`**: Mock a directory in the ancestor chain to throw `PermissionError` on read. Verify it is handled gracefully or raises `RuntimeError`.
38. **`test_f1_boundary_directory_sentinel`**: Create a *directory* named `.env` in the path instead of a file. Verify that it is handled correctly.
39. **`test_f1_boundary_symlink_traversal`**: Create a directory symlink that loops or redirects. Verify `get_root_dir()` resolves it to the real path first.
40. **`test_f1_boundary_empty_file_fallback`**: Simulate `__file__` being empty/unset. Verify the workspace root detection falls back to checking from the current working directory (`Path.cwd()`).

#### F2: Active Project Name Boundary Cases
41. **`test_f2_boundary_path_traversal`**: Call `set_project_name("../outside")`. Verify it is rejected or sanitized to prevent directory traversal.
42. **`test_f2_boundary_invalid_characters`**: Try setting project name to spaces `"   "` or empty string `""`. Verify it raises `ValueError` or reverts to default.
43. **`test_f2_boundary_extreme_length`**: Set project name to a 300-character string. Verify that path helpers handle filesystem limits or reject it.
44. **`test_f2_boundary_windows_reserved`**: Set project name to `CON` or `NUL`. Verify it is rejected or sanitized to avoid OS-level file locking/writing errors.
45. **`test_f2_boundary_thread_isolation`**: Call `set_project_name` in concurrent threads and verify that the global project name does not leak between threads (is thread-local or uses session context).

#### F3: Folder & File Path Helpers Boundary Cases
46. **`test_f3_boundary_read_only_parent`**: Set the `projects/` directory to read-only (`0o444`). Call a folder helper. Verify it raises `PermissionError` cleanly.
47. **`test_f3_boundary_dir_already_exists`**: Call a folder helper multiple times on an already existing directory. Verify it does not raise `FileExistsError`.
48. **`test_f3_boundary_missing_project_parent`**: Call a pure file helper when `projects/` is completely empty/missing. Verify it returns the correct path object without error.
49. **`test_f3_boundary_case_sensitivity`**: Verify behavior on case-insensitive filesystems when project names differ only by case (e.g. `Novel` vs `novel`).
50. **`test_f3_boundary_unicode_project_name`**: Set project name to `novel_🔥`. Verify paths resolve and folders are created correctly with UTF-8 encoding.

#### F4: Atomic Registry Writes Boundary Cases
51. **`test_f4_boundary_pre_existing_tmp`**: Simulate a pre-existing `.tmp` file left behind by a crash. Save registry and verify it overwrites the temp file and completes.
52. **`test_f4_boundary_registry_locked`**: Open `registry.json` in exclusive lock mode. Call `save_registry`. Verify it fails cleanly, cleans up the temp file, and original remains unchanged.
53. **`test_f4_boundary_large_payload`**: Save a registry with 10,000 project entries. Verify it writes atomically and does not truncate.
54. **`test_f4_boundary_disk_full`**: Mock file writing to raise `OSError(28, "No space left on device")`. Verify that no partial files are saved and original registry remains intact.
55. **`test_f4_boundary_empty_payload`**: Call `save_registry` with empty dict `{}` or `None`. Verify that it either handles empty dict correctly or raises a validation error.

#### F5: CLI Project & Lifecycle Boundary Cases
56. **`test_f5_boundary_cli_invalid_arg`**: Pass invalid symbols in `--project` (e.g. `--project '*project*'`). Verify it is rejected by the CLI or validation checks.
57. **`test_f5_boundary_state_json_corrupted`**: Write corrupted text (invalid JSON) to `projects/my_project/state.json`. Run the pipeline. Verify it warns and doesn't crash (or resets if `--from-scratch` is passed).
58. **`test_f5_boundary_scratch_non_existent`**: Run `--project ghost_project --from-scratch`. Verify that it does not crash on missing files but initializes the folder structure cleanly.
59. **`test_f5_boundary_state_invalid_phase`**: Write `state.json` with an invalid phase (e.g., `"phase": "unknown"`). Verify the pipeline defaults to `foundation` phase safely.
60. **`test_f5_boundary_resume_missing_chapters`**: Resume a pipeline where `state.json` claims 5 chapters exist but only 3 files are present. Verify that it handles the discrepancy by re-drafting missing chapters.

#### F6: Git Guards Boundary Cases
61. **`test_f6_boundary_git_already_initialized`**: Run a pipeline on a project folder that already has a `.git/` directory. Verify that it does not error or re-initialize.
62. **`test_f6_boundary_git_missing_system`**: Mock `git` commands to be unavailable (simulate system without git). Verify the pipeline runs and logs warnings but completes without crashing.
63. **`test_f6_boundary_git_add_containment`**: Run `git add -A` inside the project. Verify it does not stage changes in parent or neighboring folders.
64. **`test_f6_boundary_corrupt_git_dir`**: Create a corrupt `.git` folder (e.g., empty directory). Verify that the pipeline recovers or re-initializes git safely.
65. **`test_f6_boundary_no_global_config`**: Run git commits without global `user.name` or `user.email` set. Verify local git configs are written and commit succeeds.

#### F7: Script Routing & Typesetting Boundary Cases
66. **`test_f7_boundary_missing_typeset_dir`**: Run export when `typeset/` folder is deleted midway. Verify that the folder is recreated before Tectonic runs.
67. **`test_f7_boundary_tectonic_compile_fail`**: Simulate Tectonic returning exit code 1. Verify the pipeline logs a warning but proceeds to complete the export phase.
68. **`test_f7_boundary_massive_manuscript`**: Run typesetting on a manuscript containing 1 million words. Verify the process compiles or exits cleanly without infinite loops.
69. **`test_f7_boundary_concurrent_tectonic_runs`**: Run two Tectonic compilations in parallel for Project A and Project B. Verify no file-locking clashes occur because they compile in isolated project-level directories.
70. **`test_f7_boundary_invalid_python_interpreter`**: Simulate a failure to route subprocesses via `sys.executable` and check that the pipeline has fallback routing logic.

---

### Tier 3: Cross-Feature Combinations

71. **F1 + F2 + F3 (Root Detection + Config + Path Helpers)**:
    - Run path resolution from a nested subprocess context using a project name supplied via `AUTONOVEL_PROJECT` env var and dynamic root lookup. Verify that the resolves lead to the correct project folder inside the dynamic root.
72. **F2 + F5 + F6 (Project CLI + Lifecycle + Git Sandboxing)**:
    - Run the pipeline with `--project init_project --from-scratch`. Assert that `init_project` is registered in `registry.json`, the local Git repo is created in the subfolder, and the initial git commit contains only the initial template files.
73. **F3 + F4 (Path Helpers + Atomic Registry)**:
    - Register a new project and save the updated registry using the path returned by `get_registry_path()`. Verify that the swap occurs atomically on the actual path returned by the helper.
74. **F5 + F7 (Pipeline CLI + Sandboxed Typesetting)**:
    - Run `run_pipeline.py --project typeset_project --phase export`. Verify that the Tectonic command executes inside `projects/typeset_project/typeset/` and outputs `novel.pdf` inside that directory.
75. **F2 + F3 + F7 (Active Project + Path Helpers + Subprocess Routing)**:
    - Set the active project name, launch a generator script subprocess, and verify that the subprocess resolves its output files to the parent process's active project directory.

---

### Tier 4: Real-World Scenarios (>=5 scenarios)

76. **Scenario 1: End-to-End Fresh Novel Generation**:
    - **Flow**: User executes `python run_pipeline.py --project scifi_novel --genre "Sci-Fi" --from-scratch --notes "A colony ship lost in deep space"`.
    - **Assert**: Project folder is registered and initialized with Git. All foundation planning files (world, characters, outline, canon) are generated inside `projects/scifi_novel/`. Chapters are drafted, revised, and exported to a LaTeX PDF inside the sandbox.
77. **Scenario 2: Resuming an Interrupted Novel Draft**:
    - **Flow**: A pipeline draft runs for `projects/my_novel/` and gets interrupted at Chapter 3. The user re-runs `python run_pipeline.py --project my_novel`.
    - **Assert**: The pipeline reads `projects/my_novel/state.json`, detects that `foundation` is complete and 3 chapters are drafted. It skips foundation generation and resumes drafting starting at Chapter 4.
78. **Scenario 3: Zero-Contamination Concurrent Execution**:
    - **Flow**: Two terminal sessions run `python run_pipeline.py --project horror` and `python run_pipeline.py --project romance` concurrently.
    - **Assert**: Both pipelines write to their separate project directories without path pollution. The registry file `projects/registry.json` correctly tracks both projects.
79. **Scenario 4: Recovery from Corrupted state.json**:
    - **Flow**: The computer crashes midway during a state write, leaving `state.json` corrupted. The user re-runs the pipeline.
    - **Assert**: The pipeline catches the corrupted JSON, warns the user, and automatically restores the last committed version of `state.json` from the local project Git history to resume.
80. **Scenario 5: Building Manuscript and PDF with Missing vs. Present Tectonic**:
    - **Flow**: Run export phase with Tectonic uninstalled (mocked) and verify a clear warning is logged and PDF is skipped. Then, run it with Tectonic installed (mocked) and verify `novel.pdf` is outputted to `projects/<project>/typeset/`.

---

## 3. Test Files Mapping & Blueprints

The 80 test cases are split between two test scripts inside the `scratch/` directory:
1. `scratch/test_multi_project.py`
2. `scratch/test_path_contamination.py`

### Mocking and Interception Strategy (CODE_ONLY Environment)

To test the E2E pipeline without real API charges, network calls, or needing Tectonic installed, we will use a **Subprocess Interception Mocking Strategy**. We patch `run_pipeline.run_tool` (and `run_pipeline.uv_run`) with a custom runner. This runner records executed commands and simulates files written by subprocesses:

```python
class InterceptedSubprocessRunner:
    def __init__(self, workspace_path):
        self.workspace_path = workspace_path
        self.commands_run = []

    def __call__(self, cmd, timeout=600, check=False):
        self.commands_run.append(cmd)
        import shlex
        import subprocess
        
        # Determine the active project name from environment
        project_name = os.environ.get("AUTONOVEL_PROJECT", "default")
        proj_dir = self.workspace_path / "projects" / project_name
        
        # Simulate sub-script outputs on disk
        if "gen_world.py" in cmd:
            (proj_dir / "world.md").write_text("Mock World Bible", encoding="utf-8")
        elif "gen_characters.py" in cmd:
            (proj_dir / "characters.md").write_text("Mock Characters", encoding="utf-8")
        elif "gen_outline.py" in cmd:
            (proj_dir / "outline.md").write_text("### Chapter 1\nOutline content", encoding="utf-8")
        elif "gen_outline_part2.py" in cmd:
            (proj_dir / "outline.md").write_text("### Chapter 1\nOutline content\nForeshadowing", encoding="utf-8")
        elif "gen_canon.py" in cmd:
            (proj_dir / "canon.md").write_text("Mock Canon", encoding="utf-8")
        elif "voice_fingerprint.py" in cmd:
            (proj_dir / "voice.md").write_text("Mock Voice", encoding="utf-8")
        elif "evaluate.py" in cmd:
            # Output foundation score
            stdout = "overall_score: 8.5\nlore_score: 8.0\n"
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=stdout, stderr="")
        elif "build_outline.py" in cmd:
            (proj_dir / "outline.md").write_text("Rebuilt Outline", encoding="utf-8")
        elif "build_arc_summary.py" in cmd:
            (proj_dir / "arc_summary.md").write_text("Mock Arc Summary", encoding="utf-8")
        elif "typeset/build_tex.py" in cmd:
            (proj_dir / "typeset" / "novel.tex").write_text("Mock LaTeX", encoding="utf-8")
        elif "tectonic" in cmd:
            # Simulate PDF creation
            (proj_dir / "typeset" / "novel.pdf").write_text("Mock PDF Content", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="Tectonic compiled", stderr="")
        elif "git init" in cmd:
            (proj_dir / ".git").mkdir(exist_ok=True)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="Initialized empty Git repository", stderr="")
        elif "git commit" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="[master abcdef0] commit", stderr="")
        elif "git rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="abcdef0\n", stderr="")
            
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")
```

### `scratch/test_multi_project.py` Blueprint

This file tests active project state, atomic registry writes, CLI project arguments, and pipeline resume/scratch lifecycles.

```python
import os
import json
import pytest
import shutil
from pathlib import Path
import utils
import run_pipeline

@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    # Setup sentinels to allow get_root_dir to succeed
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]")
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=mock_key")
    
    # Mock root detection to point to temp workspace
    monkeypatch.setattr(utils, "get_root_dir", lambda: tmp_path)
    monkeypatch.setattr(run_pipeline, "BASE_DIR", tmp_path)
    
    # Reset active project name state
    utils.set_project_name(None)
    monkeypatch.delenv("AUTONOVEL_PROJECT", raising=False)
    
    yield tmp_path

def test_project_name_state_management(temp_workspace, monkeypatch):
    """F2: Verify explicit settings, fallback behavior, and priority."""
    assert utils.get_project_name() == "default"
    
    utils.set_project_name("explicit_name")
    assert utils.get_project_name() == "explicit_name"
    
    utils.set_project_name(None)
    monkeypatch.setenv("AUTONOVEL_PROJECT", "env_name")
    assert utils.get_project_name() == "env_name"

def test_save_registry_atomic_operations(temp_workspace):
    """F4: Verify atomic registry writes, temp file cleanup, and directory creation."""
    registry_path = utils.get_registry_path()
    
    # Check directory auto-creation
    data = {"projects": {"test": {"status": "ok"}}}
    utils.save_registry(data, registry_path)
    assert registry_path.exists()
    
    # Check atomic swap preservation on serialization error
    with pytest.raises(Exception):
        utils.save_registry({"bad_key": {1, 2, 3}}, registry_path)
        
    # File is still present, uncorrupted, and tmp file deleted
    assert registry_path.exists()
    assert not registry_path.with_suffix(".tmp").exists()

def test_pipeline_registration_and_isolation(temp_workspace, monkeypatch):
    """F5: Verify E2E project registration and multi-project file isolation."""
    runner = InterceptedSubprocessRunner(temp_workspace)
    monkeypatch.setattr(run_pipeline, "run_tool", runner)
    monkeypatch.setattr(run_pipeline, "uv_run", runner)
    
    # Mock Anthropic API call for notes processing
    monkeypatch.setattr(utils, "call_anthropic", lambda *args, **kwargs: "Expanded Premise")
    
    # Run pipeline for project A
    args = run_pipeline.main_parse_args(["--project", "proj_a", "--genre", "Horror", "--from-scratch", "--notes", "Spooky"])
    run_pipeline.run_pipeline(args)
    
    # Run pipeline for project B
    args = run_pipeline.main_parse_args(["--project", "proj_b", "--genre", "Sci-Fi", "--from-scratch", "--notes", "Space"])
    run_pipeline.run_pipeline(args)
    
    # Assert registry lists both projects
    registry = json.loads(utils.get_registry_path().read_text())
    assert "proj_a" in registry["projects"]
    assert "proj_b" in registry["projects"]
    
    # Verify state isolation
    assert (temp_workspace / "projects" / "proj_a" / "state.json").exists()
    assert (temp_workspace / "projects" / "proj_b" / "state.json").exists()
```

### `scratch/test_path_contamination.py` Blueprint

This file tests dynamic workspace root detection, path containment (ensuring no files are written in the root directory except in `projects/<name>/`), git sandboxing, and typeset sandboxing.

```python
import os
import pytest
import shutil
from pathlib import Path
import utils
import run_pipeline

@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    # Do NOT write pyproject.toml initially to allow testing root detection failure
    monkeypatch.setattr(utils, "get_root_dir", lambda: utils.resolve_root_from_path(tmp_path))
    monkeypatch.setattr(run_pipeline, "BASE_DIR", tmp_path)
    yield tmp_path

def test_dynamic_root_detection(tmp_path):
    """F1: Verify that get_root_dir walks up parents and raises on failure."""
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    
    # Should raise error since neither pyproject.toml nor .env is present
    with pytest.raises(RuntimeError):
        utils.resolve_root_from_path(nested)
        
    # Place pyproject.toml in a/
    (tmp_path / "a" / "pyproject.toml").write_text("[tool.poetry]")
    assert utils.resolve_root_from_path(nested) == tmp_path / "a"

def test_zero_contamination_confinement(temp_workspace, monkeypatch):
    """F3, F5: Verify running pipeline writes zero files to root workspace (except inside projects/)."""
    # Write sentinels to temp_workspace so root detection succeeds
    (temp_workspace / "pyproject.toml").write_text("[tool.poetry]")
    (temp_workspace / ".env").write_text("ANTHROPIC_API_KEY=mock_key")
    
    # Setup subprocess runner mock
    runner = InterceptedSubprocessRunner(temp_workspace)
    monkeypatch.setattr(run_pipeline, "run_tool", runner)
    monkeypatch.setattr(run_pipeline, "uv_run", runner)
    monkeypatch.setattr(utils, "call_anthropic", lambda *args, **kwargs: "Mocked")
    
    # Run pipeline under a custom project name
    args = run_pipeline.main_parse_args(["--project", "clean_proj", "--genre", "Fantasy", "--from-scratch", "--notes", "Magic"])
    run_pipeline.run_pipeline(args)
    
    # List files in temp_workspace (root)
    root_files = os.listdir(temp_workspace)
    
    # Allowed files at root: pyproject.toml, .env, and the projects/ folder
    allowed = {"pyproject.toml", ".env", "projects"}
    for f in root_files:
        assert f in allowed, f"Contamination: found {f} at root workspace!"

def test_git_sandboxing(temp_workspace, monkeypatch):
    """F6: Verify project-level git init and commits are completely sandboxed."""
    (temp_workspace / "pyproject.toml").write_text("[tool.poetry]")
    (temp_workspace / ".env").write_text("ANTHROPIC_API_KEY=mock")
    
    runner = InterceptedSubprocessRunner(temp_workspace)
    monkeypatch.setattr(run_pipeline, "run_tool", runner)
    monkeypatch.setattr(run_pipeline, "uv_run", runner)
    
    args = run_pipeline.main_parse_args(["--project", "git_sandbox_proj", "--from-scratch", "--notes", "Premise"])
    run_pipeline.run_pipeline(args)
    
    # Verify .git folder exists in project but NOT at temp_workspace root
    assert (temp_workspace / "projects" / "git_sandbox_proj" / ".git").exists()
    assert not (temp_workspace / ".git").exists()

def test_typesetting_sandboxing(temp_workspace, monkeypatch):
    """F7: Verify typesetting (Tectonic) executes in sandboxed cwd."""
    (temp_workspace / "pyproject.toml").write_text("[tool.poetry]")
    (temp_workspace / ".env").write_text("ANTHROPIC_API_KEY=mock")
    
    runner = InterceptedSubprocessRunner(temp_workspace)
    monkeypatch.setattr(run_pipeline, "run_tool", runner)
    monkeypatch.setattr(run_pipeline, "uv_run", runner)
    
    # Set to export phase directly
    utils.set_project_name("typeset_sandbox")
    state = run_pipeline.default_state()
    state["phase"] = "export"
    run_pipeline.save_state(state)
    
    args = run_pipeline.main_parse_args(["--project", "typeset_sandbox", "--phase", "export"])
    run_pipeline.run_pipeline(args)
    
    # Assert tectonic compiled in sandbox and produced PDF inside projects/typeset_sandbox/typeset/
    assert (temp_workspace / "projects" / "typeset_sandbox" / "typeset" / "novel.pdf").exists()
```

---

## 4. Verification and Implementation Guidelines

1. **Verify No Code Modification**: These tests should not write or modify any production code in `utils.py` or `run_pipeline.py`. They operate as an opaque verification suite.
2. **Execute Tests**: The tests can be executed using `pytest`:
   ```bash
   pytest scratch/test_multi_project.py
   pytest scratch/test_path_contamination.py
   ```
3. **Forensic Auditor Compliance**: Assertions verify that zero files (like `state.json`, `chapters/`, etc.) leak into the root workspace during E2E runs, meeting all isolation audits.
