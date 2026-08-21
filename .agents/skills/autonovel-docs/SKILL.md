---
name: autonovel-docs
description: Read or update the autonovel repo's documentation. Use this skill when asked about project docs, to explain a system, to update docs after code changes, or when working in D:\Tugas\LLM\autonovel.
---

# autonovel Documentation Skill

## CRITICAL: Two Kinds of .md Files

This repo's markdown splits into two groups. Confusing them is the #1 mistake:

### 1. Pipeline fuel — NOT for coding agents (runtime LLM prompt material)

| File | Consumed by |
|---|---|
| `CRAFT.md` | `gen_world.py`, `gen_outline.py` — narrative craft rules fed to the writer model |
| `ANTI-SLOP.md` | pattern source for `evaluate.py` judge prompts |
| `voice.md` | template copied into each project by `run_pipeline.py`; Part 1 guardrails + Part 2 per-novel voice |
| `MYSTERY.md` | foundation-phase template ("author's eyes only") |
| `notes_template.md` | user premise template |

**Never** feed these into coding context as if they were project docs, and
never "clean them up" — editing them changes what the novel-writing LLM
produces. They are data.

### 2. Agent/human docs

| File | Contents |
|---|---|
| `README.md` | install, quick start, CLI reference |
| `ARCHITECTURE.md` | code module map, data flow, key rules, test suites |
| `PIPELINE.md` | full pipeline spec (phases, scoring, revision loop) |
| `WORKFLOW.md` | step-by-step run guide |
| `TEST_INFRA.md` | E2E test infrastructure |
| `PROJECT.md` | refactor tracker + interface contracts |
| `AGENTS.md` | agent runbook (gitignored, local-only) |

## When to Update What

After a code change, update:

1. **New module / changed module responsibility** → `ARCHITECTURE.md` module map
2. **Changed path helper signatures or new file layout** → `PROJECT.md` interface contracts + `TEST_INFRA.md`
3. **Changed phase behavior, retry logic, thresholds** → `PIPELINE.md`
4. **Changed CLI flags or env vars** → `README.md` config table + `AGENTS.md`
5. **New/changed prompt template** → the `prompts/*.md` file itself; note it in `ARCHITECTURE.md` only if it adds a rule
6. **New event type of failure the judge can produce** → consider a Pydantic model in `validation.py`, not more regex

## Guidelines

- Docs describe the code as it is — if docs and code disagree, fix one of them now, don't leave a note.
- Keep `AGENTS.md` current with launch/monitor quirks discovered during runs.
- Do not move the pipeline-fuel files; `gen_*.py` scripts read them from root paths.
