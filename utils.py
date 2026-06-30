import _utf8
import os
import json
import re
import itertools
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


def get_logs_dir() -> Path:
    d = get_project_dir() / "logs"
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


class TruncationError(Exception):
    """Raised when the API response was truncated (stop_reason == 'max_tokens')."""
    pass


def _parse_response_json(text: str) -> dict:
    """Parse (possibly damaged) JSON from an Anthropic response string."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(text)
        return obj


def extract_text_from_response(resp):
    if isinstance(resp, dict):
        data = resp
    else:
        raw = resp.text.strip()
        content_type = resp.headers.get("content-type", "")
        is_sse = "text/event-stream" in content_type and any(
            l.strip().startswith("data:") for l in raw.splitlines()
        )
        if is_sse or not raw.startswith("{"):
            text_content = ""
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        continue
                    try:
                        item = json.loads(data_str)
                        if item.get("type") == "content_block_delta":
                            delta = item.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text_content += delta.get("text", "")
                    except json.JSONDecodeError:
                        pass
            data = {
                "content": [{"type": "text", "text": text_content}]
            }
        else:
            data = _parse_response_json(raw)

    for block in data["content"]:
        if block["type"] == "text":
            return block["text"]
    return ""


def extract_text_and_stop_reason(resp):
    """Return (text, stop_reason) from a non-streaming Anthropic response.

    stop_reason is None for streaming responses; otherwise one of
    'end_turn', 'max_tokens', 'stop_sequence', or None.
    """
    if isinstance(resp, dict):
        data = resp
        text_content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_content += block.get("text", "")
        return text_content, data.get("stop_reason")

    raw = resp.text.strip()
    content_type = resp.headers.get("content-type", "")
    is_sse = "text/event-stream" in content_type and any(
        l.strip().startswith("data:") for l in raw.splitlines()
    )
    if is_sse or not raw.startswith("{"):
        text_content = ""
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    continue
                try:
                    item = json.loads(data_str)
                    if item.get("type") == "content_block_delta":
                        delta = item.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text_content += delta.get("text", "")
                except json.JSONDecodeError:
                    pass
        return text_content, None

    data = _parse_response_json(raw)
    for block in data["content"]:
        if block["type"] == "text":
            return block["text"], data.get("stop_reason")
    return "", data.get("stop_reason")


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
    raise_on_truncation=False,
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
            if raise_on_truncation:
                text, stop_reason = extract_text_and_stop_reason(resp)
                if stop_reason == "max_tokens":
                    raise TruncationError(
                        f"Response truncated at ~{len(text.split())} words "
                        f"(stop_reason: max_tokens)"
                    )
                return text
            return extract_text_from_response(resp)
        except TruncationError:
            raise
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
    is_obj = True
    if start == -1 or (text.find('[') != -1 and text.find('[') < start):
        start = text.find('[')
        is_obj = False
    if start == -1:
        raise ValueError("No JSON object or array found in response")
        
    # Count braces/brackets to find the matching closing character,
    # thereby stripping any trailing conversation text that causes JSON decode errors.
    brace_count = 0
    in_string = False
    escape = False
    end_idx = len(text)
    for idx in range(start, len(text)):
        c = text[idx]
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
        if c == ('{' if is_obj else '['):
            brace_count += 1
        elif c == ('}' if is_obj else ']'):
            brace_count -= 1
            if brace_count == 0:
                end_idx = idx + 1
                break
                
    json_part = text[start:end_idx]
    
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


def generate_default_novel_tex(dest_path: Path):
    """Generate a default novel.tex wrapper template for LaTeX typesetting."""
    seed_path = get_seed_path()

    # Try to extract title from state.json (pipeline stores the real title here)
    title = "A Novel"
    try:
        state_title = get_novel_title()
        if state_title and state_title.lower() not in ("a novel", "the novel", "untitled"):
            title = state_title
    except Exception:
        pass
    if title == "A Novel":
        # Fallback to seed.txt first line
        if seed_path.exists():
            try:
                with open(seed_path, encoding="utf-8") as f:
                    first_line = f.readline()
                    if first_line.startswith("#"):
                        title = first_line.lstrip("#").strip()
            except Exception:
                pass

    # Try to resolve author name from git config
    author = "Author Name"
    try:
        import subprocess
        author = subprocess.check_output(["git", "config", "user.name"], text=True).strip()
    except Exception:
        pass

    # Basic clean formatting
    title_escaped = title.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")
    author_escaped = author.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")

    # Load epigraph if theme exists
    epigraph_block = ""
    if seed_path.exists():
        try:
            import re
            content = seed_path.read_text(encoding="utf-8")
            # Look for thematic core paragraph
            match = re.search(r"##\s*Thematic\s*Core\s*\n\n(.*?)(?:\n\n|\Z)", content, re.DOTALL | re.IGNORECASE)
            if match:
                theme_text = match.group(1).strip()
                # Split lines for poetry-like typesetting in epigraph
                theme_lines = theme_text.split(". ")
                theme_lines_tex = "\\\\\n  ".join(line.strip() + "." if not line.endswith(".") else line.strip() for line in theme_lines if line.strip())
                epigraph_block = f"""% === EPIGRAPH ===
