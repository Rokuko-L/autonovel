import os
from dotenv import load_dotenv
import httpx

load_dotenv()

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

    resp = httpx.post(
        f"{base_url.rstrip('/')}/v1/messages",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return extract_text_from_response(resp)


def get_novel_title():
    import json
    state_path = __import__("pathlib").Path(__file__).parent / "state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
            if "title" in state:
                return state["title"]
        except (json.JSONDecodeError, KeyError):
            pass
    return "the novel"
