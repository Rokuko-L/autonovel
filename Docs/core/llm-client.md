# LLM Client & JSON Repair (`core/llm.py`)

Every LLM call in the codebase flows through `call_llm()`. This is the
single interception point — `mock_llm.MockLLM` works by rebinding it.

## Providers

`call_llm` speaks two wire dialects and works with any endpoint that
serves either: first-party Anthropic/OpenAI, OpenRouter, Groq, Together,
LiteLLM proxies, DeepSeek's Anthropic-compat endpoint, vLLM/Ollama.

Dialect resolution per role (`writer`/`judge`/`review`):

1. `AUTONOVEL_{ROLE}_PROVIDER` (e.g. `AUTONOVEL_JUDGE_PROVIDER=anthropic`)
2. `AUTONOVEL_PROVIDER` (global default)
3. Inference: `OPENAI_API_KEY` set and `ANTHROPIC_API_KEY` unset → `openai`, else `anthropic`

Invalid values raise `ProviderError` naming the exact env var to fix.

### Wire differences handled internally

| Concern | Anthropic dialect | OpenAI dialect |
|---|---|---|
| Endpoint path | `/v1/messages` | `/chat/completions` |
| Auth | `x-api-key` + `anthropic-version` | `Authorization: Bearer` (only when key set — local gateways reject placeholder keys) |
| System prompt | top-level `system` | `{role: "system"}` message |
| Reasoning-style models (`o*`, `gpt-5*`) | — | `max_completion_tokens`, no `temperature` |
| Stop signal | `stop_reason` | `finish_reason` (`length` → `max_tokens`) |
| `beta_context=True` | 1M-context beta header | ignored (Anthropic-only), loud stderr note |

Responses are normalized to Anthropic vocabulary (`stop_reason`), so
`TruncationError` and every caller retry loop behave identically across
providers. Unsolicited SSE stream bodies are parsed for both chunk shapes.

### Config variables

| Variable | Purpose |
|---|---|
| `AUTONOVEL_PROVIDER` | Global dialect: `anthropic` \| `openai` |
| `AUTONOVEL_{ROLE}_PROVIDER` | Per-role dialect override |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` | Anthropic-dialect credentials + endpoint (any compat gateway) |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | OpenAI-dialect credentials + endpoint (include the `/v1` prefix if the gateway uses one) |
| `AUTONOVEL_{ROLE}_MODEL` | Model id — free-form string, gateway namespacing (`deepseek/deepseek-v4-pro`) works as-is |
| `AUTONOVEL_EXTRA_HEADERS` | JSON object merged into every request (OpenRouter `HTTP-Referer`/`X-Title`, etc.) |

## Key Types

| Symbol | Purpose |
|---|---|
| `call_llm(prompt, system, model_key, max_tokens, temperature, beta_context, timeout, raise_on_truncation)` | POST to the resolved provider endpoint with retries (5 attempts, exponential backoff; 4xx auth errors fail fast). |
| `resolve_provider(model_key)` | Dialect resolution (see precedence above). |
| `DEFAULT_MODELS` | Role → model per provider, used when the env var is unset. |
| `ProviderError` | Missing/invalid provider config; message names the env var. |
| `TruncationError` | Raised when the normalized stop reason is `max_tokens` (unless `raise_on_truncation=False`). Callers retry with larger budgets. |
| `extract_text_from_response` / `extract_text_and_stop_reason` | Take `dialect=`; handle JSON, SSE, and dict responses for both shapes. |
| `set_client(client)` | Test seam — install an `httpx.Client` (e.g. `MockTransport`). |
| `parse_json_response(text) -> dict \| list` | **Healing parser** — see below. |

## The Healing Parser

LLMs return damaged JSON constantly. `parse_json_response` recovers in layers:

1. Strip ``` fences
2. Locate first `{`/`[` and find its matching close via brace counting
   (ignores braces inside strings)
3. `repair_unescaped_quotes` — escape raw `"` inside string values using
   boundary lookahead (`is_json_boundary`)
4. Insert missing commas, strip trailing commas
5. `fix_truncated_json` — close open strings/braces for truncated output
   (logs a `[WARN] HEALED` to stderr with caller location)

The result is *syntactically* valid JSON. It says nothing about *shape* —
that is `validation.py`'s job.

## Retry Conventions

- Transport failures: handled inside `call_llm`.
- Truncation: callers catch `TruncationError` and re-ask with a larger
  `max_tokens` (see `draft_chapter.py`, `evaluate.call_judge_json`).
- Syntax errors + schema violations: callers catch and feed the error text
  back as a "fix your previous response" prompt (self-correction).

Wire-format behavior is pinned by `scratch/test_provider_llm.py`
(httpx.MockTransport asserts actual request shapes and response
normalization per dialect).

Related: [output-validation.md](output-validation.md) ·
[path-resolution.md](path-resolution.md)
