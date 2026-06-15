# Milestone 3 Analysis Report: Pipeline Orchestration & Registry (`run_pipeline.py`)

## Executive Summary
This report analyzes the requirements and outlines the design for the Milestone 3 refactoring of `run_pipeline.py`. The primary goal is to shift `run_pipeline.py` from a single-project architecture to an isolated, multi-project orchestration framework. 

This design implements:
1. A CLI `--project` argument and immediate startup configuration.
2. Complete removal of static global path constants, replacing them with dynamic runtime path evaluations via `utils.py` helpers.
3. Atomic registry management in `projects/registry.json` conforming to test schemas.
4. Seamless lifecycle state management (resuming by default, with complete `--from-scratch` cleanup that preserves `.git` and `.env`).
5. Option B Git Guards at both the root level (preventing `projects/` leaks) and the project level (independent git repositories and templates).

---

## 1. CLI Project Argument (`--project`)
### Design
To allow users to specify a unique namespace for each execution run, the `--project` argument is added to the argument parser in `main()`.

- **Argument Definition**:
  ```python
  parser.add_argument(
      "--project", default=None,
      help="Target project namespace folder under projects/"
  )
  ```
- **Startup Logic**:
  Immediately upon parsing arguments:
  1. If `args.project` is provided, call `utils.set_project_name(args.project)`.
  2. Set `os.environ["AUTONOVEL_PROJECT"]` to the resolved active project name to ensure that any child subprocess scripts (e.g. `gen_world.py`, `draft_chapter.py`) inherit this setting and write to the correct project folder.

### Proposed Code Changes
```python
# Before (run_pipeline.py, main() and run_pipeline(args)):
def main():
    ...
    parser.add_argument("--notes", default=os.environ.get("AUTONOVEL_NOTES", ""), ...)
    args = parser.parse_args()
    run_pipeline(args)

# After:
def main():
    ...
    parser.add_argument("--notes", default=os.environ.get("AUTONOVEL_NOTES", ""), ...)
    parser.add_argument("--project", default=None, help="Project folder name under projects/")
    
    args = parser.parse_args()
    if args.project:
        import utils
        utils.set_project_name(args.project)
        # Propagate project name to child processes via environment variable
        os.environ["AUTONOVEL_PROJECT"] = args.project
    run_pipeline(args)
```

---

## 2. Dynamic Path Resolution
### Design
Currently, `run_pipeline.py` defines static path constants at the module level relative to the script location. These constants must be removed and replaced with dynamic function-level evaluations using `utils.py` helpers:

- **Directory Mappings**:
  - `STATE_FILE` $\rightarrow$ `utils.get_state_path()`
  - `RESULTS_FILE` $\rightarrow$ `utils.get_results_path()`
  - `CHAPTERS_DIR` $\rightarrow$ `utils.get_chapters_dir()`
  - `BRIEFS_DIR` $\rightarrow$ `utils.get_briefs_dir()`
  - `EDIT_LOGS_DIR` $\rightarrow$ `utils.get_edit_logs_dir()`
  - `EVAL_LOGS_DIR` $\rightarrow$ `utils.get_eval_logs_dir()`
- **Root-level Reference Mappings**:
  - Scripts and root files (like `.env` and `apply_cuts.py`) should be accessed relative to `utils.get_root_dir()`.
- **Subprocess Execution CWD**:
  - Run general scripts (like `draft_chapter.py`) in `cwd=str(utils.get_root_dir())`.
  - Git commands (staging, committing, resetting) must be executed in `cwd=str(utils.get_project_dir())` to maintain repository isolation.
  - Tectonic compilation must be executed in `cwd=str(utils.get_typeset_dir())`.

To implement this cleanly, we add a `cwd` argument to the `run_tool` subprocess helper:

### Proposed Code Changes
```python
# Before (run_pipeline.py, Constants & run_tool):
BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "state.json"
RESULTS_FILE = BASE_DIR / "results.tsv"
CHAPTERS_DIR = BASE_DIR / "chapters"
BRIEFS_DIR = BASE_DIR / "briefs"
EDIT_LOGS_DIR = BASE_DIR / "edit_logs"
EVAL_LOGS_DIR = BASE_DIR / "eval_logs"

def run_tool(cmd: str, timeout: int = 600, check: bool = False) -> subprocess.CompletedProcess:
    ...
        result = subprocess.run(
            shlex.split(cmd), shell=False, capture_output=True, text=True,
            encoding="utf-8", timeout=timeout, cwd=str(BASE_DIR),
        )
    ...

# After:
import utils

# (Globals STATE_FILE, RESULTS_FILE, etc. are completely removed)

def run_tool(cmd: str, timeout: int = 600, check: bool = False, cwd: str = None) -> subprocess.CompletedProcess:
    step(f"RUN: {cmd}")
    run_cwd = cwd if cwd is not None else str(utils.get_root_dir())
    try:
        result = subprocess.run(
            shlex.split(cmd), shell=False, capture_output=True, text=True,
            encoding="utf-8", timeout=timeout, cwd=run_cwd,
        )
    ...
```

