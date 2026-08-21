"""Anthropic API client, response extraction, and JSON repair."""

import os
import sys
import json
import re

import httpx


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

def _warn_unused_trailing(text: str, consumed_len: int) -> None:
    """Warn to stderr when a response contains content after the first JSON value."""
    import sys
    trailing = text[consumed_len:].strip()
    if trailing:
        print(
            f"  [WARN] JSON parse dropped {len(trailing)} trailing chars after the first "
            f"JSON value (possible second object or conversation tail): "
            f"{trailing[:80]!r}...",
            file=sys.stderr,
        )

def _parse_response_json(text: str) -> dict:
    """Parse (possibly damaged) JSON from an Anthropic response string."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        obj, end = decoder.raw_decode(text)
        _warn_unused_trailing(text, end)
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
                        if item.get("type") == "message":
                            for block in item.get("content", []):
                                if block.get("type") == "text":
                                    text_content += block.get("text", "")
                        elif item.get("type") == "content_block_delta":
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
        stop_reason = None
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    continue
                try:
                    item = json.loads(data_str)
                    if item.get("type") == "message":
                        for block in item.get("content", []):
                            if block.get("type") == "text":
                                text_content += block.get("text", "")
                        if item.get("stop_reason"):
                            stop_reason = item["stop_reason"]
                    elif item.get("type") == "content_block_delta":
                        delta = item.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text_content += delta.get("text", "")
                    elif item.get("type") == "message_delta":
                        if item.get("delta", {}).get("stop_reason"):
                            stop_reason = item["delta"]["stop_reason"]
                except json.JSONDecodeError:
                    pass
        return text_content, stop_reason

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
    raise_on_truncation=True,
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
    healed = fix_truncated_json(json_part)
    if healed != json_part:
        import traceback
        caller = traceback.extract_stack(limit=4)[-2]
        print(
            f"  [WARN] parse_json_response HEALED truncated JSON from {caller.filename.split('/')[-1]}:{caller.lineno} "
            f"(appended {len(healed) - len(json_part)} closing chars — partial data will be used as-is)",
            file=sys.stderr,
        )
        json_part = healed
        # Healing can manufacture a trailing comma (e.g. "…[1," → "[1,]") — repair it.
        json_part = re.sub(r',\s*([\}\]])', r'\1', json_part)
    
    if end_idx < len(text) and text[end_idx:].strip():
        import traceback
        caller = traceback.extract_stack(limit=4)[-2]
        print(
            f"  [WARN] parse_json_response ignored {len(text[end_idx:].strip())} trailing chars after the "
            f"closing brace from {caller.filename.split('/')[-1]}:{caller.lineno}",
            file=sys.stderr,
        )
    
    return json.loads(json_part, strict=False)
