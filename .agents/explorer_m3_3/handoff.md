# Handoff Report: Milestone 3 Orchestration & Registry Design

## 1. Observation
- In `run_pipeline.py`, the following global constants define paths relative to the script location (lines 43-49):
  ```python
  BASE_DIR = Path(__file__).resolve().parent
  STATE_FILE = BASE_DIR / "state.json"
  RESULTS_FILE = BASE_DIR / "results.tsv"
  CHAPTERS_DIR = BASE_DIR / "chapters"
  BRIEFS_DIR = BASE_DIR / "briefs"
  EDIT_LOGS_DIR = BASE_DIR / "edit_logs"
  EVAL_LOGS_DIR = BASE_DIR / "eval_logs"
  ```
- Subprocess execution currently uses `BASE_DIR` as the working directory (lines 139-140):
  ```python
  encoding="utf-8", timeout=timeout, cwd=str(BASE_DIR),
  ```
- Git helpers in `run_pipeline.py` run from `BASE_DIR` (the root git repository context), which lacks isolation (lines 166-170):
  ```python
  def git_add_commit(message: str) -> str:
      """Stage all changes and commit. Returns short hash or empty string."""
      run_tool("git add -A")
      result = run_tool(f'git commit -m "{message}" --allow-empty')
  ```
- In `scratch/test_multi_project.py`, the test asserts that project initialization registers the project name as a key under the `"projects"` property of the registry file (lines 976-978):
  ```python
      # 2. Registered in registry.json (F5)
      registry = json.loads(utils.get_registry_path().read_text(encoding="utf-8"))
      assert "init_combo_proj" in registry["projects"]
  ```
- The test asserts that the project directory has an independent git repo and `.gitignore` file (lines 980-982):
  ```python
      # 3. Independent git repo created (F6)
      assert (utils.get_project_dir() / ".git").exists()
      assert (utils.get_project_dir() / ".gitignore").exists()
  ```

---

## 2. Logic Chain
- To achieve project isolation, we must remove all static global path constants in `run_pipeline.py` and replace them with dynamic evaluations using `utils.py` helpers.
- Since `run_pipeline.py` spawns child scripts (e.g. `gen_world.py`, `draft_chapter.py`), and since memory state does not cross process boundaries, setting `os.environ["AUTONOVEL_PROJECT"] = args.project` on startup ensures child subprocesses resolve paths in the correct directory.
- The project-level Git operations (commits, resets, status checks) and typesetting (tectonic compilation) must be run in their respective subdirectory context (`project_dir` and `typeset_dir`). Therefore, adding a `cwd` argument to `run_tool` allows executing commands cleanly in these isolated contexts.
- Writing to `projects/registry.json` must preserve the `"projects": { "<project_name>": { ... } }` schema to pass test assertions in `test_multi_project.py`.
- The `--from-scratch` cleanup loop must iterate over the project directory and delete files/folders but explicitly skip `.git` so that the repository history is preserved across restarts, satisfying test cases.

---

## 3. Caveats
- This is a read-only design analysis. Implementation of these changes is scoped for the implementer agent.
- We assume that the git binary is available on the path of the execution environment (required for `git init`). If missing, subprocess calls will warn but keep executing.

---

## 4. Conclusion
The requirements for Milestone 3 are fully analyzed, and the proposed design provides a robust roadmap to implement the project isolation and CLI capabilities in `run_pipeline.py` safely and cleanly without path contamination.

---

## 5. Verification Method
1. Inspect the updated `run_pipeline.py` to confirm the removal of top-level globals and addition of `--project` and environment propagation.
2. Verify that `verify_root_gitignore` is called and adds `projects/` to root `.gitignore`.
3. Verify that `init_project_git` runs `git init` and writes `typeset/\n*.pdf\n` inside the project folder.
4. Run the project's test command to verify everything passes:
   ```powershell
   uv run pytest scratch/test_path_contamination.py
   uv run pytest scratch/test_multi_project.py
   ```
5. Invalidation conditions: Any test failures in `test_multi_project.py` or `test_path_contamination.py` indicate path contamination or interface mismatch.
