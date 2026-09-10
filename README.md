<div align="center">

# gesaku

**An autonomous pipeline that writes a complete novel from a single premise.**

Feed it a genre and a one-sentence idea — it builds the world, characters, and outline, drafts every chapter, revises against its own scores, and exports a finished PDF.

Built for two kinds of operators: **agents** that drive it from the CLI, and **humans** who watch the same run live in a web console.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — the modify → evaluate → keep/discard loop, applied to fiction.

</div>

---

## What you get

| | |
|---|---|
| **Pipeline** | Genre config → foundation (world / characters / outline / canon) → sequential drafting → adversarial revision with plateau detection → LaTeX PDF |
| **CLI** | `uv run gesaku run --json` — launch, stream structured events, stop. Same supervisor as the UI. |
| **Console** | `uv run gesaku` — React + FastAPI operator console on `:8600` (projects, pipeline dashboard, scores, SSE live feed) |
| **Providers** | Anthropic *or* OpenAI dialect — DeepSeek, OpenRouter, Groq, Together, LiteLLM, first-party, … per-role overrides |
| **Multi-project** | Isolated workspaces under `projects/<name>/` with their own state, logs, and git history |

Every phase scores its output and only keeps improvements.

---

## Quick start

```bash
git clone https://github.com/Rokuko-L/gesaku.git && cd gesaku
cp .env.example .env
# put an API key in .env (see Configuration)

# agent-style: start a novel, stream JSONL
uv run gesaku run --project demo --from-scratch \
  --genre "Cyberpunk Noir" \
  --chapters 12 \
  --notes "Detective with a heart condition" \
  --json
```

In another terminal (optional, same run):

```bash
uv run gesaku                 # open the console — project appears live
uv run gesaku status --json
uv run gesaku logs -f --project demo
```

A 12-chapter novel typically takes **20–40+ minutes** of wall time depending on models and retries.

`--notes` accepts a string or a file path. Short notes (&lt;300 words) are auto-expanded; long ones (&gt;1500) auto-summarized.

---

## Install