\\newcommand{{\\makeepigraph}}{{%
  \\thispagestyle{{empty}}
  \\vspace*{{2.5in}}
  \\begin{{center}}
  \\begin{{minipage}}{{3in}}
  \\begin{{center}}
  \\itshape
  {theme_lines_tex}\\\\[12pt]
  \\end{{center}}
  \\end{{minipage}}
  \\end{{center}}
  \\clearpage
}}"""
        except Exception:
            pass

    # If no epigraph was extracted, create a simple empty one
    if not epigraph_block:
        epigraph_block = """% === EPIGRAPH ===
\\newcommand{\\makeepigraph}{%
  \\thispagestyle{empty}
  \\clearpage
}"""

    # Generate standard template content
    template = f"""\\documentclass[11pt, openany]{{book}}

% === GEOMETRY: Trade paperback (5.5 x 8.5 inches) ===
\\usepackage[
  paperwidth=5.5in,
  paperheight=8.5in,
  inner=0.85in,
  outer=0.65in,
  top=0.75in,
  bottom=0.85in,
  headheight=14pt
]{{geometry}}

% === FONTS ===
\\usepackage{{fontspec}}
\\setmainfont{{EBGaramond}}[
  UprightFont = EBGaramond-Regular,
  ItalicFont  = EBGaramond-Italic,
  BoldFont    = EBGaramond-Regular,
  BoldItalicFont = EBGaramond-Italic,
]

% === TYPOGRAPHY ===
\\usepackage{{microtype}}
\\usepackage{{setspace}}
\\setstretch{{1.12}}
\\usepackage{{parskip}}
\\setlength{{\\parindent}}{{1.5em}}
\\setlength{{\\parskip}}{{0pt}}

% === GRAPHICS ===
\\usepackage{{graphicx}}

% === DROP CAPS ===
\\usepackage{{lettrine}}
\\setcounter{{DefaultLines}}{{2}}

