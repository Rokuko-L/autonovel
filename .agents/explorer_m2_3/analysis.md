# Milestone 2: Core Path & Config Refactoring (utils.py) - Analysis and Design

This report analyzes the requirements for refactoring `utils.py` to support project session isolation, dynamic path resolution, and atomic registry state updates, as defined in `PROJECT.md` and `ORIGINAL_REQUEST.md`.

---

## 1. Analysis of Current `utils.py`

The current `utils.py` contains:
- Configuration loader (`load_dotenv()`).
- Global constants for default models (`DEFAULT_MODELS`, `MODEL_ENV_VARS`).
- Anthropic API integration (`call_anthropic()`, `get_client()`, `get_max_tokens_with_thinking()`, `extract_text_from_response()`).
- Title resolver (`get_novel_title()`), which currently has a hardcoded path reading from `Path(__file__).parent / "state.json"`.
- Text formatter (`format_prompt()`).

### Required Additions and Modifications
To satisfy Milestone 2, we must introduce:
1. **Root Directory Resolver**: `get_root_dir()`
2. **Project State Configuration**: `set_project_name()` and `get_project_name()`
3. **Atomic Writer for Registry**: `save_registry()`
4. **Folder Helpers**: `get_chapters_dir()`, `get_edit_logs_dir()`, `get_eval_logs_dir()`, `get_briefs_dir()`, and `get_typeset_dir()`.
5. **File Helpers**: `get_outline_path()`, `get_state_path()`, `get_results_path()`, `get_registry_path()`, `get_world_path()`, `get_voice_path()`, `get_characters_path()`, `get_canon_path()`, `get_manuscript_path()`, `get_reviews_path()`, and `get_arc_summary_path()`.

Additionally, existing functions (like `get_novel_title()`) must be updated to use the new file helpers to prevent path leakage and hardcoded references.

---

## 2. Design of Proposed Implementations

### A. Root Directory Resolution (`get_root_dir()`)
- **Requirement**: Walk up the directory structure starting from `__file__` to find `pyproject.toml` or `.env`. Raise `RuntimeError` if not found.
- **Design Decision**: Cache the resolved path in a module-level variable `_root_dir` to avoid repetitive file system checks.
- **Code Logic**:
  ```python
  _root_dir = None

  def get_root_dir() -> Path:
      global _root_dir
      if _root_dir is None:
          current = Path(__file__).resolve().parent
          while True:
              if (current / "pyproject.toml").exists() or (current / ".env").exists():
                  _root_dir = current
                  break
              parent = current.parent
              if parent == current:
                  break
              current = parent
          if _root_dir is None:
              raise RuntimeError("Project root containing pyproject.toml or .env not found")
      return _root_dir
  ```

### B. Project Configuration State (`set_project_name()`, `get_project_name()`)
- **Requirement**: Set and retrieve the active project name. Fall back to the `AUTONOVEL_PROJECT` environment variable, then to `"default"`.
- **Design Decision**: Store the project name in a module-level variable `_project_name`. This functions as simple global session memory.
- **Code Logic**:
  ```python
  _project_name = None

  def set_project_name(name: str):
      global _project_name
      _project_name = name

  def get_project_name() -> str:
      global _project_name
      if _project_name is not None:
          return _project_name
      env_name = os.environ.get("AUTONOVEL_PROJECT")
      if env_name:
          return env_name
      return "default"
  ```

### C. Registry Atomic Writer (`save_registry()`)
- **Requirement**: Atomically write registry JSON via a `.tmp` file and rename, with cleanup of the `.tmp` file if JSON serialization fails.
- **Design Decision**: Perform the JSON serialization inside a `try...except` block. If serialization fails, delete the `.tmp` file using `.unlink()` and re-raise the exception. If successful, perform `os.replace()` to atomically swap the file (which is atomic on both POSIX and Windows).
- **Code Logic**:
  ```python
  def save_registry(data: dict, path: Path):
      path.parent.mkdir(parents=True, exist_ok=True)
      tmp_path = path.with_suffix(path.suffix + ".tmp")
      serialized = False
      try:
          with open(tmp_path, "w", encoding="utf-8") as f:
              json.dump(data, f, indent=2)
          serialized = True
      except Exception as e:
          # Clean up temporary file on serialization failure
          try:
              if tmp_path.exists():
                  tmp_path.unlink()
          except Exception:
              pass
          raise e

      if serialized:
          os.replace(tmp_path, path)
  ```

### D. Path Resolution Helper (`get_project_dir()`)
To ensure clean DRY code, a helper is introduced to resolve the base directory of the active project under `projects/<project_name>/` relative to the root directory.
- **Code Logic**:
  ```python
  def get_project_dir() -> Path:
      return get_root_dir() / "projects" / get_project_name()
  ```