| Need | Why |
|------|-----|
| [Python 3.12+](https://www.python.org/downloads/) | Runtime |
| [uv](https://docs.astral.sh/uv/#installation) | Deps + `uv run gesaku` |
| An API key | Any Anthropic- or OpenAI-compatible endpoint |
| Node 20+ | Only for console `--dev` / rebuilding the SPA |
| [Tectonic](https://tectonic-typesetting.github.io/) | Only for PDF export |
| EB Garamond fonts | Only for PDF typesetting (`uv run python install_fonts.py`) |

```bash
# uv (Windows)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# uv (macOS / Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Optional global binary:

```bash
uv tool install .
gesaku --help
```

---

## Three ways to run

### 1. Agent / CLI (no browser)

Same `RunManager` + `projects/<name>/run.json` contract as the console — the UI shows CLI-launched runs unchanged.

```bash
# stream human logs
uv run gesaku run --project noir --genre "…" --notes premise.txt --from-scratch

# machine-readable JSONL (for agents)
uv run gesaku run --project noir --json
uv run gesaku run --project noir --detach --json    # fire-and-forget

uv run gesaku status --json
uv run gesaku logs --project noir -f
uv run gesaku stop --project noir
```

Flags after `run` that the agent CLI doesn’t claim are passed through to `run_pipeline.py` (`--from-scratch`, `--phase`, `--chapters`, …).

**JSONL event types:** `started` · `log` · `phase` · `score` · `warn` · `error` · `fatal` · `state` · `done`

### 2. Operator console

```bash
uv run gesaku              # built SPA + API on http://127.0.0.1:8600
uv run gesaku --dev        # vite HMR :5175, API :8600
uv run gesaku --no-open
```

First time in `--dev`: `cd webui/frontend && npm install`.  
Static mode uses `webui/frontend/dist` (build with `npm run build` if you changed the frontend).

### 3. Raw orchestrator

```bash
uv run python run_pipeline.py --from-scratch --genre "…" --notes "…"
uv run python run_pipeline.py --phase foundation
uv run python run_pipeline.py --phase drafting
uv run python run_pipeline.py --phase revision --revision-cycles 5
uv run python run_pipeline.py --phase export
uv run python run_pipeline.py --project mynovel --from-scratch
```

---

## Configuration

Copy `.env.example` → `.env`.

### Providers & models

| Variable | Default | Purpose |
|----------|---------|---------|
| `GESAKU_PROVIDER` | inferred | Dialect for all roles: `anthropic` \| `openai` |
| `GESAKU_{ROLE}_PROVIDER` | — | Per-role override (`WRITER` / `JUDGE` / `REVIEW`) |
| `ANTHROPIC_API_KEY` | — | Anthropic-dialect key |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | Anthropic-dialect endpoint |
| `OPENAI_API_KEY` | — | OpenAI-dialect key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-dialect endpoint (keep `/v1` or `/api/v1`) |
| `GESAKU_WRITER_MODEL` | provider default | Drafting & revision |
| `GESAKU_JUDGE_MODEL` | provider default | Chapter / foundation scoring |
| `GESAKU_REVIEW_MODEL` | provider default | Deep prose review |
| `GESAKU_EXTRA_HEADERS` | — | JSON object merged into every request |

### Run defaults & gates

| Variable | Default | Purpose |
|----------|---------|---------|
| `GESAKU_PROJECT` | `default` | Project name under `projects/` |
| `GESAKU_GENRE` | — | Default genre |
| `GESAKU_CHAPTERS` | `24` | Default chapter count |
| `GESAKU_NOTES` | — | Default premise |
| `GESAKU_PERSPECTIVE` | — | `first_person` \| `third_person` (empty = foundation decides) |
| `GESAKU_FOUNDATION_THRESHOLD` | `7.5` | Foundation exit gate |
| `GESAKU_CHAPTER_THRESHOLD` | `6.5` | Per-chapter keep gate |
| `GESAKU_MAX_CHAPTER_ATTEMPTS` | `5` | Draft retries |
| `GESAKU_MIN_REVISION_CYCLES` | `3` | Floor before plateau stop |
| `GESAKU_MAX_REVISION_CYCLES` | `6` | Revision cap |
| `GESAKU_PLATEAU_DELTA` | `0.3` | Score delta that counts as stalled |

### Examples

**DeepSeek (Anthropic dialect)**

```
ANTHROPIC_API_KEY=sk-deepseek-…
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
GESAKU_WRITER_MODEL=deepseek-v4-flash
GESAKU_JUDGE_MODEL=deepseek-v4-pro
GESAKU_REVIEW_MODEL=deepseek-v4-pro
```

**OpenRouter (OpenAI dialect)**

```
GESAKU_PROVIDER=openai
OPENAI_API_KEY=sk-or-v1-…
OPENAI_BASE_URL=https://openrouter.ai/api/v1
GESAKU_EXTRA_HEADERS={"HTTP-Referer": "https://your-site.example", "X-Title": "gesaku"}
GESAKU_WRITER_MODEL=anthropic/claude-sonnet-4.5
GESAKU_JUDGE_MODEL=deepseek/deepseek-v4-pro
```

**Mixed: cheap writer, strong judge**

```
GESAKU_PROVIDER=openai
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-v1-…
GESAKU_JUDGE_PROVIDER=anthropic
GESAKU_JUDGE_MODEL=claude-opus-4-6
GESAKU_WRITER_MODEL=deepseek/deepseek-v4-pro
```

---

## Pipeline

```
Foundation   genre config · world · characters · outline · ledger · canon
             loop until foundation_score ≥ threshold (plateau-aware)

Drafting     sequential chapters; each scored; low scores retry with critique

Revision     adversarial edit → cuts → reader panel → briefs → rewrites
             + full-manuscript review; stops on plateau or max cycles

Export       rebuild outline · arc summary · LaTeX · tectonic PDF
```

The novel is six co-evolving layers (voice, world, characters, outline, chapters, canon). Changes propagate down and up; debts are tracked in `state.json`.

---

## Layout

```
core/           paths · llm · validation · outline · textstats · mock_llm
pipeline/       evaluate · draft_chapter · revision · review · export helpers
foundation/     gen_genre_framework · gen_world · gen_characters · gen_outline* …
prompts/        static LLM templates (paths.load_prompt)
webui/          server.py (FastAPI :8600) + frontend/ (React 19 + Vite)
projects/       per-novel workspaces (gitignored)
scratch/        offline unittest suites (MockLLM)
cli.py          gesaku — console + agent commands
run_pipeline.py orchestrator
Docs/           start at overview.md
```

Module map and data flow: [Docs/overview.md](Docs/overview.md).  
Operator console API: [Docs/systems/console-bridge.md](Docs/systems/console-bridge.md).

### Stage scripts

| Script | Phase | Role |
|--------|-------|------|
| `foundation/gen_genre_framework.py` | Foundation | Genre prompts + eval criteria |
| `foundation/gen_world.py` · `gen_characters.py` · `gen_outline*.py` · `gen_canon.py` | Foundation | World, cast, outline, ledger, canon |
| `pipeline/voice_fingerprint.py` | Foundation | Quantitative voice analysis |
| `pipeline/draft_chapter.py` · `run_drafts.py` | Drafting | Sequential chapters |
| `pipeline/evaluate.py` | All | Mechanical slop + LLM judge |
| `pipeline/adversarial_edit.py` · `apply_cuts.py` · `reader_panel.py` · `gen_brief.py` · `gen_revision.py` · `review.py` | Revision | Edit, cut, panel, brief, rewrite, review |
| `pipeline/compare_chapters.py` | Revision | Head-to-head tournament |
| `pipeline/gen_novel_tex.py` | Export | LaTeX template via LLM |
| `run_pipeline.py` | Orchestration | Phase controller |
| `cli.py` | CLI | `gesaku` console + agent commands |

---

## Development

```bash
uv run --frozen ruff check --select F821,F811 .
uv run --frozen python -m unittest discover -s scratch -p "test_*.py"
```

Offline tests use `MockLLM` / mock transports — no network required. CI also proves the suite stays green with a black-hole `ANTHROPIC_BASE_URL`.

---

## License

[MIT](LICENSE)

---

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=Rokuko-L/gesaku&type=Date)](https://star-history.com/#Rokuko-L/gesaku&Date)

</div>
