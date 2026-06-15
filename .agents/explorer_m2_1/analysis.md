# Analysis Report — Milestone 2: Core Path & Config Refactoring (utils.py)

This report details the architectural analysis and implementation design for the refactoring of `utils.py` as part of Milestone 2 of the Autonovel project. The objective is to transition from global, hardcoded workspace paths to dynamic, isolated project sessions located under `projects/<project_name>/`.

---

## 1. Executive Summary
- **Primary Goal**: Refactor path resolution in `utils.py` to enable isolation of project-specific novel generation sessions.
- **Key Deliverables**: 
  - Dynamic root directory resolver (`get_root_dir()`).
  - Active project configuration memory state getters and setters (`set_project_name()`, `get_project_name()`).
  - Atomic registry updates (`save_registry()`).
  - Clean distinction between side-effectful folder helpers (ensure directory existence) and pure file helpers.
- **Proposed Solution**: Written to `d:\Tugas\LLM\autonovel\.agents\explorer_m2_1\proposed_utils.py`. The proposed file passes syntax verification and successfully preserves original Anthropic API interfaces while modernizing path resolution.

---

## 2. Analysis of Current `utils.py`

In the current codebase, `utils.py` defines:
```python
BASE_DIR = Path(__file__).resolve().parent
```
And resolve paths relative to `BASE_DIR` in a hardcoded manner (e.g. `get_novel_title()` loads `state.json` directly from the parent directory of `__file__`).

### Key Shortcomings of Current Implementation:
1. **No Project Session Support**: Files like `state.json`, `outline.md`, and subdirectories like `chapters/` are written directly to the project root directory. Running multiple concurrent novel runs would overwrite these files.
2. **Hardcoded State Paths**: `get_novel_title()` hardcodes the location of `state.json` relative to `__file__`.
3. **No Central Project Memory**: There is no mechanism to set or get an active project session name dynamically.

---

## 3. Detailed Refactoring Design

### A. Dynamic Root Directory WALK-UP (`get_root_dir()`)
We define a robust walk-up resolver that traverses upward from the location of the utility script until it finds a marker file (`pyproject.toml` or `.env`).

```python
def get_root_dir() -> Path:
    """Walk up parent folders from __file__ to find pyproject.toml or .env. Raise RuntimeError if missing."""
    curr = Path(__file__).resolve().parent
    while True:
        if (curr / "pyproject.toml").exists() or (curr / ".env").exists():
            return curr
        parent = curr.parent
        if parent == curr:
            break
        curr = parent
    raise RuntimeError("Project root containing pyproject.toml or .env not found.")
```

*Rationale*:
- Uses `.resolve()` to handle symbolic links and ensure absolute paths.
- Guards against infinte loops at filesystem root by checking `parent == curr`.
- Raises a `RuntimeError` if marker files are missing, ensuring clean error propagation rather than silent failure.

### B. Project Session Memory
We maintain the active project name inside a private module-level global variable `_project_name`.

```python
# Active project configuration state memory
_project_name = None

def set_project_name(name: str):
    """Set active project name in global or session-level configuration memory."""
    global _project_name
    _project_name = name

def get_project_name() -> str:
    """Retrieve active project name, fallback to AUTONOVEL_PROJECT env var, default to 'default'."""
    global _project_name
    if _project_name is not None:
        return _project_name
    env_val = os.environ.get("AUTONOVEL_PROJECT")
    if env_val:
        return env_val
    return "default"
```

*Rationale*:
- Allows programmatic configuration (`set_project_name`) for CLI arguments (e.g., `--project name` in `run_pipeline.py`).
- Integrates seamlessly with environment variables via `AUTONOVEL_PROJECT` fallback.
- Guarantees a default `"default"` value to prevent `NoneType` errors.

### C. Atomic Registry Updates (`save_registry()`)
The registry state must be written atomically to prevent file corruption during pipeline failures or concurrent accesses.

```python
def save_registry(data: dict, path: Path):
    """Atomically write registry JSON via .tmp file and rename, with cleanup if JSON serialization fails."""
    import json
    path = path.resolve()
    # Ensure parent folder exists
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        # Write JSON to .tmp file
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        # Clean up .tmp file if JSON serialization / writing fails
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise e
    
    # Atomic rename (replace target path if exists)
    try:
        os.replace(tmp_path, path)
    except Exception as e:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise e
```

*Rationale*:
- By resolving the path to an absolute path first, and creating `tmp_path` in the exact same directory, we ensure the temp file and target file reside on the same filesystem/drive.
- In Python on Windows, `os.replace` is atomic when files are on the same volume.
- Cleans up the `.tmp` file using a `try-except` block if JSON serialization or renaming fails, keeping the directory clean.

### D. Folder Helpers (Creation-on-demand)
Folder helpers must return `Path` objects and ensure the target directory exists.

- **`get_chapters_dir() -> Path`**: `projects/<project_name>/chapters/`
- **`get_edit_logs_dir() -> Path`**: `projects/<project_name>/edit_logs/`
- **`get_eval_logs_dir() -> Path`**: `projects/<project_name>/eval_logs/`
- **`get_briefs_dir() -> Path`**: `projects/<project_name>/briefs/`
- **`get_typeset_dir() -> Path`**: `projects/<project_name>/typeset/`

*Implementation Pattern*:
```python
def get_chapters_dir() -> Path:
    d = get_root_dir() / "projects" / get_project_name() / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    return d
```

### E. File Helpers (Pure Functions)
File helpers return path references and must **not** perform filesystem creation side effects.

- **`get_outline_path()`** -> `outline.md`
- **`get_state_path()`** -> `state.json`
- **`get_results_path()`** -> `results.tsv` (corresponds to `results.tsv` in `run_pipeline.py`)
- **`get_registry_path()`** -> `projects/registry.json`
- **`get_world_path()`** -> `world.md`
- **`get_voice_path()`** -> `voice.md`
- **`get_characters_path()`** -> `characters.md`
- **`get_canon_path()`** -> `canon.md`
- **`get_manuscript_path()`** -> `manuscript.md`
- **`get_reviews_path()`** -> `reviews.md`
- **`get_arc_summary_path()`** -> `arc_summary.md`

*Implementation Pattern*:
```python
def get_outline_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "outline.md"

def get_registry_path() -> Path:
    return get_root_dir() / "projects" / "registry.json"
```

---

## 4. Backwards Compatibility & Integration Details

1. **`BASE_DIR` Variable**: Some scripts might import `BASE_DIR` directly from `utils`. To prevent regressions:
   ```python
   try:
       BASE_DIR = get_root_dir()
   except RuntimeError:
       BASE_DIR = Path(__file__).resolve().parent
   ```
2. **`get_novel_title()`**: Refactored to leverage `get_state_path()` instead of a hardcoded parent relative path:
   ```python
   def get_novel_title():
       import json
       state_path = get_state_path()
       if state_path.exists():
           try:
               state = json.loads(state_path.read_text(encoding="utf-8"))
               if "title" in state:
                   return state["title"]
           except (json.JSONDecodeError, KeyError):
               pass
       return "the novel"
   ```
