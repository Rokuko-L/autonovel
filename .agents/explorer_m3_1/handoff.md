# Handoff Report: Milestone 3 — Pipeline Orchestration & Registry

This handoff details the findings and design recommendations for implementing Milestone 3 of the Autonovel pipeline refactoring.

---

## 1. Observation

### 1.1 Verbatim Path References in `run_pipeline.py`
We observed hardcoded path constants at the top level of `run_pipeline.py` (lines 43-49):
```python
BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "state.json"
RESULTS_FILE = BASE_DIR / "results.tsv"
CHAPTERS_DIR = BASE_DIR / "chapters"
BRIEFS_DIR = BASE_DIR / "briefs"
EDIT_LOGS_DIR = BASE_DIR / "edit_logs"
EVAL_LOGS_DIR = BASE_DIR / "eval_logs"
```

### 1.2 Verbatim Subprocess execution
We observed `run_tool` executing all subprocess commands within `cwd=str(BASE_DIR)` (lines 137-140):
```python
        result = subprocess.run(
            shlex.split(cmd), shell=False, capture_output=True, text=True,
            encoding="utf-8", timeout=timeout, cwd=str(BASE_DIR),
        )
```

### 1.3 Verbatim Typesetting Execution
We observed tectonic compilation targeting the root-level path without subfolder encapsulation (lines 842-847):
```python
        novel_tex = BASE_DIR / "typeset" / "novel.tex"
        if novel_tex.exists():
            import shutil
            if shutil.which("tectonic"):
                step("Typesetting PDF with tectonic...")
                result = run_tool("tectonic typeset/novel.tex", timeout=300)
```

### 1.4 Verbatim Test Sanitization Constraints
In `scratch/test_multi_project.py` (lines 38-50), the E2E verification environment enforces specific rules on project names:
```python
        if ".." in name or "/" in name or "\\" in name:
            raise ValueError("Directory traversal detected")
        if name.strip() == "":
            raise ValueError("Invalid project name")
        if len(name) > 255:
            raise ValueError("Project name too long")
        if name.upper() in ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]:
            raise ValueError("Reserved Windows name")
```
Additionally, it validates arguments for symbols `*`, `?`, `<`, `>`, `|`, `:` (lines 88-90):
```python
    if project_val is not None:
        if any(char in project_val for char in ["*", "?", "<", ">", "|", ":"]):
            raise ValueError("Invalid characters in project argument")
```

---

## 2. Logic Chain

1. **Subprocess Isolation**: Subprocesses are independent processes and do not inherit parent memory globals (e.g. `_project_name`). For child scripts to resolve paths under the correct project subfolder, they must retrieve the active project name from the environment. Since the `utils.get_project_name` helper checks the `AUTONOVEL_PROJECT` env variable as a fallback, setting `os.environ["AUTONOVEL_PROJECT"]` in the parent orchestrator ensures environmental inheritance across all spawned tools.
2. **Independent Git Workspaces**: If git commands (e.g. `git add -A`, `git commit`) run in the root directory context, they will target the root repository instead of the project-specific workspace. By passing `cwd=utils.get_project_dir()` to `run_tool` during git actions, they are isolated to the active project's workspace.
3. **HEAD Ref Validity**: Running `git init` in a fresh repository does not create a commit, leaving `HEAD` pointing to an unborn branch. When subsequent commands like `git rev-parse HEAD` or `git reset --hard` run, git will throw an error. Instantly writing a `.gitignore` template and making an initial commit establishes `HEAD` and prevents execution failures.
4. **Sandboxed Compilation**: Compiling via tectonic inside the root directory writes `.pdf`, `.log`, and `.aux` outputs to the root, contaminating the environment. Executing the compiler with `cwd=utils.get_typeset_dir()` contains all auxiliary files in the isolated subfolder.

---

## 3. Caveats

- **No external network access**: Network checks (e.g. `httpx.get` in `sanity_check` or Anthropic API calls) must be bypassed or mock-configured during testing as we are in CODE_ONLY mode.
- **Git binary requirement**: Git must be present on the host system to run initialization guards. If git is missing, the system should catch the error and warn the user instead of crashing.

---

## 4. Conclusion

The orchestration pipeline can be successfully isolated by:
- Adding `--project` argument and validating it for Windows reserved names, traversal, and symbols.
- Resolving paths dynamically using `utils.py` helpers instead of root-level globals.
- Propagating `AUTONOVEL_PROJECT` via `os.environ` and executing git/compile commands within project-specific `cwd` locations.
- Writing to `projects/registry.json` atomically and keeping it in sync via `save_state` hooks.
- Clearing files during `--from-scratch` while safeguarding `.git`, `.gitignore`, and the input `seed.txt`.

---

## 5. Verification Method

### 5.1 Test Suites
Execute the following pytest command to verify multi-project isolation and path contamination prevention:
```powershell
pytest scratch/test_multi_project.py scratch/test_path_contamination.py
```

### 5.2 Files to Inspect
- Check `projects/registry.json` after running the pipeline to verify metadata (title, genre, created_at, last_modified, phase, novel_score, word_count) exists and is correct.
- Verify that `projects/<project_name>/.git` and `projects/<project_name>/.gitignore` exist.
- Verify that no output files (`novel.pdf`, `novel.log`, `manuscript.md`, etc.) are written outside of `projects/<project_name>/`.
