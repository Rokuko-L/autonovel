import _utf8
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

_root_dir = None
_project_name = None


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


# Keep BASE_DIR for backward compatibility
BASE_DIR = get_root_dir()


def set_project_name(name: str):
    """Set the active project name in global configuration memory."""
    global _project_name
    projects_root = (get_root_dir() / "projects").resolve()
    proposed_dir = (projects_root / name).resolve()
    try:
        is_rel = proposed_dir.is_relative_to(projects_root)
    except AttributeError:
        is_rel = proposed_dir == projects_root or projects_root in proposed_dir.parents
    if not is_rel or proposed_dir == projects_root:
        raise ValueError("Invalid project name: path isolation violation")
    _project_name = name
    os.environ["AUTONOVEL_PROJECT"] = name


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
    projects_root = (get_root_dir() / "projects").resolve()
    proposed_dir = (projects_root / get_project_name()).resolve()
    try:
        is_rel = proposed_dir.is_relative_to(projects_root)
    except AttributeError:
        is_rel = proposed_dir == projects_root or projects_root in proposed_dir.parents
    if not is_rel or proposed_dir == projects_root:
        raise ValueError("Invalid project name: path isolation violation")
    return proposed_dir


def save_registry(data: dict, path: Path):
    """Atomically write registry JSON via .tmp file and rename, with cleanup if serialization fails."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        raise e


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

def get_active_genre_path() -> Path:
    return get_project_dir() / "active_genre.json"


def get_seed_path() -> Path:
    return get_project_dir() / "seed.txt"


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

    import time
    import sys

    max_retries = 5
    backoff = 2
    for attempt in range(1, max_retries + 1):
        try:
            client = get_client()
            resp = client.post(
                f"{base_url.rstrip('/')}/v1/messages",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            return extract_text_from_response(resp)
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code in [400, 401, 403, 404]:
                raise e
            if attempt == max_retries:
                raise e
            print(f"API call failed (attempt {attempt}/{max_retries}): {e}. Retrying in {backoff}s...", file=sys.stderr)
            time.sleep(backoff)
            backoff *= 2


def get_novel_title():
    """Retrieve novel title from state.json, resolving state path dynamically."""
    state_path = get_state_path()
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if "title" in state:
                return state["title"]
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    return "the novel"


def format_prompt(template: str, **kwargs) -> str:
    """Format a template string by replacing both double-braced and single-braced placeholders."""
    for k, v in kwargs.items():
        template = template.replace(f"{{{{{k}}}}}", str(v))
        template = template.replace(f"{{{k}}}", str(v))
    return template