All functions calling these constants will resolve paths dynamically. For example:
```python
# Before (load_state):
def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return default_state()

# After:
def load_state() -> dict:
    state_file = utils.get_state_path()
    if state_file.exists():
        with open(state_file, encoding="utf-8") as f:
            return json.load(f)
    return default_state()
```

---

## 3. Atomic Registry Management (`projects/registry.json`)
### Design
The registry system acts as the single source of truth tracking all active and completed novel project sessions. 

- **File Path**: Dynamically resolved via `utils.get_registry_path()`.
- **Atomic Operations**:
  Uses `utils.save_registry(data, path)` which handles atomic writes via temporary files (`.tmp`) and cleanups to avoid data corruption.
- **Registry Schema**:
  ```json
  {
    "projects": {
      "<project_name>": {
        "status": "active",
        "path": "<absolute_project_directory>",
        "title": "<novel_title>",
        "genre": "<genre_name>",
        "created_at": "<ISO_timestamp>",
        "last_modified": "<ISO_timestamp>",
        "phase": "<current_phase>",
        "novel_score": 0.0,
        "word_count": 0
      }
    }
  }
  ```
- **Automated Lifecycle Synchronization**:
  By integrating the registry update directly inside the `save_state(state)` wrapper, we guarantee that the registry is automatically updated whenever the state progresses, finishes, or is interrupted.

### Proposed Code Changes
```python
def load_registry() -> dict:
    """Load project registry from projects/registry.json."""
    registry_path = utils.get_registry_path()
    if registry_path.exists():
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "projects" in data:
                    return data
        except Exception:
            pass
    return {"projects": {}}


def update_registry_entry(phase: str = None, novel_score = None, word_count: int = None, title: str = None, genre: str = None):
    """Write or update a project session entry in the registry atomically."""
    registry_path = utils.get_registry_path()
    project_name = utils.get_project_name()
    project_dir = utils.get_project_dir()
    
    registry = load_registry()
    projects = registry["projects"]
    
    now = datetime.now().isoformat()
    if project_name not in projects:
        projects[project_name] = {
            "status": "active",
            "path": str(project_dir),
            "title": title or "the novel",
            "genre": genre or "",
            "created_at": now,
            "last_modified": now,
            "phase": phase or "foundation",
            "novel_score": novel_score or 0.0,
            "word_count": word_count or 0
        }
    else:
        entry = projects[project_name]
        if title is not None:
            entry["title"] = title
        if genre is not None:
            entry["genre"] = genre
        if phase is not None:
            entry["phase"] = phase
        if novel_score is not None:
            try:
                entry["novel_score"] = float(novel_score)
            except (ValueError, TypeError):
                pass
        if word_count is not None:
            entry["word_count"] = word_count
        entry["last_modified"] = now

    utils.save_registry(registry, registry_path)


def save_state(state: dict):
    """Write state to state.json and sync to registry."""
    state_file = utils.get_state_path()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        
    # Gather metadata
    title = state.get("title") or utils.get_novel_title()
    genre = state.get("genre")
    if not genre:
        try:
            genre_cfg = load_genre()
            genre = genre_cfg.get("genre_name", "")
        except Exception:
            genre = ""
            
    score = state.get("novel_score")
    if score is None or score == 0.0 or score == "?":
        score = state.get("foundation_score", 0.0)
        
    update_registry_entry(
        phase=state.get("phase"),
        novel_score=score,
        word_count=count_words_in_chapters(),
        title=title,
        genre=genre
    )
```

---

## 4. Pipeline Lifecycle and Resuming / Resetting
### Design
- **Default Behavior**: Resumes from the existing `projects/<project_name>/state.json` if present.
- **Scratch / Reset (`--from-scratch`) Behavior**:
  1. Iterate through the target `project_dir` folder if it exists.
  2. Skip the `.git` directory so we do not delete project-level git history.
  3. Recursively remove directories (`shutil.rmtree`) and files (`unlink`).
  4. Copy the root `seed.txt` (if present) into the empty project directory so that the pipeline has a seed concept to start with.
  5. Initialize a default state, optionally applying the `--chapters` count.
  6. Write the initial state.

