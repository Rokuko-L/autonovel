# Output Validation Layer (`core/validation.py`)

`llm.parse_json_response()` guarantees valid JSON but not valid *shape*.
Historically, a judge omitting `overall_score` or returning it as a string
silently poisoned downstream scores (`-1.0`, KeyError three phases later —
roughly half of all `fix:` commits in the git history). This module closes
that hole.

## Usage

```python
import validation

model = validation.parse_validated(
    validation.ScoreOutput, raw_text, context="Judge response")
data = model.model_dump()   # dict for legacy call sites
```

Raises `OutputValidationError` (subclass of `ValueError`) when the text has
no JSON or fails schema validation. `.feedback` carries an LLM-readable
explanation designed to be pasted into a self-correction retry prompt.

## Models

| Model | Required | Notes |
|---|---|---|
| `ScoreOutput` | `overall_score: float` (0–10) | Foundation/chapter evals. Extra keys allowed (dynamic genre dimensions). Coerces `"7.5"` and strips `/10`. |
| `NovelScoreOutput` | `novel_score: float` (0–10) | Full-novel eval. Same coercion. |
| `CompareOutput` | `winner: "A"\|"B"\|<chapter#>` | Head-to-head verdicts; normalizes case, accepts chapter numbers. |

## Where It's Wired

- `evaluate.call_judge_json(..., model=...)` — validates every attempt;
  schema failures join JSON-syntax failures in the LLM self-correction loop
  (the fix prompt quotes the validation feedback).
- `compare_chapters.compare()` — tournament verdicts.

**Rule:** any new judge/LLM JSON contract gets a Pydantic model here. Never
re-implement regex extraction for output that is already JSON.

Related: [llm-client.md](llm-client.md) ·
[../pipeline/scoring-engine.md](../pipeline/scoring-engine.md)
