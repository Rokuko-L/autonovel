<div align="center">

# autonovel

An autonomous pipeline that writes a complete novel from a single premise.
Feed it a genre and a one-sentence idea — it builds the world, characters,
outline, drafts every chapter, revises them, and exports a finished manuscript.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch): the same modify-evaluate-keep/discard loop, applied to fiction.

</div>

## What is this?

autonovel is a fully automated novel-generation pipeline. You provide a genre and a premise, and it:

1. **Generates a genre configuration** — system prompts, evaluation criteria, and generation templates tailored to your genre
2. **Builds the foundation** — world bible, character registry, chapter outline, foreshadowing ledger, canon
3. **Drafts every chapter** — writes sequentially with automatic retries on low scores
4. **Revises the manuscript** — adversarial editing, reader panel evaluations, automated revision briefs, rewrite cycles with plateau detection
5. **Exports a finished PDF** — LaTeX typeset novel with a professionally designed layout

Each phase scores its output and only keeps improvements (modify → evaluate → keep/discard).

## What You Need to Install

### Essentials

| Dependency | Version | Why |
|------------|---------|-----|
| [Python](https://www.python.org/downloads/) | 3.12+ | Runtime |
| [uv](https://docs.astral.sh/uv/#installation) | latest | Package manager (replaces pip) |
| An API key | — | LLM provider (see below) |

### Install uv

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify: `uv --version`

### Get an API Key

autonovel supports any Anthropic-compatible provider:

- **Anthropic** — get a key at https://console.anthropic.com/
- **DeepSeek** — get a key at https://platform.deepseek.com/ and use `https://api.deepseek.com/anthropic` as base URL
- **OpenRouter** — get a key at https://openrouter.ai/ and use their Anthropic-compatible endpoint

### Optional: Tectonic (for PDF export)

Required only if you want the pipeline to compile the novel into a PDF.

**Windows:**
```powershell
scoop install tectonic
```
Or download from [GitHub Releases](https://github.com/tectonic-typesetting/tectonic/releases) — place `tectonic.exe` somewhere in your PATH.

**macOS:**
```bash
brew install tectonic
```

**Linux:**
```bash
sudo apt install tectonic          # Debian/Ubuntu
sudo dnf install tectonic          # Fedora
sudo pacman -S tectonic            # Arch
```
Or download the Linux binary from [GitHub Releases](https://github.com/tectonic-typesetting/tectonic/releases).

Verify: `tectonic --version`

### Optional: EB Garamond Fonts (for PDF typesetting)

The LaTeX output uses EB Garamond. If you skip this, the PDF build will fail at the font stage.

Run the included installer script:
```bash
uv run python install_fonts.py
```

Or install manually:

**Windows:**
Download from [Google Fonts](https://fonts.google.com/specimen/EB+Garamond) and install for your user (double-click the `.ttf` files → Install).

**macOS:**
```bash
brew install --cask font-eb-garamond
```

**Linux:**
```bash
sudo apt install fonts-ebgaramond
```

## Quick Start

```bash
git clone <repo-url> && cd autonovel
cp .env.example .env
# Edit .env with your API key and model choices

# Run the full pipeline from scratch
uv run python run_pipeline.py --from-scratch \
  --genre "Cyberpunk Noir" \
  --chapters 12 \
  --notes "Detective with a heart condition"
```

The first run sets up the project, installs dependencies automatically, and starts the foundation phase. A complete novel (12 chapters) takes roughly 20–40 minutes depending on the model.

The `--notes` flag accepts a raw string or a file path (`--notes my_ideas.txt`). The pipeline auto-expands short notes (<300 words) and auto-summarizes long ones (>1500).

## Configuration

Copy `.env.example` to `.env` and set:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTONOVEL_PROVIDER` | inferred | API dialect for all roles: `anthropic` or `openai` |
| `AUTONOVEL_{ROLE}_PROVIDER` | — | Per-role dialect override (e.g. cheap `openai` writer + `anthropic` judge) |
| `ANTHROPIC_API_KEY` | — | Anthropic-dialect key (first-party or any compat gateway) |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | Anthropic-dialect endpoint — e.g. `https://api.deepseek.com/anthropic` for DeepSeek |
| `OPENAI_API_KEY` | — | OpenAI-dialect key (first-party, OpenRouter, Groq, Together, LiteLLM…) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-dialect endpoint — keep gateway prefixes like `/api/v1` or `/v1` |
| `AUTONOVEL_WRITER_MODEL` | provider default (`claude-sonnet-4-6` / `gpt-5.2`) | Model for drafting and revision (free-form id, gateway namespacing OK) |
| `AUTONOVEL_JUDGE_MODEL` | provider default (`claude-opus-4-6` / `gpt-5.2`) | Model for evaluation and scoring |
| `AUTONOVEL_REVIEW_MODEL` | provider default (`claude-opus-4-6` / `gpt-5.2`) | Model for deep prose analysis |
| `AUTONOVEL_EXTRA_HEADERS` | — | JSON object merged into every request (e.g. OpenRouter's `HTTP-Referer`/`X-Title`) |
| `AUTONOVEL_GENRE` | — | Default genre (instead of `--genre`) |
| `AUTONOVEL_CHAPTERS` | `24` | Default chapter count |
| `AUTONOVEL_NOTES` | — | Default story premise |
| `AUTONOVEL_PROJECT` | `default` | Active project name |
| `AUTONOVEL_FOUNDATION_THRESHOLD` | `7.5` | Foundation exit gate (plateaus exit after 3 stalled iterations) |

### Example: DeepSeek `.env` (Anthropic dialect)

```
ANTHROPIC_API_KEY=sk-deepseek-your-key
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
AUTONOVEL_WRITER_MODEL=deepseek-v4-flash
AUTONOVEL_JUDGE_MODEL=deepseek-v4-pro
AUTONOVEL_REVIEW_MODEL=deepseek-v4-pro
```

### Example: OpenRouter `.env` (OpenAI dialect)

```
AUTONOVEL_PROVIDER=openai
OPENAI_API_KEY=sk-or-v1-your-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
AUTONOVEL_EXTRA_HEADERS={"HTTP-Referer": "https://your-site.example", "X-Title": "autonovel"}
AUTONOVEL_WRITER_MODEL=anthropic/claude-sonnet-4.5
AUTONOVEL_JUDGE_MODEL=deepseek/deepseek-v4-pro
AUTONOVEL_REVIEW_MODEL=anthropic/claude-opus-4.5
```

### Example: mixed providers (cheap writer, strong judge)

```
AUTONOVEL_PROVIDER=openai
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-v1-your-key
AUTONOVEL_JUDGE_PROVIDER=anthropic
AUTONOVEL_JUDGE_MODEL=claude-opus-4-6
AUTONOVEL_WRITER_MODEL=deepseek/deepseek-v4-pro
```

## Pipeline Phases

### Foundation
Builds the genre config, world bible, character registry, chapter outline, foreshadowing ledger, and canon. Each iteration generates all five documents, scores them, and keeps only improvements. Loops until `foundation_score > 7.5` or max iterations.

### Drafting
Writes chapters sequentially. Each chapter is evaluated after drafting — low scores trigger a retry with the critique as additional context.

### Revision
Adversarial editing → apply cuts → reader panel → generate briefs → rewrite chapters. Plateau detection stops the loop when scores stabilize. A full-manuscript dual-persona review catches structural and prose-level issues.

### Export
Rebuilds the outline from final chapters, generates an arc summary, builds LaTeX content, and compiles the PDF via tectonic.

## CLI

```bash
uv run python run_pipeline.py                                # resume from state
uv run python run_pipeline.py --from-scratch ...              # start fresh
uv run python run_pipeline.py --phase foundation              # run one phase
uv run python run_pipeline.py --phase drafting
uv run python run_pipeline.py --phase revision --max-cycles 5
uv run python run_pipeline.py --phase export
uv run python run_pipeline.py --genre "Horror" --chapters 8 --notes "file.txt"
uv run python run_pipeline.py --project mynovel               # multi-project
uv run python run_pipeline.py --project mynovel --from-scratch
```

All flags can also be set via environment variables (`AUTONOVEL_GENRE`, `AUTONOVEL_CHAPTERS`, `AUTONOVEL_NOTES`).

## Project Structure

> The full module map and data flow live in [Docs/overview.md](Docs/overview.md).

```
.
├── core/                    Shared library (paths, llm, outline, textstats,
│                            novel_tex, genre, validation, mock_llm)
├── pipeline/                Stage scripts (evaluate, draft_chapter, review,
│                            reader_panel, adversarial_edit, apply_cuts,
│                            repair_slop, build_*, gen_brief, gen_revision,
│                            sanitize_outline_titles, voice_fingerprint,
│                            gen_novel_tex, pipeline_infra)
├── foundation/              Foundation generators (gen_genre_framework,
│                            gen_world, gen_characters, gen_outline*,
│                            gen_canon, gen_title, seed)
├── prompts/                 Static prompt templates
├── Docs/                    Documentation (start at overview.md)
├── projects/                Multi-project workspaces (gitignored)
│   ├── registry.json
│   └── <project_name>/      state.json, chapters/, eval_logs/, typeset/...
├── scratch/                 Offline test suites
├── typeset/                 LaTeX build helper
├── run_pipeline.py          Pipeline orchestrator (entry point)
├── gui.py                   Desktop GUI (entry point)
└── install_fonts.py         EB Garamond font installer
```

## Scripts Reference

| Script | Phase | Purpose |
|--------|-------|---------|
| `foundation/gen_genre_framework.py` | Foundation | Initialize genre config via 2-pass LLM meta-prompt |
| `foundation/gen_world.py` | Foundation | Seed → world bible |
| `foundation/gen_characters.py` | Foundation | Seed + world → character registry |
| `foundation/gen_outline.py` | Foundation | Chapter-by-chapter outline |
| `foundation/gen_outline_part2.py` | Foundation | Foreshadowing ledger |
| `foundation/gen_canon.py` | Foundation | Cross-reference hard facts |
| `pipeline/voice_fingerprint.py` | Foundation | Quantitative prose analysis |
| `pipeline/draft_chapter.py` | Drafting | Write one chapter |
| `pipeline/run_drafts.py` | Drafting | Batch sequential drafter |
| `pipeline/evaluate.py` | All | Mechanical slop scorer + LLM judge |
| `pipeline/adversarial_edit.py` | Revision | "Cut 500 words" analysis |
| `pipeline/apply_cuts.py` | Revision | Batch cut applicator |
| `pipeline/reader_panel.py` | Revision | 4-persona evaluation |
| `pipeline/gen_brief.py` | Revision | Auto-generate revision briefs |
| `pipeline/gen_revision.py` | Revision | Rewrite from a brief |
| `pipeline/review.py` | Revision | Full-manuscript dual-persona review |
| `pipeline/build_arc_summary.py` | Revision | Generate arc summary |
| `pipeline/compare_chapters.py` | Revision | Head-to-head Elo tournament |
| `pipeline/gen_novel_tex.py` | Export | Generate custom LaTeX template via LLM |
| `run_pipeline.py` | Orchestration | Full pipeline controller |
| `gui.py` | — | Desktop GUI (customtkinter) |

## Design

The novel is five co-evolving layers:

```
Voice / Style     → How we write
World / Setting   → What exists
Characters        → Who acts
Outline           → What happens (in what order)
Chapters          → The actual prose
Canon             → What is true (cross-cutting)
```

Changes propagate downward (lore change → outline change → chapter revision) and upward (writing reveals a gap → update lore). The pipeline tracks propagation debts in `state.json`.

## License

[MIT](LICENSE)

---

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=Rokuko-L/autonovel&type=Date)](https://star-history.com/#Rokuko-L/autonovel&Date)

</div>
