# Milestone 2: Core Path & Config Refactoring (utils.py) Analysis & Design

## Executive Summary
This report analyzes the requirements for refactoring `utils.py` in the Autonovel project to support isolated project sessions. The design proposes dynamic path resolution, active project configuration, and atomic registry serialization. All paths are resolved dynamically relative to `projects/<project_name>/` (except the registry, which sits at `projects/registry.json`), avoiding root directory pollution and ensuring clean session isolation.

---

## 1. Current State of `utils.py`
The current `utils.py` (located at `d:\Tugas\LLM\autonovel\utils.py`) defines a static `BASE_DIR = Path(__file__).resolve().parent` and hardcoded file paths (like `state.json` resolved as `__import__("pathlib").Path(__file__).parent / "state.json"` in `get_novel_title()`). It does not yet contain active project configuration state or dynamic subdirectory helpers, meaning all novel generation files are written directly to the workspace root.

---

## 2. Proposed Design & Interface Contracts

### 2.1 Project Root Discovery
```python
def get_root_dir() -> Path:
    """
    Walks up parent folders from __file__ to find pyproject.toml or .env.
    Raises RuntimeError if neither is found in any ancestor directory.
    """
```
- **Resolution Logic**: Starting from `Path(__file__).resolve().parent`, walk up parent directories. If `current / "pyproject.toml"` or `current / ".env"` exists, return `current`. If the root of the file system is reached without success, raise `RuntimeError("Project root directory containing pyproject.toml or .env not found.")`.

### 2.2 Active Project Configuration State
- We store the active project name in a module-level global variable `_active_project` initialized to `None`.
- **Set Project Name**:
  ```python
  def set_project_name(name: str):
      global _active_project
      _active_project = name
  ```
- **Get Project Name**:
  ```python
  def get_project_name() -> str:
      global _active_project
      if _active_project is not None:
          return _active_project
      env_val = os.environ.get("AUTONOVEL_PROJECT")
      if env_val:
          return env_val
      return "default"
  ```

### 2.3 Atomic Registry Updates
```python
def save_registry(data: dict, path: Path):
    """
    Atomically writes registry JSON data via a .tmp file and renames it to the target path.
    If serialization or writing fails, the .tmp file is deleted.
    """
```
- **Implementation Strategy**:
  1. Ensure the parent directory exists: `path.parent.mkdir(parents=True, exist_ok=True)`.
  2. Define the temp path: `tmp_path = path.parent / f"{path.name}.tmp"`.
  3. Try to serialize `data` and write to `tmp_path`. If serialization/writing throws an exception, catch it, check if `tmp_path` exists, delete (`unlink`) it, and re-raise the exception.
  4. Once written successfully, use `os.replace(tmp_path, path)` to perform an atomic replace.

### 2.4 Dynamic Folder Helpers
These helpers must return `Path` objects and ensure the directory exists by invoking `.mkdir(parents=True, exist_ok=True)`.
- `get_chapters_dir() -> Path`: `projects/<project_name>/chapters`
- `get_edit_logs_dir() -> Path`: `projects/<project_name>/edit_logs`
- `get_eval_logs_dir() -> Path`: `projects/<project_name>/eval_logs`
- `get_briefs_dir() -> Path`: `projects/<project_name>/briefs`
- `get_typeset_dir() -> Path`: `projects/<project_name>/typeset`

### 2.5 Pure File Helpers
These are pure functions returning `Path` objects with **no side effects** (do not call `.mkdir()` or write files).
- `get_outline_path() -> Path`: `projects/<project_name>/outline.md`
- `get_state_path() -> Path`: `projects/<project_name>/state.json`
- `get_results_path() -> Path`: `projects/<project_name>/results.tsv`
- `get_registry_path() -> Path`: `projects/registry.json`
- `get_world_path() -> Path`: `projects/<project_name>/world.md`
- `get_voice_path() -> Path`: `projects/<project_name>/voice.md`
- `get_characters_path() -> Path`: `projects/<project_name>/characters.md`
- `get_canon_path() -> Path`: `projects/<project_name>/canon.md`
- `get_manuscript_path() -> Path`: `projects/<project_name>/manuscript.md`
- `get_reviews_path() -> Path`: `projects/<project_name>/reviews.md`
- `get_arc_summary_path() -> Path`: `projects/<project_name>/arc_summary.md`