### E. Folder Helpers (With Side Effects)
- **Requirement**: Return `Path` objects and ensure the target directories exist.
- **Implementation**: Call `.mkdir(parents=True, exist_ok=True)` on the paths before returning them.
- **Code Logic**:
  ```python
  def get_chapters_dir() -> Path:
      d = get_project_dir() / "chapters"
      d.mkdir(parents=True, exist_ok=True)
      return d

  def get_edit_logs_dir() -> Path:
      d = get_project_dir() / "edit_logs"
      d.mkdir(parents=True, exist_ok=True)
      return d

  def get_eval_logs_dir() -> Path:
      d = get_project_dir() / "eval_logs"
      d.mkdir(parents=True, exist_ok=True)
      return d

  def get_briefs_dir() -> Path:
      d = get_project_dir() / "briefs"
      d.mkdir(parents=True, exist_ok=True)
      return d

  def get_typeset_dir() -> Path:
      d = get_project_dir() / "typeset"
      d.mkdir(parents=True, exist_ok=True)
      return d
  ```

### F. File Helpers (Pure Functions)
- **Requirement**: Return `Path` objects without creating directories or files.
- **Implementation**: Pure return of path segments without calling any filesystem mutation methods.
- **Code Logic**:
  ```python
  def get_outline_path() -> Path:
      return get_project_dir() / "outline.md"

  def get_state_path() -> Path:
      return get_project_dir() / "state.json"

  def get_results_path() -> Path:
      return get_project_dir() / "results.tsv"

  def get_registry_path() -> Path:
      return get_root_dir() / "projects" / "registry.json"

  def get_world_path() -> Path:
      return get_project_dir() / "world.md"

  def get_voice_path() -> Path:
      return get_project_dir() / "voice.md"

  def get_characters_path() -> Path:
      return get_project_dir() / "characters.md"

  def get_canon_path() -> Path:
      return get_project_dir() / "canon.md"

  def get_manuscript_path() -> Path:
      return get_project_dir() / "manuscript.md"

  def get_reviews_path() -> Path:
      return get_project_dir() / "reviews.md"

  def get_arc_summary_path() -> Path:
      return get_project_dir() / "arc_summary.md"
  ```

---

## 3. Proposal for Complete Refactored `utils.py`

This proposed content integrates the design patterns above into the existing `utils.py` codebase.

```python
import _utf8
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

# Global config/path state memory
_root_dir = None
_project_name = None

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


def get_root_dir() -> Path:
    """Walk up from __file__ to locate the project root containing pyproject.toml or .env."""
    global _root_dir
    if _root_dir is None:
        current = Path(__file__).resolve().parent
        while True:
            if (current / "pyproject.toml").exists() or (current / ".env").exists():
                _root_dir = current
                break
            parent = current.parent
            if parent == current:
                break
            current = parent
        if _root_dir is None:
            raise RuntimeError("Project root containing pyproject.toml or .env not found")
    return _root_dir


def set_project_name(name: str):
    """Set the active project name in global configuration memory."""
    global _project_name
    _project_name = name


def get_project_name() -> str:
    """Retrieve the active project name, falling back to AUTONOVEL_PROJECT env or 'default'."""
    global _project_name
    if _project_name is not None:
        return _project_name
    env_name = os.environ.get("AUTONOVEL_PROJECT")
    if env_name:
        return env_name
    return "default"


def get_project_dir() -> Path:
    """Helper to return the current project's base directory."""
    return get_root_dir() / "projects" / get_project_name()


def save_registry(data: dict, path: Path):
    """Atomically write registry JSON via .tmp file and rename, with cleanup if serialization fails."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    serialized = False
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        serialized = True
    except Exception as e:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        raise e

    if serialized:
        os.replace(tmp_path, path)


# --- Folder Helpers (with side effects) ---

def get_chapters_dir() -> Path:
    d = get_project_dir() / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_edit_logs_dir() -> Path:
    d = get_project_dir() / "edit_logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_eval_logs_dir() -> Path:
    d = get_project_dir() / "eval_logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_briefs_dir() -> Path:
    d = get_project_dir() / "briefs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_typeset_dir() -> Path:
    d = get_project_dir() / "typeset"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- File Helpers (pure functions) ---

def get_outline_path() -> Path:
    return get_project_dir() / "outline.md"


def get_state_path() -> Path:
    return get_project_dir() / "state.json"


def get_results_path() -> Path:
    return get_project_dir() / "results.tsv"


def get_registry_path() -> Path:
    return get_root_dir() / "projects" / "registry.json"


def get_world_path() -> Path:
    return get_project_dir() / "world.md"


def get_voice_path() -> Path:
    return get_project_dir() / "voice.md"


def get_characters_path() -> Path:
    return get_project_dir() / "characters.md"


def get_canon_path() -> Path:
    return get_project_dir() / "canon.md"


def get_manuscript_path() -> Path:
    return get_project_dir() / "manuscript.md"


def get_reviews_path() -> Path:
    return get_project_dir() / "reviews.md"


def get_arc_summary_path() -> Path:
    return get_project_dir() / "arc_summary.md"


# --- Existing Helpers Refactored & Retained ---

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
    """Retrieve novel title from state.json, resolving state path dynamically."""
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
