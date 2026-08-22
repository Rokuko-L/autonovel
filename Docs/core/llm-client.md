# LLM Client & JSON Repair (`core/llm.py`)

Every LLM call in the codebase flows through `call_anthropic()`. This is the
single interception point — `mock_llm.MockLLM` works by rebinding it.

## Key Types

| Symbol | Purpose |
|---|---|
| `call_anthropic(prompt, system, model_key, max_tokens, temperature, beta_context, timeout, raise_on_truncation)` | POST to `/v1/messages` with retries (5 attempts, exponential backoff; 4xx auth errors fail fast). |
| `DEFAULT_MODELS` / `MODEL_ENV_VARS` | `writer`/`judge`/`review` roles → `AUTONOVEL_WRITER_MODEL` etc. |
| `TruncationError` | Raised when `stop_reason == "max_tokens"` (unless `raise_on_truncation=False`). Callers retry with larger budgets. |
| `extract_text_from_response` / `extract_text_and_stop_reason` | Handle both JSON and SSE responses. |
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

- Transport failures: handled inside `call_anthropic`.
- Truncation: callers catch `TruncationError` and re-ask with a larger
  `max_tokens` (see `draft_chapter.py`, `evaluate.call_judge_json`).
- Syntax errors + schema violations: callers catch and feed the error text
  back as a "fix your previous response" prompt (self-correction).

Related: [output-validation.md](output-validation.md) ·
[path-resolution.md](path-resolution.md)

## Call Telemetry

Every `call_anthropic` attempt appends one JSON line to the active project's
`llm_events.jsonl` (path helper: `paths.get_llm_events_path()`). Event fields:
`ts, model_key, model, ok, attempt, tokens_in, tokens_out, duration_ms,
stop_reason, prompt_chars, response_chars, prompt_head` — failures add
`error`. This feeds the webui's token stats and LLM inspector; telemetry
failures are swallowed by design and never break generation.