% === HEADERS AND FOOTERS ===
\\usepackage{{fancyhdr}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyhead[LE]{{\\small\\textsc{{{title_escaped.lower()}}}}}
\\fancyhead[RO]{{\\small\\textit{{\\leftmark}}}}
\\fancyfoot[C]{{\\thepage}}
\\renewcommand{{\\headrulewidth}}{{0pt}}

\\fancypagestyle{{plain}}{{
  \\fancyhf{{}}
  \\fancyfoot[C]{{\\thepage}}
  \\renewcommand{{\\headrulewidth}}{{0pt}}
}}

% === CHAPTER STYLE ===
\\usepackage{{titlesec}}

% Ornamental bell motif (using dingbats)
\\newcommand{{\\bellornament}}{{%
  \\par\\noindent\\vspace{{6pt}}%
  \\hfill{{\\large\\symbol{{"2756}}}}\\hfill\\null%
  \\vspace{{6pt}}\\par%
}}

% Scene break ornament
\\newcommand{{\\scenebreak}}{{%
  \\par\\vspace{{0.6\\baselineskip}}%
  \\noindent\\hfil%
  \\IfFileExists{{../art/pdf/scene_break.pdf}}{{%
    \\includegraphics[width=1.2in]{{../art/pdf/scene_break.pdf}}%
  }}{{%
  \\IfFileExists{{../art/scene_break.png}}{{%
    \\includegraphics[width=1.2in]{{../art/scene_break.png}}%
  }}{{%
    {{\\small\\symbol{{"2022}}\\quad\\symbol{{"2022}}\\quad\\symbol{{"2022}}}}%
  }}}}%
  \\hfil%
  \\par\\vspace{{0.6\\baselineskip}}%
}}

\\renewcommand{{\\thechapter}}{{\\Roman{{chapter}}}}
\\titleformat{{\\chapter}}[display]
  {{\\normalfont\\centering}}
  {{\\vspace*{{1.5in}}\\footnotesize\\textsc{{chapter \\thechapter}}}}
  {{4pt}}
  {{\\Large\\itshape}}
  [\\vspace{{8pt}}{{\\small--- $\\diamond$ ---}}\\vspace{{0.5in}}]

\\titlespacing*{{\\chapter}}{{0pt}}{{0pt}}{{0pt}}

% Lowercase chapter name in header
\\renewcommand{{\\chaptermark}}[1]{{\\markboth{{#1}}{{}}}}

% === TITLE PAGE DESIGN ===
\\newcommand{{\\makenoveltitle}}{{%
  \\thispagestyle{{empty}}
  \\begin{{center}}
  \\vspace*{{2in}}
  
  {{\\Huge\\textsc{{{title_escaped}}}}}\\\\[0.4in]
  
  {{\\small------\\quad$\\diamond$\\quad------}}\\\\[0.5in]
  
  {{\\large\\textit{{A Novel}}}}\\\\[1in]
  
  {{\\Large\\textsc{{{author_escaped}}}}}\\\\[1.5in]
  
  \\end{{center}}
  \\clearpage
}}

{epigraph_block}

% === HALF TITLE ===
\\newcommand{{\\makehalftitle}}{{%
  \\thispagestyle{{empty}}
  \\vspace*{{3in}}
  \\begin{{center}}
  {{\\large\\textsc{{{title_escaped}}}}}
  \\end{{center}}
  \\clearpage
}}

% === PDF METADATA ===
\\usepackage{{hyperref}}
\\hypersetup{{
  pdftitle={{{title_escaped}}},
  pdfauthor={{{author_escaped}}},
  hidelinks
}}

% === BEGIN DOCUMENT ===
\\begin{{document}}

\\frontmatter

% Full-bleed cover image (if exists)
\\IfFileExists{{../art/cover.png}}{{%
  \\thispagestyle{{empty}}
  \\newgeometry{{margin=0pt}}
  \\noindent\\includegraphics[width=\\paperwidth, height=\\paperheight, keepaspectratio]{{../art/cover.png}}%
  \\restoregeometry%
  \\clearpage%
}}{{}}

% Half title
\\makehalftitle

% Blank verso
\\thispagestyle{{empty}}
\\mbox{{}}
\\clearpage

% Title page
\\makenoveltitle

% Copyright / colophon
\\thispagestyle{{empty}}
\\vspace*{{\\fill}}
\\begin{{center}}

{{\\small This is a work of fiction.}}\\\\[18pt]

\\end{{center}}
\\vspace*{{\\fill}}
\\clearpage

% Epigraph
\\makeepigraph

% Blank verso before main text
\\thispagestyle{{empty}}
\\mbox{{}}
\\clearpage

\\mainmatter

% === CHAPTERS ===
\\input{{chapters_content.tex}}

% === END MATTER ===
\\backmatter

\\thispagestyle{{empty}}
\\vspace*{{3in}}
\\begin{{center}}
{{\\small------\\quad$\\diamond$\\quad------}}\\\\[0.3in]
{{\\small\\textit{{The page turned.}}}}
\\end{{center}}

\\end{{document}}
"""
    dest_path.write_text(template, encoding="utf-8")


def validate_generator_output(content: str, name: str, min_len: int = 100, expected_headers: list[str] | None = None) -> str:
    """Guardrail: check a foundation generator's output is non-empty, meets min length,
    and has expected headers. Returns the stripped content on success.
    Raises RuntimeError on failure."""
    content = content.strip()
    if not content:
        raise RuntimeError(f"{name}: output is empty")
    if len(content) < min_len:
        raise RuntimeError(f"{name}: output too short ({len(content)} chars, minimum {min_len})")
    if expected_headers:
        for h in expected_headers:
            if h not in content:
                raise RuntimeError(f"{name}: output missing expected header '{h}'")
    return content


def _normalize_beat_label(label: str) -> str:
    """Normalize a beat label for fuzzy matching — remove bold, POV, numbering."""
    label = re.sub(r'\*\*', '', label)
    label = re.sub(r'\([^)]*\)', '', label)
    label = re.sub(r'^\d+[\.\)]\s*', '', label)
    label = label.replace('_', ' ').replace('/', ' ').replace('-', ' ')
    label = re.sub(r'\s+', ' ', label).strip()
    return label.lower()


def _beats_match(required: str, present: str) -> bool:
    """Token-set containment check: all required words appear in present label."""
    r_tokens = set(_normalize_beat_label(required).split())
    p_tokens = set(_normalize_beat_label(present).split())
    return r_tokens.issubset(p_tokens) and len(r_tokens) > 0


def _parse_bold_numbered_beats(outline_text: str) -> list[dict]:
    """Fallback — extract beats from bold-numbered header format.

    Handles:
      **1. beat_label (POV info)**
      Paragraph text accumulates as scene_summary until next beat header.
      *1. beat_label* (single-asterisk variant)
    """
    lines = outline_text.split('\n')
    in_section = False
    beats = []
    current_beat = None
    current_summary: list[str] = []

    for line in lines:
        stripped = line.strip()

        header_match = re.match(
            r'^#{0,3}\s*\**\s*PREMISE\s+BEATS\**\s*:?\**\s*$', stripped, re.IGNORECASE
        )
        if header_match:
            in_section = True
            continue

        if not in_section:
            continue

        end_match = re.match(
            r'^(?:#{1,3}\s|MAIN\s+PLOT)', stripped, re.IGNORECASE
        )
        if end_match:
            if current_beat is not None:
                beats.append({"beat": current_beat, "scene_summary": ' '.join(current_summary).strip()})
            break

        beat_header_match = re.match(
            r'^\s*\*+\s*\d+[\.\)]\s+(.+?)\s*\*+\s*$', stripped
        )
        if beat_header_match:
            if current_beat is not None:
                beats.append({"beat": current_beat, "scene_summary": ' '.join(current_summary).strip()})
            current_beat = beat_header_match.group(1).strip()
            current_summary = []
            continue

        if current_beat is not None and stripped:
            current_summary.append(stripped)

    if in_section and current_beat is not None:
        beats.append({"beat": current_beat, "scene_summary": ' '.join(current_summary).strip()})

    return beats


def _parse_plain_numbered_beats(outline_text: str) -> list[dict]:
    """Fallback — extract beats from plain numbered format:

      1. beat_label: scene summary
      2. beat_label: scene summary

    Matches the style most models naturally produce when told a 'numbered list'.
    """
    lines = outline_text.split('\n')
    in_section = False
    beats = []

    for line in lines:
        stripped = line.strip()

        header_match = re.match(
            r'^#{0,3}\s*\**\s*PREMISE\s+BEATS\**\s*:?\**\s*$', stripped, re.IGNORECASE
        )
        if header_match:
            in_section = True
            continue

        end_match = re.match(
            r'^(?:#{1,3}\s|MAIN\s+PLOT)', stripped, re.IGNORECASE
        )
        if in_section and end_match:
            break

        if in_section:
            numbered_match = re.match(r'^\s*\d+[\.\)]\s+(.+)$', stripped)
            if not numbered_match:
                continue
            content = numbered_match.group(1).strip()
            colon_idx = content.find(':')
            if colon_idx == -1:
                beats.append({"beat": content.strip(), "scene_summary": ""})
            else:
                beat_label = content[:colon_idx].strip()
                scene_summary = content[colon_idx + 1:].strip()
                beats.append({"beat": beat_label, "scene_summary": scene_summary})

    return beats


def parse_premise_beats(outline_text: str) -> list[dict]:
    """
    Extract premise beats from Chapter 1's PREMISE BEATS section in the outline.
    Returns list of {"beat": str, "scene_summary": str} in order found.
    Returns empty list if no PREMISE BEATS section is found.

    Tries three formats in order:
      1. Bullet lines:  - beat_label: scene summary
      2. Plain numbered: N. beat_label: scene summary
      3. Bold-numbered: **N. beat_label (POV info)** then paragraph
    """
    lines = outline_text.split('\n')
    in_section = False
    beats = []

    for line in lines:
        stripped = line.strip()

        header_match = re.match(
            r'^#{0,3}\s*\**\s*PREMISE\s+BEATS\**\s*:?\**\s*$', stripped, re.IGNORECASE
        )
        if header_match:
            in_section = True
            continue

        end_match = re.match(
            r'^(?:#{1,3}\s|MAIN\s+PLOT)', stripped, re.IGNORECASE
        )
        if in_section and end_match:
            break

        if in_section:
            bullet_match = re.match(r'^[-*+]\s+(.+)$', stripped)
            if not bullet_match:
                continue
            content = bullet_match.group(1).strip()
            colon_idx = content.find(':')
            if colon_idx == -1:
                beats.append({"beat": content.strip(), "scene_summary": ""})
            else:
                beat_label = content[:colon_idx].strip()
                scene_summary = content[colon_idx + 1:].strip()
                beats.append({"beat": beat_label, "scene_summary": scene_summary})

    if not beats:
        beats = _parse_plain_numbered_beats(outline_text)
    if not beats:
        beats = _parse_bold_numbered_beats(outline_text)

    return beats


def validate_premise_beats(required_beats: list[str], outline_text: str) -> tuple[bool, str]:
    """
    Validate that Chapter 1's PREMISE BEATS section contains all required beats
    in relative order (subsequence match, not exact match — extra unlisted beats
    between required ones are allowed).  Uses token-set matching so human-readable
    labels like "Ordinary World / Otaku Life" match slug keys like
    "ordinary_world_otaku_life".

    Returns (passed: bool, error_message: str).
    """
    present = parse_premise_beats(outline_text)
    present_labels = [b["beat"] for b in present]

    if not present_labels:
        return False, "No PREMISE BEATS section found in Chapter 1 outline"

    missing = []
    it = iter(present_labels)
    for required in required_beats:
        found = False
        for p in it:
            if _beats_match(required, p):
                found = True
                break
        if not found:
            missing.append(required)

    if missing:
        return False, f"Missing premise beat(s): {', '.join(missing)}"

    return True, ""


# --- Repetition detection ---

def shingled_jaccard(a: str, b: str, n: int = 4) -> float:
    """Token n-gram Jaccard similarity between two strings."""
    a_tokens = a.lower().split()
    b_tokens = b.lower().split()
    if len(a_tokens) < n or len(b_tokens) < n:
        return 0.0
    shingles_a = set(zip(*[a_tokens[i:] for i in range(n)]))
    shingles_b = set(zip(*[b_tokens[i:] for i in range(n)]))
    if not shingles_a or not shingles_b:
        return 0.0
    return len(shingles_a & shingles_b) / len(shingles_a | shingles_b)


def detect_repeated_paragraphs(
    text: str,
    min_words: int = 12,
    jaccard_threshold: float = 0.55,
    ngram: int = 4,
) -> tuple[list[tuple[int, int, float]], list[str]]:
    """Find near-duplicate paragraph pairs in text.

    Splits on double-newlines, filters out short paragraphs and `---`
    separators. Returns (pairs, paragraphs) where each pair is
    (idx_a, idx_b, similarity) and paragraphs is the filtered list
    (indices correspond).
    """
    raw = [p.strip() for p in text.strip().split('\n\n') if p.strip()]
    expanded = [p for p in raw if not p.startswith('---')]
    filtered = [(i, p) for i, p in enumerate(expanded) if len(p.split()) >= min_words]
    pairs: list[tuple[int, int, float]] = []
    for (i, p1), (j, p2) in itertools.combinations(filtered, 2):
        sim = shingled_jaccard(p1, p2, n=ngram)
        if sim >= jaccard_threshold:
            pairs.append((i, j, sim))
    return pairs, expanded


def chain_flagged_pairs(
    pairs: list[tuple[int, int, float]],
    max_gap: int = 3,
    max_offset: int = 30,
) -> list[list[tuple[int, int, float]]]:
    """Cluster pairs whose (j-i) distance is similar and positions are near.

    Two pairs (i1,j1) and (i2,j2) chain if |(j1-i1) - (j2-i2)| <= max_gap
    AND |i2 - i1| <= max_offset. This groups structurally repeated templates
    (same offset recurring at different absolute positions) while keeping
    isolated refrains separate.
    """
    if not pairs:
        return []
    parent = list(range(len(pairs)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for a in range(len(pairs)):
        i1, j1, _ = pairs[a]
        d1 = j1 - i1
        for b in range(a + 1, len(pairs)):
            i2, j2, _ = pairs[b]
            d2 = j2 - i2
            if abs(d1 - d2) <= max_gap and abs(i2 - i1) <= max_offset:
                union(a, b)

    from collections import defaultdict
    clusters: dict[int, list[tuple[int, int, float]]] = defaultdict(list)
    for idx, p in enumerate(pairs):
        clusters[find(idx)].append(p)
    return list(clusters.values())


def check_structural_repetition(
    text: str,
    min_words: int = 12,
    jaccard_threshold: float = 0.55,
    high_sim_threshold: float = 0.85,
    ngram: int = 4,
    max_gap: int = 3,
    max_offset: int = 30,
) -> tuple[bool, list[str], dict]:
    """Run full repetition check and return (regen, feedback_lines, sidecar).

    Decision logic:
    - A chained cluster is structural if it has >=3 high-sim pairs
      (the reaction-rules for-loop pattern).
    - Additionally, any unchained pair with sim >= high_sim_threshold
      is structural (short duplicated block like a repeated letter).
    """
    pairs, paras = detect_repeated_paragraphs(
        text, min_words, jaccard_threshold, ngram
    )
    clusters = chain_flagged_pairs(pairs, max_gap, max_offset)

    feedback: list[str] = []
    sidecar_clusters: list[dict] = []

    for cluster in clusters:
        indices = sorted(set(p[0] for p in cluster) | set(p[1] for p in cluster))
        n_pairs = len(cluster)
        n_paras = len(indices)
        sims = [s for _, _, s in cluster]
        high_sim = sum(1 for s in sims if s >= high_sim_threshold)

        # Rep pick: paragraph that appears in the most pairs
        counts: dict[int, int] = {}
        for i, j, _ in cluster:
            counts[i] = counts.get(i, 0) + 1
            counts[j] = counts.get(j, 0) + 1
        rep_idx = max(counts, key=lambda k: counts[k])
        rep_text = paras[rep_idx][:200] if rep_idx < len(paras) else ""

        is_structural = high_sim >= 3

        entry = {
            "n_paras": n_paras,
            "n_pairs": n_pairs,
            "high_sim": high_sim,
            "min_sim": round(min(sims), 3),
            "offsets": sorted(set(j - i for i, j, _ in cluster)),
            "indices": indices,
            "representative": rep_text[:120],
            "is_structural": is_structural,
        }
        sidecar_clusters.append(entry)

        if is_structural:
            feedback.append(
                f"The following passage (or something nearly identical to it) "
                f"appeared in {n_paras} different places:\n"
                f'  "{rep_text}..."\n'
                f"This repeated block appeared {n_pairs} times. "
                f"Each occurrence should be a distinct moment — vary the "
                f"content or cut the repetition entirely. Do not reuse the same "
                f"scene-setting beats (checking the quest log, looking at the "
                f"calendar, etc.) as a template for multiple list items.\n"
            )

    # Individual high-sim pairs within non-structural clusters
    # (catches isolated duplicates like a repeated letter quotation
    # that don't form a structural for-loop pattern)
    flagged_individual_pairs: list[dict] = []
    seen_paras: set[int] = set()
    for cluster in clusters:
        i0, j0, _ = cluster[0]
        is_struct = sum(1 for _, _, s in cluster if s >= high_sim_threshold) >= 3
        if is_struct:
            continue
        for i, j, sim in cluster:
            if sim >= high_sim_threshold:
                if i not in seen_paras:
                    seen_paras.add(i)
                    rep_text = paras[i][:200] if i < len(paras) else ""
                    feedback.append(
                        f"The following passage appeared near-verbatim in 2 places:\n"
                        f'  "{rep_text}..."\n'
                    )
                    flagged_individual_pairs.append({
                        "idx_a": i, "idx_b": j, "sim": round(sim, 3),
                        "representative": rep_text[:120],
                    })

    sidecar = {
        "regen_requested": len(feedback) > 0,
        "total_pairs": len(pairs),
        "total_clusters": len(clusters),
        "clusters": sidecar_clusters,
        "flagged_individual_pairs": flagged_individual_pairs,
    }

    return len(feedback) > 0, feedback, sidecar