### Proposed Code Changes
```python
# Inside run_pipeline(args):
    # Load or initialize state
    project_dir = utils.get_project_dir()
    
    if args.from_scratch:
        banner("STARTING FROM SCRATCH")
        if project_dir.exists():
            import shutil
            for item in project_dir.iterdir():
                if item.name == ".git":
                    continue
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception as e:
                    print(f"WARN: Failed to clean up {item}: {e}", file=sys.stderr)
        
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy root seed.txt to project if it exists and project seed doesn't
        root_seed = utils.get_root_dir() / "seed.txt"
        project_seed = project_dir / "seed.txt"
        if root_seed.exists() and not project_seed.exists():
            try:
                import shutil
                shutil.copy(root_seed, project_seed)
                step("Copied root seed.txt to project directory")
            except Exception as e:
                print(f"WARN: Failed to copy root seed.txt: {e}", file=sys.stderr)
                
        state = default_state()
        if args.chapters:
            try:
                state["chapters_total"] = int(args.chapters)
            except ValueError:
                pass
        save_state(state)
    else:
        state = load_state()
```

---

## 5. Option B Git Guards
### Design
To safeguard both global and project-level file scopes, Option B Git Guards are implemented:

1. **Root `.gitignore` Guard**:
   On pipeline execution startup, check `utils.get_root_dir() / ".gitignore"`. Verify that it ignores `projects/`. If missing, append `projects/` to ensure project-level files are never accidentally tracked in the root repository.
2. **Project-level Git Guard**:
   Check if `projects/<project_name>/.git/` exists. If missing:
   - Run `git init` inside `projects/<project_name>/`.
   - Write a project-level `.gitignore` containing:
     ```
     typeset/
     *.pdf
     ```
     This keeps intermediate typesetting logs and compiled PDF outputs untracked at the project level.

### Proposed Code Changes
```python
def verify_root_gitignore():
    """Verify that the root directory's .gitignore has 'projects/'."""
    root_dir = utils.get_root_dir()
    gitignore_path = root_dir / ".gitignore"
    
    if not gitignore_path.exists():
        try:
            gitignore_path.write_text("projects/\n", encoding="utf-8")
            step("Created root .gitignore with 'projects/'")
        except Exception as e:
            print(f"WARN: Failed to write root .gitignore: {e}", file=sys.stderr)
        return
        
    try:
        content = gitignore_path.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines()]
        if "projects/" not in lines and "projects" not in lines:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                if content and not content.endswith("\n"):
                    f.write("\n")
                f.write("projects/\n")
            step("Appended 'projects/' to root .gitignore")
    except Exception as e:
        print(f"WARN: Failed to read/update root .gitignore: {e}", file=sys.stderr)


def init_project_git():
    """Initialize a Git repository inside the project folder if missing."""
    project_dir = utils.get_project_dir()
    git_dir = project_dir / ".git"
    
    project_dir.mkdir(parents=True, exist_ok=True)
    
    if not git_dir.exists():
        step(f"Initializing Git repository in {project_dir}")
        try:
            subprocess.run(["git", "init"], cwd=str(project_dir), check=True, capture_output=True, text=True)
        except Exception as e:
            print(f"WARN: Failed to run 'git init' in {project_dir}: {e}", file=sys.stderr)
            
        project_gitignore = project_dir / ".gitignore"
        if not project_gitignore.exists():
            try:
                project_gitignore.write_text("typeset/\n*.pdf\n", encoding="utf-8")
                step("Wrote project-level .gitignore template")
            except Exception as e:
                print(f"WARN: Failed to write project-level .gitignore: {e}", file=sys.stderr)


# Integrated in run_pipeline(args):
def run_pipeline(args):
    # Guard 1: Root Git ignore check
    verify_root_gitignore()
    
    # Guard 2: Project-level Git init and gitignore template
    init_project_git()
    
    # Run pre-flight checks
    sanity_check(args)
    ...
```

---

## 6. Verification and Test Plan
The refactored script design will be verified against the project's E2E test suites:

- **Test Commands**:
  ```powershell
  # Run all path isolation and multi-project tests
  uv run pytest scratch/test_path_contamination.py
  uv run pytest scratch/test_multi_project.py
  ```
- **Containment Checks**:
  Verify that when running the pipeline:
  - No new files are written to the workspace root directory.
  - All project artifacts (chapters, outlines, state) reside solely under `projects/<project_name>/`.
  - The root Git repository remains completely clean, and files inside `projects/` are untracked by the root repository.
  - Commits performed during the pipeline runs are isolated in `projects/<project_name>/.git`.
