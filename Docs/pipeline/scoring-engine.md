# Scoring Engine (`pipeline/evaluate.py`)

Every keep/discard decision in the pipeline comes from this module. Two
independent signals are combined: a **mechanical slop score** (no LLM) and
an **LLM judge score**.

```
final_score = max(0, judge_overall_score - slop_penalty - length_penalty
                      - orientation_penalty)
```

## Mechanical Slop Score (`slop_score(text)`)

Deterministic detectors, each with its own penalty cap (global cap 4.0):

| Detector | Catches |
|---|---|
| Tier 1/2/3 word lists | "delve", "utilize", filler phrases |
| `FICTION_AI_TELLS` | prose clichés ("eyes widened", "a wave of X") |
| `STRUCTURAL_AI_TICS` | rhetorical formulas ("not just X, but Y") |
| `PROSE_TIC_PATTERNS` | density-based tic families — penalized only *per 3k words above threshold* (a single "not X, but Y" is human; a cluster is a machine) |
| Staccato runs | 3+ consecutive sentences ≤4 words |
| Em-dash density, sentence-length CV, transition-opener ratio | rhythm uniformity |
| Non-Latin script | glyphs EBGaramond can't render |

## LLM Judge

- `call_judge_json(prompt, model=...)` — judge call with self-correction
  retries for syntax AND schema failures (see
  [../core/output-validation.md](../core/output-validation.md)).
- Chapter eval prompt includes voice, world summary, characters, canon,
  the chapter's outline entry, previous-chapter tail, and disclosure ceiling.
- The judge also emits `new_canon_entries` (core vs incremental) and
  `unexplained_references`, which feed later chapters' canon files.

## Post-Judge Penalties (`evaluate_chapter`)

1. **Slop penalty** — subtracted from raw judge score (`raw_judge_score`
   preserved in eval logs).
2. **Length penalty** — ±3.0 scaled outside an 80%–125% window of target
   words (climax/finale chapters get a 155% ceiling).
3. **Orientation penalty** — up to −2.0 when ≥2 outline Orientation Facts
   aren't dramatized (synonym-aware matching).

## Eval Logs

Each run writes `projects/<name>/eval_logs/<timestamp>_<mode>.json` with the
full result dict. `_latest_chapter_score(n)` reads these back for the
full-novel evaluation's chapter metadata.

Related: [state-and-git.md](state-and-git.md) ·
[../core/output-validation.md](../core/output-validation.md) · [spec.md](spec.md)