---

## 3. Proposed Code Content for `utils.py`

Below is the complete proposed code for `utils.py` integrating the design:

```python
import _utf8
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_MODELS = {
    "writer": "claude-sonnet-4-6",
    "judge": "claude-opus-4-6",
    "review": "claude-opus-4-6",
}

MODEL_ENV_VARS = {
    "writer": "AUTONOVEL_WRITER_MODEL",
    "judge": "AUTONOVEL_JUDGE_MODEL",
    "review": "AUTONOVEL_REVIEW_MODEL",
}

# Project state tracking
_active_project = None


def get_root_dir() -> Path:
    """Walk up from __file__ to find pyproject.toml or .env. Raise RuntimeError if missing."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "pyproject.toml").exists() or (current / ".env").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise RuntimeError("Project root containing pyproject.toml or .env not found.")


def set_project_name(name: str):
    """Set active project name in global or session-level configuration memory."""
    global _active_project
    _active_project = name


def get_project_name() -> str:
    """Retrieve active project name, fallback to AUTONOVEL_PROJECT environment variable, default to 'default'."""
    global _active_project
    if _active_project is not None:
        return _active_project
    env_val = os.environ.get("AUTONOVEL_PROJECT")
    if env_val:
        return env_val
    return "default"


def save_registry(data: dict, path: Path):
    """Atomically write registry JSON via .tmp file and rename, with cleanup of the .tmp file if JSON serialization fails."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f"{path.name}.tmp"
    try:
        serialized = json.dumps(data, indent=2)
        tmp_path.write_text(serialized, encoding="utf-8")
        os.replace(tmp_path, path)
    except Exception as e:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise e


# Folder helpers (ensure directories exist under projects/<project_name>/)
def get_chapters_dir() -> Path:
    p = get_root_dir() / "projects" / get_project_name() / "chapters"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_edit_logs_dir() -> Path:
    p = get_root_dir() / "projects" / get_project_name() / "edit_logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_eval_logs_dir() -> Path:
    p = get_root_dir() / "projects" / get_project_name() / "eval_logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_briefs_dir() -> Path:
    p = get_root_dir() / "projects" / get_project_name() / "briefs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_typeset_dir() -> Path:
    p = get_root_dir() / "projects" / get_project_name() / "typeset"
    p.mkdir(parents=True, exist_ok=True)
    return p


# Pure file helpers (no side effects)
def get_outline_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "outline.md"


def get_state_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "state.json"


def get_results_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "results.tsv"


def get_registry_path() -> Path:
    return get_root_dir() / "projects" / "registry.json"


def get_world_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "world.md"


def get_voice_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "voice.md"


def get_characters_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "characters.md"


def get_canon_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "canon.md"


def get_manuscript_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "manuscript.md"


def get_reviews_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "reviews.md"


def get_arc_summary_path() -> Path:
    return get_root_dir() / "projects" / get_project_name() / "arc_summary.md"


def extract_text_from_response(resp):
    data = resp if isinstance(resp, dict) else resp.json()
    for block in data["content"]:
        if block["type"] == "text":
            return block["text"]
    return ""


def get_max_tokens_with_thinking(max_tokens):
    return max_tokens + 8000


_client = None


def get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
    return _client


def call_anthropic(
    prompt,
    system=None,
    model_key="writer",
    max_tokens=4000,
    temperature=0.3,
    beta_context=False,
    timeout=300,
):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    model = os.environ.get(MODEL_ENV_VARS[model_key], DEFAULT_MODELS[model_key])

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    if beta_context:
        headers["anthropic-beta"] = "context-1m-2025-08-07"

    payload = {
        "model": model,
        "max_tokens": get_max_tokens_with_thinking(max_tokens),
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    client = get_client()
    resp = client.post(
        f"{base_url.rstrip('/')}/v1/messages",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return extract_text_from_response(resp)


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


def format_prompt(template: str, **kwargs) -> str:
    """Format a template string by replacing both double-braced and single-braced placeholders."""
    for k, v in kwargs.items():
        template = template.replace(f"{{{{{k}}}}}", str(v))
        template = template.replace(f"{{{k}}}", str(v))
    return template
```
