# autonovel

An autonomous pipeline for writing a complete novel from a single premise. Feed it a genre and a one-sentence idea — it builds the world, characters, outline, drafts every chapter, revises them, and exports the finished manuscript.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch): the same modify-evaluate-keep/discard loop, applied to fiction.

---

## Quick Start

```bash
git clone <repo-url> && cd autonovel
cp .env.example .env    # Add your API key

# Run the pipeline from scratch
uv run python run_pipeline.py --from-scratch \
  --genre "Cyberpunk Noir" \
  --chapters 12 \
  --notes "Detective with a heart condition"
```

The `--notes` flag is the single source of truth. It accepts a raw string or a file path (`--notes my_ideas.txt`). The pipeline auto-expands short notes (<300 words) or auto-summarizes long ones (>1500).

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An API key for [Anthropic](https://console.anthropic.com/) or any Anthropic-compatible provider (DeepSeek, OpenRouter, etc.)
- **(Optional) [Tectonic](https://tectonic-typesetting.github.io/)**: Required if you want to automatically compile the generated novel into a beautiful typeset PDF.
  - *Windows*: `scoop install tectonic` (or download from GitHub Releases)
  - *macOS*: `brew install tectonic`
  - *Linux*: `sudo apt install tectonic` (or package manager equivalent)

---

## Configuration

Copy `.env.example` to `.env` and set:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | — | API key |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | API endpoint (set to `https://api.deepseek.com/anthropic` for DeepSeek) |
| `AUTONOVEL_WRITER_MODEL` | `claude-sonnet-4-6` | Model for writing tasks |
| `AUTONOVEL_JUDGE_MODEL` | `claude-opus-4-6` | Model for evaluation |
| `AUTONOVEL_REVIEW_MODEL` | `claude-opus-4-6` | Model for revision |
| `AUTONOVEL_GENRE` | — | Default genre (instead of `--genre`) |
| `AUTONOVEL_CHAPTERS` | `24` | Default chapter count |
| `AUTONOVEL_NOTES` | — | Default story premise |

---

## Pipeline Phases

### Foundation
Builds the world bible, character registry, chapter outline, foreshadowing ledger, and canon. Each iteration generates all five documents, scores them, and keeps only improvements. Loops until `foundation_score > 7.5` or max iterations.

### Drafting
Writes chapters sequentially. Each chapter is evaluated after drafting — low scores trigger a retry. Forward progress over perfection.

### Revision
Adversarial editing → apply cuts → reader panel → generate briefs → rewrite chapters. Plateau detection stops the loop when scores stabilize. Then a full-manuscript review catches structural and prose-level issues.

### Export
Compiles all chapters into a single manuscript document. Ready for final formatting.

---

## CLI

```
python run_pipeline.py                           # resume from state
python run_pipeline.py --from-scratch ...         # start fresh
python run_pipeline.py --phase foundation         # run one phase
python run_pipeline.py --genre "Horror" --chapters 8 --notes "file.txt"
```

All flags can also be set via environment variables (`AUTONOVEL_GENRE`, `AUTONOVEL_CHAPTERS`, `AUTONOVEL_NOTES`).

---

## Scripts

| Script | Phase | Purpose |
|--------|-------|---------|
| `gen_genre_framework.py` | Foundation | Initialize genre config via meta-prompt |
| `gen_world.py` | Foundation | Seed → world bible |
| `gen_characters.py` | Foundation | Seed + world → character registry |
| `gen_outline.py` | Foundation | Chapter-by-chapter outline |
| `gen_outline_part2.py` | Foundation | Foreshadowing ledger |
| `gen_canon.py` | Foundation | Cross-reference hard facts |
| `voice_fingerprint.py` | Foundation | Quantitative prose analysis |
| `draft_chapter.py` | Drafting | Write one chapter |
| `evaluate.py` | All | Mechanical slop scorer + LLM judge |
| `adversarial_edit.py` | Revision | "Cut 500 words" analysis |
| `apply_cuts.py` | Revision | Batch cut applicator |
| `reader_panel.py` | Revision | 4-persona evaluation |
| `gen_brief.py` | Revision | Auto-generate revision briefs |
| `gen_revision.py` | Revision | Rewrite from a brief |
| `review.py` | Revision | Full-manuscript dual-persona review |
| `run_pipeline.py` | Orchestration | Full pipeline controller |

---

## File Structure

```
active_genre.json    — Genre configuration (auto-generated)
seed.txt             — Expanded story premise (auto-generated from --notes)
state.json           — Pipeline state tracker
chapters/            — Drafted chapter files
briefs/              — Revision briefs
edit_logs/           — Voice fingerprint, evaluation scores
typeset/             — LaTeX template and build tools
```

---

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
