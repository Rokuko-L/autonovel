# Milestone 3 Analysis Report: Pipeline Orchestration & Registry

## 1. Executive Summary
This analysis details the design and architecture required to refactor `run_pipeline.py` to support multi-project isolation, registry management, resilient lifecycle states, and Git sandboxing. By utilizing dynamic path helpers from `utils.py` and enforcing local working directory restrictions, we isolate different project environments under `projects/<project_name>/`.

---

## 2. Command-Line Interface (`--project`)

### 2.1 Argument Addition
We add a `--project` argument to `argparse.ArgumentParser` in `main()` of `run_pipeline.py`.
```python
parser.add_argument(
    "--project", default=None,
    help="Name of the project directory under projects/"
)
```

### 2.2 Startup Execution & Name Validation
Immediately after parsing arguments, the pipeline must validate the project name and call `utils.set_project_name()`. Because subprocesses run in independent environments, we must also set the `AUTONOVEL_PROJECT` environment variable so all child scripts inherit the project context.

To pass the strict E2E boundary tests, we implement the following sanitizations:
```python
args = parser.parse_args()

if args.project:
    project_name = args.project
    # Validate characters (check for *, ?, <, >, |, :)
    if any(char in project_name for char in ["*", "?", "<", ">", "|", ":"]):
        raise ValueError("Invalid characters in project argument")
    # Validate directory traversal
    if ".." in project_name or "/" in project_name or "\\" in project_name:
        raise ValueError("Directory traversal detected")
    # Validate non-empty / whitespace
    if project_name.strip() == "":
        raise ValueError("Invalid project name")
    # Validate length
    if len(project_name) > 255:
        raise ValueError("Project name too long")
    # Validate Windows reserved names
    if project_name.upper() in ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]:
        raise ValueError("Reserved Windows name")

    utils.set_project_name(project_name)
    os.environ["AUTONOVEL_PROJECT"] = project_name
else:
    # Fallback to current project name
    os.environ["AUTONOVEL_PROJECT"] = utils.get_project_name()
```

---

## 3. Dynamic Path Resolution & Global Variable Removal

The top-level global path variables must be removed from `run_pipeline.py` to avoid hardcoding paths to the root directory. Instead, paths are evaluated dynamically inside functions using `utils.py` helpers.

### 3.1 Mapping of Global Variables
The following global variables are replaced by dynamic lookups:

| Global Variable (Before) | Dynamic Resolution (After) |
|---|---|
| `BASE_DIR = Path(__file__).resolve().parent` | `utils.get_root_dir()` |
| `STATE_FILE = BASE_DIR / "state.json"` | `utils.get_state_path()` |
| `RESULTS_FILE = BASE_DIR / "results.tsv"` | `utils.get_results_path()` |
| `CHAPTERS_DIR = BASE_DIR / "chapters"` | `utils.get_chapters_dir()` |
| `BRIEFS_DIR = BASE_DIR / "briefs"` | `utils.get_briefs_dir()` |
| `EDIT_LOGS_DIR = BASE_DIR / "edit_logs"` | `utils.get_edit_logs_dir()` |
| `EVAL_LOGS_DIR = BASE_DIR / "eval_logs"` | `utils.get_eval_logs_dir()` |

### 3.2 Modifying `run_tool` for Project Working Directory
To ensure git commands run inside the isolated project directories rather than the root directory, `run_tool` is updated to support a `cwd` parameter:
```python
def run_tool(cmd: str, timeout: int = 600, check: bool = False, cwd: Path = None) -> subprocess.CompletedProcess:
    step(f"RUN: {cmd}")
    if cwd is None:
        cwd = utils.get_root_dir()
    try:
        result = subprocess.run(
            shlex.split(cmd), shell=False, capture_output=True, text=True,
            encoding="utf-8", timeout=timeout, cwd=str(cwd),
        )
        # ... error logging ...
        return result
    except subprocess.TimeoutExpired:
        # ... timeout handling ...
```

---

## 4. Atomic Registry Management (`projects/registry.json`)

To track isolated novel sessions concurrently, we manage `projects/registry.json` using the atomic helper `utils.save_registry`.

