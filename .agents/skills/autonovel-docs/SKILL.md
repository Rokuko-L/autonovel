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

### 2. Agent/human docs (Docs/)

| File | Contents |
|---|---|
| `Docs/overview.md` | entry point: module map, data flow, key rules, links to every doc |
| `Docs/workflow.md` | step-by-step run guide |
| `Docs/pipeline/spec.md` | full pipeline spec (phases, scoring, revision loop) |
| `Docs/pipeline/state-and-git.md` | state.json, registry, git keep/discard plumbing |
| `Docs/pipeline/scoring-engine.md` | how chapters get scored |
| `Docs/core/path-resolution.md` | project isolation, path helpers, atomic writes |
| `Docs/core/llm-client.md` | API client, retries, truncation, JSON repair |
| `Docs/core/output-validation.md` | Pydantic schemas for LLM output |
| `Docs/core/prompt-management.md` | prompts/ directory conventions |
| `Docs/systems/mock-testing.md` | offline testing with MockLLM |
| `Docs/reference/test-infra.md` | E2E test infrastructure |
| `Docs/reference/test-suites.md` | offline suite index |
| `Docs/reference/project-refactor.md` | completed multi-project refactor record |
| `README.md` | install, quick start, CLI reference |
| `AGENTS.md` | agent runbook (gitignored, local-only) |

## When to Update What

After a code change, update:

1. **New module / changed module responsibility** → `Docs/overview.md` module map (+ its own doc under `Docs/core/` or `Docs/pipeline/`)
2. **Changed path helper signatures or new file layout** → `Docs/core/path-resolution.md` + `Docs/reference/test-infra.md`
3. **Changed phase behavior, retry logic, thresholds** → `Docs/pipeline/spec.md` or `state-and-git.md`
4. **Changed scoring/penalties** → `Docs/pipeline/scoring-engine.md`
5. **Changed CLI flags or env vars** → `README.md` config table + `AGENTS.md`
6. **New/changed prompt template** → the `prompts/*.md` file itself; note it in `Docs/core/prompt-management.md`
7. **New judge JSON contract** → a Pydantic model in `core/validation.py`, documented in `Docs/core/output-validation.md`

## Guidelines

- Docs describe the code as it is — if docs and code disagree, fix one of them now, don't leave a note.
- Keep `AGENTS.md` current with launch/monitor quirks discovered during runs.
- Do not move the pipeline-fuel files; `gen_*.py` scripts read them from root paths.
