import _utf8
import os
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()


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


try:
    BASE_DIR = get_root_dir()
except RuntimeError:
    BASE_DIR = Path(__file__).resolve().parent

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


# Folder helpers (return Path objects and ensure directory exists)

def get_chapters_dir() -> Path:
    d = get_root_dir() / "projects" / get_project_name() / "chapters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_edit_logs_dir() -> Path:
    d = get_root_dir() / "projects" / get_project_name() / "edit_logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_eval_logs_dir() -> Path:
    d = get_root_dir() / "projects" / get_project_name() / "eval_logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_briefs_dir() -> Path:
    d = get_root_dir() / "projects" / get_project_name() / "briefs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_typeset_dir() -> Path:
    d = get_root_dir() / "projects" / get_project_name() / "typeset"
    d.mkdir(parents=True, exist_ok=True)
    return d


# File helpers (pure functions returning Path objects without file/directory creation side effects)

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