### 4.1 Registry Structure
The registry is structured as a dictionary mapped under a top-level `"projects"` key for test compatibility:
```json
{
  "projects": {
    "my_novel": {
      "title": "The Glass Tower",
      "genre": "Cyberpunk Noir",
      "created_at": "2026-06-16T13:54:00Z",
      "last_modified": "2026-06-16T14:10:00Z",
      "phase": "drafting",
      "novel_score": 7.8,
      "word_count": 12500,
      "status": "active",
      "path": "d:\\Tugas\\LLM\\autonovel\\projects\\my_novel"
    }
  }
}
```

### 4.2 Helper for Atomic Updates
We introduce an atomic registry update function in `run_pipeline.py`:
```python
def update_registry_entry(project_name: str, phase: str, novel_score=None, word_count=None, title=None, genre=None):
    registry_path = utils.get_registry_path()
    registry_data = {"projects": {}}
    
    if registry_path.exists():
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry_data = json.load(f)
        except Exception:
            pass
            
    if "projects" not in registry_data:
        registry_data["projects"] = {}
        
    entry = registry_data["projects"].get(project_name, {})
    now = datetime.now().isoformat()
    
    if not entry:
        entry["created_at"] = now
        entry["status"] = "active"
        entry["path"] = str(utils.get_project_dir())
        
    entry["last_modified"] = now
    entry["phase"] = phase
    
    if title is not None:
        entry["title"] = title
    elif "title" not in entry:
        entry["title"] = utils.get_novel_title()
        
    if genre is not None:
        entry["genre"] = genre
    elif "genre" not in entry:
        try:
            from genre import load_genre
            genre_cfg = load_genre()
            entry["genre"] = genre_cfg.get("genre_name", "unknown")
        except Exception:
            entry["genre"] = "unknown"
            
    if novel_score is not None:
        entry["novel_score"] = novel_score
    elif "novel_score" not in entry:
        entry["novel_score"] = 0.0
        
    if word_count is not None:
        entry["word_count"] = word_count
    elif "word_count" not in entry:
        entry["word_count"] = count_words_in_chapters()
        
    registry_data["projects"][project_name] = entry
    utils.save_registry(registry_data, registry_path)
```

### 4.3 Automated Lifecycle Hooks
The registry should automatically synchronize whenever state is loaded, modified, or completed.
1. **At Pipeline Start**: Initialize the entry immediately.
2. **At State Save**: Intercept `save_state(state)` to update the registry in a single step:
   ```python
   def save_state(state: dict):
       """Write state to state.json and update registry."""
       with open(utils.get_state_path(), "w", encoding="utf-8") as f:
           json.dump(state, f, indent=2)
           
       try:
           novel_score = state.get("novel_score", 0.0) or state.get("foundation_score", 0.0)
           update_registry_entry(
               project_name=utils.get_project_name(),
               phase=state.get("phase", "foundation"),
               novel_score=novel_score,
               word_count=count_words_in_chapters(),
               title=state.get("title")
           )
       except Exception as e:
           print(f"Warning: Failed to update registry: {e}", file=sys.stderr)
   ```

---

## 5. Lifecycle Management: Resume vs. Scratch

### 5.1 Resume Behavior (Default)
By default, the pipeline checks if `projects/<project_name>/state.json` exists. If it does, the state is read, and the pipeline resumes from the last completed stage.
We update `load_state()` to use the dynamic path:
```python
def load_state() -> dict:
    """Load pipeline state from state.json, creating defaults if missing."""
    state_path = utils.get_state_path()
    if state_path.exists():
        try:
            with open(state_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print("WARNING: state.json corrupted, returning default state.", file=sys.stderr)
    return default_state()
```

### 5.2 Scratch / Reset Behavior (`--from-scratch`)
When the `--from-scratch` flag is provided, the project folder is cleared to prevent cross-contamination, but we must protect critical configuration files:
- **Do NOT delete `.git/`** (keeps the repository intact and avoids initialization issues).
- **Do NOT delete `.gitignore`** (retains Git exclusion patterns).
- **Do NOT delete `seed.txt`** (keeps the story premise if `--notes` was not provided).

```python
if args.from_scratch:
    banner("STARTING FROM SCRATCH")
    project_dir = utils.get_project_dir()
    
    # 1. Clean up old files and folders safely
    if project_dir.exists():
        import shutil
        has_notes = bool(args.notes)
        for item in project_dir.iterdir():
            if item.name == ".git":
                continue
            if item.name == "seed.txt" and not has_notes:
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
                
    # 2. Reset and save state
    state = default_state()
    if args.chapters:
        try:
            state["chapters_total"] = int(args.chapters)
        except ValueError:
            pass
    save_state(state)
```

