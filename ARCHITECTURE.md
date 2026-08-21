# autonovel — Code Architecture

> What lives where in the *code*. For pipeline process/specs see
> [PIPELINE.md](PIPELINE.md); for run instructions see [WORKFLOW.md](WORKFLOW.md).

## Module Map

```
Core library (imported by every script)
├── paths.py        Project root/state resolution, folder+file path helpers,
│                   prompt loader (load_prompt), atomic registry writes
├── llm.py          Anthropic client (call_anthropic), response extraction,
│                   healing JSON parser (parse_json_response)
├── outline.py      Outline text ops: chapter headings, premise beats,
│                   plants/harvests validation, debt extraction
├── textstats.py    Context windows (tail/head), repetition detection
├── novel_tex.py    Default LaTeX novel.tex template generation
├── validation.py   Pydantic schema layer for LLM output (parse_validated)
└── mock_llm.py     Offline LLM mock for tests (MockLLM.install())

Pipeline
├── run_pipeline.py   Orchestrator: phases (foundation/drafting/revision/export),
│                     sanity checks, CLI
├── pipeline_infra.py Git plumbing, registry/state persistence, run_tool,
│                     score parsing, phase constants
├── gen_*.py          One script per generation task (world, characters,
│                     outline, canon, titles, briefs, revisions, tex)
├── evaluate.py       Scoring engine: mechanical slop + LLM judge
├── compare_chapters.py / reader_panel.py / review.py / adversarial_edit.py
└── gui.py            Desktop GUI (customtkinter)

Data (per-project, under projects/<name>/)
├── prompts/*.md      Shared prompt templates (loaded via paths.load_prompt)
└── CRAFT.md, ANTI-SLOP.md, voice.md, MYSTERY.md, notes_template.md
                     PIPELINE FUEL — runtime LLM prompt material, NOT agent docs
```

## Data Flow

```
gen_*.py scripts ──call──> llm.call_anthropic() ──> raw text
                        ──parse──> llm.parse_json_response()   (syntax heal)
                        ──validate──> validation.parse_validated()  (schema)
                        ──write──> paths.get_*_path() targets under projects/<name>/
run_pipeline.py orchestrates phases via pipeline_infra (state.json checkpoints,
git keep/discard per attempt, results.tsv score log)
```

## Key Rules

1. **All I/O through `paths.py` helpers** — never hardcode `projects/<name>/...`.
2. **Validate LLM JSON with Pydantic models** (`validation.ScoreOutput`, etc.);
   feed `OutputValidationError.feedback` back into self-correction retries.
3. **Static prompts live in `prompts/*.md`** — extract new ones instead of
   growing inline constants. Function-local f-string prompts may stay local
   until they stabilize.
4. **Test offline** with `mock_llm.MockLLM`; suites live in `scratch/test_*.py`
   and must pass without an API key.
5. **Atomic JSON writes** via tmp-file + rename (see `paths.save_registry`).
6. **Project-name path isolation**: any user-derived path component goes
   through `set_project_name`'s containment check.

## Test Suites (offline)

| Suite | Covers |
|---|---|
| `scratch/test_utils.py` | path helpers, project state |
| `scratch/test_utils_stress.py` | concurrency/traversal edge cases |
| `scratch/test_json_repair.py` | damaged-JSON healing |
| `scratch/test_encoding_healing.py` | UTF-16/latin-1 self-heal |
| `scratch/test_multi_project.py` | registry isolation |
| `scratch/test_path_contamination.py` | cross-project leakage |
| `scratch/test_mock_llm.py` | mock harness + validation retry integration |

Run all:

```bash
uv run python -m unittest discover -s scratch -p "test_*.py"
uv run python scratch/test_multi_project.py && uv run python scratch/test_path_contamination.py
```
