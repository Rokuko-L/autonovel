# AUTONOVEL — How to Run a Novel (runbook for future agents)

## Environment
- Repo: `/mnt/d/Tugas/LLM/autonovel` (WSL mount of `D:\Tugas\LLM\autonovel`)
- Python: `uv` with a fixed venv — ALWAYS prefix: `UV_PROJECT_ENVIRONMENT=/tmp/opencode/autonovel-wsl-venv uv run python <script>`
- API: `.env` → `ANTHROPIC_BASE_URL=http://localhost:20128` (local `next-server` proxy; check alive with `pgrep -f next-server`). Models: `writer_combo` for writer/judge/review.

## Launching a run (CRITICAL: setsid)
The bash tool kills the whole process group when a command times out — plain `nohup ... &` dies. Use `setsid` + short tool timeout:

```bash
cd /mnt/d/Tugas/LLM/autonovel && \
UV_PROJECT_ENVIRONMENT=/tmp/opencode/autonovel-wsl-venv setsid uv run python run_pipeline.py \
  --project "PROJECT NAME" --from-scratch \
  --genre "COMEDY FANTASY MISUNDERSTANDING" \
  --notes "projects/OLD PROJECT/seed.txt" \
  --chapters 24 --words-per-chapter 3000 --revision-cycles 3 \
  [--perspective first_person|third_person] \
  > /tmp/opencode/run_launch.log 2>&1 < /dev/null &
```
Then return immediately (tool timeout ~15s OK); verify with `pgrep -af run_pipeline.py`.

Notes:
- `--genre` is REQUIRED for a fresh project (sanity check exits otherwise). Reuse the old project's `active_genre.json` → `genre_name` field.
- `--notes <path>`: reads the file; if >1500 words it's summarized for the genre framework while the FULL doc goes to the new project's `seed.txt`. Same behavior as the original run.
- New project dir = `projects/<name>/`; follow the "`<name> v2`" pattern to preserve old runs.
- `--from-scratch` wipes the project dir (safe on a fresh name).
- Resume after crash: rerun the SAME command WITHOUT `--from-scratch` — state.json picks up the current phase.

## Monitoring (10-min cadence)
- Launch log: `/tmp/opencode/run_launch.log`. NOTE: output is block-buffered — the log can sit stale/0B while work progresses. Watch FILES, not just the log:
  - `projects/<name>/state.json` → `phase`, `chapters_drafted`, `novel_score`, `revision_cycle`
  - `projects/<name>/results.tsv` → per-attempt scores (`discarded`/`keep`/`forced`)
  - file mtimes in the project dir (outline.md, canon.md, chapters/ch_XX.md)
- Loop: `sleep 600` with tool timeout `630000`.

## Timing (24 ch / 3000w / 3 cycles ≈ 7-9 h total)
- Foundation: ~1 h (genre framework 2 passes, world, characters, outline 1+2, titles, canon)
- Drafting: ~15-20 min/chapter incl. eval + possible retries (max 5 attempts; slop-dominant drafts get in-place `repair_slop.py` instead of blind regen)
- Revision: 3 cycles, adversarial edits run 4-wide (default `AUTONOVEL_MAX_WORKERS=4`)
- Export: ~30-45 min (build_outline 12-wide, arc summary, manuscript, tectonic PDF at `projects/<name>/typeset/novel.pdf`)

## Known behavior / quirks
- Low-scoring chapters are almost always MECHANICAL slop (staccato runs, `not X but Y`, `x_of_y` frames), not foundation/evaluator faults — raw judge scores stay 7.5-8.7 while slop penalties drag the total.
- Premise-beat validation may retry up to 5x (now tolerant of beats distributed across the outline).
- `build_outline.py` retries transient failures 3x internally; if export still FATALs, just resume.
- max_tokens truncation crashes are recovered by resume (state saved per phase/chapter).
- PDF chapter titles are normalized at write time; slug titles (`shadow_compact_ambush`) are rejected at the outline stage.