---

## 6. Option B Git Guards

### 6.1 Root `.gitignore` Protection
We check the root `.gitignore` on startup. If `"projects/"` is not in the file, we append it to prevent local workspaces from leaking into the parent repository.
```python
def verify_root_gitignore():
    root_dir = utils.get_root_dir()
    root_gitignore = root_dir / ".gitignore"
    has_projects = False
    
    if root_gitignore.exists():
        try:
            content = root_gitignore.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.splitlines()]
            if "projects/" in lines or "projects" in lines:
                has_projects = True
        except Exception as e:
            print(f"Warning: Could not read root .gitignore: {e}", file=sys.stderr)
            
    if not has_projects:
        try:
            with open(root_gitignore, "a", encoding="utf-8") as f:
                if root_gitignore.exists() and root_gitignore.stat().st_size > 0:
                    f.write("\n")
                f.write("# Ignore project-specific isolated workspaces\nprojects/\n")
            step("Added 'projects/' to root .gitignore")
        except Exception as e:
            print(f"Warning: Could not write to root .gitignore: {e}", file=sys.stderr)
```

### 6.2 Per-Project Git Initialization
To isolate draft tracking, each project folder must contain an independent git repository. To allow the pipeline's git operations (`git reset`, `git commit`) to execute successfully, we must commit the initial `.gitignore` file immediately. This establishes `HEAD` as a valid ref.
```python
def initialize_project_git():
    project_dir = utils.get_project_dir()
    project_dir.mkdir(parents=True, exist_ok=True)
    
    git_dir = project_dir / ".git"
    if not git_dir.exists():
        step(f"Initializing new Git repository in {project_dir}")
        try:
            # git init
            subprocess.run(["git", "init"], cwd=str(project_dir), check=True, capture_output=True)
            
            # Write project-level .gitignore
            proj_gitignore = project_dir / ".gitignore"
            gitignore_template = """# Ignore LaTeX typesetting build artifacts
typeset/novel.pdf
typeset/*.aux
typeset/*.log
typeset/*.out
typeset/*.toc
typeset/*.fls
typeset/*.fdb_latexmk
typeset/*.synctex.gz
typeset/_markdown_*
typeset/markdown-languages.json

# Ignore temporary files
*.tmp
*.temp
.DS_Store
"""
            proj_gitignore.write_text(gitignore_template, encoding="utf-8")
            
            # Initial commit to create valid HEAD ref
            subprocess.run(["git", "add", ".gitignore"], cwd=str(project_dir), check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial commit: git guards & gitignore"], cwd=str(project_dir), check=True, capture_output=True)
            step("Project Git repository initialized and initial commit created")
        except Exception as e:
            print(f"Warning: Could not initialize Git in project directory: {e}", file=sys.stderr)
```

### 6.3 Restricting Git and Typeset Commands to Project CWD
All git operations in the pipeline must execute inside the project directory:
- `git add -A` -> `run_tool("git add -A", cwd=utils.get_project_dir())`
- `git commit` -> `run_tool(f"git commit -m ...", cwd=utils.get_project_dir())`
- `git reset` -> `run_tool("git reset --hard HEAD", cwd=utils.get_project_dir())`
- `git checkout` -> `run_tool(f"git checkout -- chapters/...", cwd=utils.get_project_dir())`

Likewise, sandboxed compilation using `tectonic` must run in the project typesetting directory:
```python
result = run_tool("tectonic novel.tex", timeout=300, cwd=utils.get_typeset_dir())
```

---

## 7. Implementation Workflow Protocol

When the implementer acts on this design, they should perform these modifications in order:
1. Call `verify_root_gitignore()` and `initialize_project_git()` at the very beginning of `run_pipeline(args)`.
2. Clean up paths in `run_pipeline.py` by removing top-level globals and substituting them with dynamic helper functions.
3. Update `load_state()`, `save_state()`, and git execution methods to enforce local directory isolation.
4. Hook up `update_registry_entry` within pipeline execution start, state save, and final completion.
