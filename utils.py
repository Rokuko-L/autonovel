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
    if isinstance(resp, dict):
        data = resp
    else:
        content_type = resp.headers.get("content-type", "")
        if "text/event-stream" in content_type or not resp.text.strip().startswith("{"):
            text_content = ""
            for line in resp.text.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        continue
                    try:
                        import json
                        item = json.loads(data_str)
                        if item.get("type") == "content_block_delta":
                            delta = item.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text_content += delta.get("text", "")
                    except json.JSONDecodeError:
                        pass
            data = {
                "content": [
                    {
                        "type": "text",
                        "text": text_content
                    }
                ]
            }
        else:
            data = resp.json()

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


def is_json_boundary(text: str, idx: int, is_key: bool) -> bool:
    """Check if the lookahead character indicates this quote is a JSON structural boundary."""
    n = len(text)
    j = idx
    while j < n and text[j].isspace():
        j += 1
    if j == n:
        return True
    
    c = text[j]
    if is_key:
        return c == ':'
    else:
        if c in ('}', ']'):
            return True
        if c == ',':
            # Check what follows the comma; it must be a valid JSON key, value, or closing brace
            k = j + 1
            while k < n and text[k].isspace():
                k += 1
            if k == n:
                return True
            next_c = text[k]
            if next_c in ('"', '{', '[', '}', ']'):
                return True
            if next_c.isdigit() or next_c == '-':
                return True
            if next_c in ('t', 'f', 'n'):
                word = text[k:k+5]
                if word.startswith('true') or word.startswith('false') or word.startswith('null'):
                    return True
            return False
        if c == '"':
            # Lookahead check for missing commas: see if this starts a new key (e.g. "key":)
            k = j + 1
            while k < n and text[k] != '"':
                k += 1
            if k < n:
                k += 1
                while k < n and text[k].isspace():
                    k += 1
                if k < n and text[k] == ':':
                    return True
            return False
        return False


def repair_unescaped_quotes(text: str) -> str:
    """Escapes unescaped double quotes inside JSON string values."""
    result = []
    in_value_string = False
    is_key = False
    i = 0
    n = len(text)
    stack = []  # Track open containers: '{' or '['
    
    while i < n:
        c = text[i]
        
        # Track containers if we are outside any string
        if not in_value_string:
            if c in ('{', '['):
                stack.append(c)
            elif c in ('}', ']'):
                if stack:
                    stack.pop()
                    
        if c == '"':
            # Check if this quote is already escaped
            is_escaped = False
            backslashes = 0
            k = i - 1
            while k >= 0 and text[k] == '\\':
                backslashes += 1
                k -= 1
            if backslashes % 2 == 1:
                is_escaped = True
                
            if is_escaped:
                result.append(c)
                i += 1
                continue
                
            if not in_value_string:
                # Entering a JSON key or string value
                # Determine if it's a key or a value
                if stack and stack[-1] == '[':
                    # Inside an array, it's always a value string
                    is_key = False
                else:
                    # Inside an object or at top-level
                    last_char = None
                    k = len(result) - 1
                    while k >= 0:
                        if not result[k].isspace():
                            last_char = result[k]
                            break
                        k -= 1
                    is_key = (last_char != ':')
                
                in_value_string = True
                result.append(c)
                i += 1
            else:
                # Inside a string. Check if this is the closing boundary quote
                if is_json_boundary(text, i + 1, is_key):
                    in_value_string = False
                    result.append(c)
                else:
                    result.append('\\"')
                i += 1
        else:
            result.append(c)
            i += 1
            
    return "".join(result)


def fix_truncated_json(text: str) -> str:
    """Heal truncated JSON strings by closing open string values and structures."""
    in_string = False
    escape = False
    stack = []
    
    for i, c in enumerate(text):
        if escape:
            escape = False
            continue
        if c == '\\' and in_string:
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c in ('{', '['):
            stack.append(c)
        elif c in ('}', ']'):
            if stack:
                stack.pop()
                
    if in_string:
        text += '"'
    for open_char in reversed(stack):
        if open_char == '{':
            text += '}'
        elif open_char == '[':
            text += ']'
    return text


def parse_json_response(text: str) -> dict | list:
    """Extract and heal JSON from LLM response text."""
    import re
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        
    start = text.find('{')
    if start == -1:
        start = text.find('[')
    if start == -1:
        raise ValueError("No JSON object or array found in response")
        
    json_part = text[start:]
    
    # Run repairs
    json_part = repair_unescaped_quotes(json_part)
    
    # Missing commas repair (avoiding escaped quotes using negative lookbehind (?<!\\))
    json_part = re.sub(
        r'(?<!\\)("|\d|\]|\}|true|false|null)\s+(?<!\\)(\s*"([^"]+)"\s*:)',
        r'\1,\n\2',
        json_part
    )
    
    # Trailing commas repair
    json_part = re.sub(r',\s*([\}\]])', r'\1', json_part)
    
    # Heal truncated JSON
    json_part = fix_truncated_json(json_part)
    
    return json.loads(json_part, strict=False)


