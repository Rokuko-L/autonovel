#!/usr/bin/env python3
"""
run_pipeline.py — Fully automated novel pipeline orchestrator.

Runs the complete autonovel pipeline from seed concept to finished novel.
Manages state, git commits, evaluation, and retry logic.

Usage:
  python run_pipeline.py --project mynovel  # run from current state for project
  python run_pipeline.py --project mynovel --from-scratch     # start fresh
  python run_pipeline.py --project mynovel --from-scratch --genre "Horror" --chapters 8 --notes "haunted school"
                                           # auto-creates seed.txt from notes
  python run_pipeline.py --project mynovel --phase foundation # run only foundation
  python run_pipeline.py --project mynovel --phase drafting   # run only drafting
  python run_pipeline.py --project mynovel --phase revision   # run only revision
  python run_pipeline.py --project mynovel --phase export     # run only export
  python run_pipeline.py --project mynovel --max-cycles 4     # limit revision cycles
"""

import _utf8
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from genre import load_genre
from utils import call_anthropic
import utils

load_dotenv()

# ---------------------------------------------------------------------------
# Constants  (all path-dependent values are resolved at runtime via utils)
# ---------------------------------------------------------------------------

FOUNDATION_THRESHOLD = 7.5
CHAPTER_THRESHOLD = 7.0
MAX_FOUNDATION_ITERS = 20
MAX_CHAPTER_ATTEMPTS = 5
MIN_REVISION_CYCLES = 3
MAX_REVISION_CYCLES = 6
PLATEAU_DELTA = 0.3
CHAPTERS_TOTAL = 24  # default; overridden by genre config at runtime

PHASE_ORDER = ["foundation", "drafting", "revision", "export"]


# ---------------------------------------------------------------------------
# Git & registry helpers (Option B: per-project repos)
# ---------------------------------------------------------------------------

def ensure_gitignore_projects():
    """Ensure root .gitignore contains a rule for projects/ to prevent nested-repo commits."""
    root = utils.get_root_dir()
    gi_path = root / ".gitignore"
    entry = "projects/"
    if gi_path.exists():
        content = gi_path.read_text(encoding="utf-8")
        lines = [l.strip() for l in content.splitlines()]
        if entry in lines:
            return  # already present
        gi_path.write_text(content.rstrip() + "\n" + entry + "\n", encoding="utf-8")
    else:
        gi_path.write_text(entry + "\n", encoding="utf-8")
    print(f"[git] Added '{entry}' to root .gitignore")


def ensure_project_git(project_dir: Path):
    """Initialize a git repo inside the project folder if not already present (idempotent)."""
    git_dir = project_dir / ".git"
    if git_dir.exists():
        return  # already initialized
    result = subprocess.run(
        ["git", "init", str(project_dir)],
        capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode == 0:
        print(f"[git] Initialized project repo at {project_dir}")
    else:
        print(f"[git] WARNING: git init failed: {result.stderr.strip()}")
    # Write a project-level .gitignore template
    proj_gi = project_dir / ".gitignore"
    if not proj_gi.exists():
        proj_gi.write_text("*.aux\n*.log\n*.toc\n*.out\n*.synctex.gz\n", encoding="utf-8")


def load_registry() -> dict:
    """Load the project registry JSON. Returns empty dict if not found."""
    reg_path = utils.get_registry_path()
    if reg_path.exists():
        try:
            return json.loads(reg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def update_registry(project_name: str, metadata: dict):
    """Atomically update registry.json with project metadata."""
    registry = load_registry()
    registry[project_name] = metadata
    utils.save_registry(registry, utils.get_registry_path())


# ---------------------------------------------------------------------------
# Helpers: state management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Load pipeline state from the active project's state.json, creating defaults if missing."""
    state_path = utils.get_state_path()
    if state_path.exists():
        with open(state_path, encoding="utf-8") as f:
            return json.load(f)
    return default_state()


def default_state() -> dict:
    return {
        "phase": "foundation",
        "current_focus": "planning",
        "iteration": 0,
        "foundation_score": 0.0,
        "lore_score": 0.0,
        "chapters_drafted": 0,
        "chapters_total": CHAPTERS_TOTAL,
        "novel_score": 0.0,
        "revision_cycle": 0,
        "debts": [],
    }


def save_state(state: dict):
    """Write state to the active project's state.json."""
    state_path = utils.get_state_path()
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Helpers: logging
# ---------------------------------------------------------------------------

def log_result(commit: str, phase: str, score, word_count: int,
               status: str, description: str):
    """Append a row to results.tsv in the active project directory."""
    results_file = utils.get_results_path()
    header = "commit\tphase\tscore\tword_count\tstatus\tdescription\n"
    if not results_file.exists():
        results_file.write_text(header, encoding="utf-8")
    elif results_file.stat().st_size == 0:
        results_file.write_text(header, encoding="utf-8")
    with open(results_file, "a", encoding="utf-8") as f:
        f.write(f"{commit}\t{phase}\t{score}\t{word_count}\t{status}\t{description}\n")


def banner(text: str, char: str = "=", width: int = 60):
    """Print a visible phase/step banner."""
    print(f"\n{char * width}")
    print(f"  {text}")
    print(f"{char * width}")


def step(text: str):
    """Print a step indicator."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] {text}")


# ---------------------------------------------------------------------------
# Helpers: subprocess execution
# ---------------------------------------------------------------------------

def run_tool(cmd: str, timeout: int = 600, check: bool = False, cwd: str = None) -> subprocess.CompletedProcess:
    """
    Run a tool as a subprocess, capturing output.
    Uses shell=False with shlex.split for argument safety.
    Returns CompletedProcess; never raises unless check=True.
    """
    step(f"RUN: {cmd}")
    try:
        cmd_norm = cmd.replace("\\", "/")
        effective_cwd = cwd if cwd is not None else str(utils.get_root_dir())
        result = subprocess.run(
            shlex.split(cmd_norm), shell=False, capture_output=True, text=True,
            encoding="utf-8", timeout=timeout, cwd=effective_cwd,
        )
        if result.returncode != 0:
            print(f"    WARN: exit code {result.returncode}")
            stderr_preview = (result.stderr or "")[:2000]
            if stderr_preview:
                print(f"    stderr: {stderr_preview}")
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, result.stdout, result.stderr)
        return result
    except subprocess.TimeoutExpired:
        print(f"    ERROR: timed out after {timeout}s")
        # Return a fake CompletedProcess for graceful handling
        fake = subprocess.CompletedProcess(cmd, returncode=-1, stdout="", stderr="TIMEOUT")
        return fake


def uv_run(script: str, timeout: int = 600) -> subprocess.CompletedProcess:
    """Shorthand for 'uv run python <script>' from project root. Fails fast."""
    return run_tool(f"uv run \"{sys.executable}\" {script}", timeout=timeout, check=True)


# ---------------------------------------------------------------------------
# Helpers: git operations
# ---------------------------------------------------------------------------

def git_add_commit(message: str) -> str:
    """Stage all changes and commit. Returns short hash or empty string."""
    project_dir = utils.get_project_dir()
    run_tool("git add -A", cwd=str(project_dir))
    status_result = run_tool("git status --porcelain", cwd=str(project_dir))
    if status_result.stdout.strip():
        result = run_tool(f'git commit -m "{message}"', cwd=str(project_dir))
        if result.returncode == 0:
            hash_result = run_tool("git rev-parse --short HEAD", cwd=str(project_dir))
            commit_hash = hash_result.stdout.strip()
            step(f"GIT COMMIT: {commit_hash} — {message}")
            return commit_hash
    step("GIT: nothing to commit or commit failed")
    return ""


def git_reset_hard(ref: str = "HEAD~1"):
    """Hard reset to discard bad changes."""
    step(f"GIT RESET: {ref}")
    run_tool(f"git reset --hard {ref}", cwd=str(utils.get_project_dir()))


def git_short_hash() -> str:
    """Get current HEAD short hash."""
    r = run_tool("git rev-parse --short HEAD", cwd=str(utils.get_project_dir()))
    return r.stdout.strip() if r.returncode == 0 else "unknown"


# ---------------------------------------------------------------------------
# Helpers: score parsing
# ---------------------------------------------------------------------------

def parse_score(stdout: str, key: str = "overall_score") -> float:
    """
    Parse a score from evaluate.py YAML-like stdout output.
    Looks for lines like 'overall_score: 8.0' or 'novel_score: 7.5'.
    """
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith(f"{key}:"):
            val = line.split(":", 1)[1].strip()
            try:
                return float(val)
            except ValueError:
                continue
    return -1.0


def parse_lore_score(stdout: str) -> float:
    """Parse lore_score from foundation evaluation output."""
    return parse_score(stdout, "lore_score")


def count_words_in_chapters() -> int:
    """Sum word count across all chapter files in the active project."""
    total = 0
    chapters_dir = utils.get_chapters_dir()
    if chapters_dir.exists():
        for f in chapters_dir.glob("ch_*.md"):
            total += len(f.read_text(encoding="utf-8").split())
    return total


def count_chapter_files() -> int:
    """Count the number of chapter files in the active project."""
    chapters_dir = utils.get_chapters_dir()
    if not chapters_dir.exists():
        return 0
    return len(list(chapters_dir.glob("ch_*.md")))


def get_total_chapters(state: dict) -> int:
    """Determine total chapter count from state or outline."""
    if state.get("chapters_total", 0) > 0:
        return state["chapters_total"]
    # Try to infer from outline.md
    outline = utils.get_outline_path()
    if outline.exists():
        text = outline.read_text(encoding="utf-8")
        matches = re.findall(r'###\s*Ch(?:apter)?\s*(\d+)', text)
        if matches:
            return max(int(m) for m in matches)
    return CHAPTERS_TOTAL


# ---------------------------------------------------------------------------
# Dynamic seed processor
# ---------------------------------------------------------------------------

def process_notes(notes_input, genre):
    """Process user notes into seed.txt and return the string for gen_genre_framework.

    Resolves file-or-string input, then branches on word count:
      Short (<300w):     LLM expand → seed.txt gets expansion, returns original
      Goldilocks (300-1500w):        seed.txt gets notes, returns original
      Massive (>1500w):  LLM summarize → seed.txt gets full doc, returns summary

    Returns None if no notes_input provided.
    """
    if not notes_input:
        return None

    notes_path = Path(notes_input)
    if notes_path.exists():
        notes = notes_path.read_text(encoding="utf-8")
        step(f"Read notes from file: {notes_input}")
    else:
        notes = str(notes_input)

    word_count = len(notes.split())
    genre_str = genre or "the specified genre"

    banner(f"PROCESSING NOTES ({word_count} words)", "-")

    # seed.txt lives in the project directory
    seed_file = utils.get_seed_path()

    if word_count < 300:
        step(f"Notes too short ({word_count}w). Expanding to ~500 words via LLM...")
        expanded = call_anthropic(
            prompt=(
                f"The user has provided a very brief premise for a {genre_str} novel:\n\n"
                f"'{notes}'\n\n"
                f"Expand this into a dense, rich 500-word story document. "
                f"Establish a compelling core conflict, hint at the worldbuilding/setting, "
                f"and outline the protagonist's main flaw and goal. "
                f"Make it highly specific and creative."
            ),
            model_key="writer",
            max_tokens=2000,
            temperature=0.8,
            timeout=120,
        )
        seed_file.write_text(expanded, encoding="utf-8")
        step(f"seed.txt written ({len(expanded.split())}w, expanded from {word_count})")
        return notes

    if word_count <= 1500:
        step(f"Notes are a good size ({word_count}w). Writing directly to seed.txt.")
        seed_file.write_text(notes, encoding="utf-8")
        return notes

    step(f"Notes are very long ({word_count}w). Summarizing to ~500 words for genre framework...")
    summary = call_anthropic(
        prompt=(
            f"The user has provided a massive document ({word_count} words) for a {genre_str} novel. "
            f"Extract a dense 500-word summary of the core premise, genre, main characters, "
            f"and central conflict. Do not write a story, just extract the core DNA."
        ),
        model_key="writer",
        max_tokens=2000,
        temperature=0.3,
        timeout=120,
    )
    seed_file.write_text(notes, encoding="utf-8")
    step(f"seed.txt written with full {word_count}w doc. Summary ({len(summary.split())}w) sent to genre framework.")
    return summary


# ---------------------------------------------------------------------------
# PHASE 1 — FOUNDATION
# ---------------------------------------------------------------------------

def run_foundation(state: dict) -> dict:
    """
    Build planning documents (world, characters, outline, voice, canon).
    Loop until foundation_score > threshold or max iterations reached.
    """
    banner("PHASE 1: FOUNDATION", "=")

    best_score = state.get("foundation_score", 0.0)
    iteration = state.get("iteration", 0)

    for i in range(iteration + 1, MAX_FOUNDATION_ITERS + 1):
        banner(f"Foundation Iteration {i}", "-")
        state["iteration"] = i

        # 1. Generate planning documents
        step("Generating world bible...")
        uv_run("gen_world.py", timeout=600)

        step("Generating characters...")
        uv_run("gen_characters.py", timeout=600)

        step("Generating outline (part 1)...")
        uv_run("gen_outline.py", timeout=900)

        step("Generating outline (part 2 — foreshadowing)...")
        uv_run("gen_outline_part2.py", timeout=600)

        step("Generating canon...")
        uv_run("gen_canon.py", timeout=600)

        step("Running voice fingerprint...")
        uv_run("voice_fingerprint.py", timeout=600)

        # 2. Evaluate
        step("Evaluating foundation...")
        eval_result = uv_run("evaluate.py --phase=foundation", timeout=300)
        score = parse_score(eval_result.stdout, "overall_score")
        lore = parse_lore_score(eval_result.stdout)

        step(f"Foundation score: {score}  (lore: {lore}, prev best: {best_score})")

        # 3. Keep or discard
        if score >= best_score:
            commit_hash = git_add_commit(
                f"foundation iter {i}: score {score} (lore {lore})")
            log_result(commit_hash, "foundation", score, 0, "keep",
                       f"Iteration {i}: score improved {best_score} -> {score}")
            best_score = score
            state["foundation_score"] = score
            state["lore_score"] = lore
            save_state(state)
        else:
            step(f"Score did not improve ({score} <= {best_score}), discarding")
            git_reset_hard("HEAD")
            log_result("discarded", "foundation", score, 0, "discard",
                       f"Iteration {i}: no improvement ({score} <= {best_score})")

        # 4. Check exit condition
        if best_score >= FOUNDATION_THRESHOLD:
            step(f"Foundation score {best_score} >= {FOUNDATION_THRESHOLD} — PASSED")
            break
    else:
        step(f"WARNING: max iterations ({MAX_FOUNDATION_ITERS}) reached "
             f"with score {best_score}")

    # Determine total chapters from state (preset by genre config in run_pipeline)
    total = state.get("chapters_total", CHAPTERS_TOTAL)
    state["chapters_total"] = total
    state["phase"] = "drafting"
    state["current_focus"] = "chapter_drafting"
    save_state(state)

    banner(f"FOUNDATION COMPLETE — score {best_score}, {total} chapters planned")
    return state


# ---------------------------------------------------------------------------
# PHASE 2 — DRAFTING
# ---------------------------------------------------------------------------

def run_drafting(state: dict) -> dict:
    """
    Draft each chapter sequentially, evaluating and retrying as needed.
    """
    banner("PHASE 2: DRAFTING", "=")

    total = get_total_chapters(state)
    start_chapter = state.get("chapters_drafted", 0) + 1

    chapters_dir = utils.get_chapters_dir()  # also creates the directory

    for ch in range(start_chapter, total + 1):
        banner(f"Drafting Chapter {ch}/{total}", "-")
        drafted = False

        for attempt in range(1, MAX_CHAPTER_ATTEMPTS + 1):
            step(f"Attempt {attempt}/{MAX_CHAPTER_ATTEMPTS}")

            # Draft
            draft_result = uv_run(f"draft_chapter.py {ch}", timeout=600)
            if draft_result.returncode != 0:
                step(f"Draft failed (exit {draft_result.returncode}), retrying...")
                continue

            # Check the chapter file exists and has content
            ch_file = chapters_dir / f"ch_{ch:02d}.md"
            if not ch_file.exists() or ch_file.stat().st_size < 100:
                step("Chapter file missing or too short, retrying...")
                continue

            word_count = len(ch_file.read_text(encoding="utf-8").split())
            step(f"Drafted {word_count} words")

            # Evaluate
            eval_result = uv_run(f"evaluate.py --chapter={ch}", timeout=300)
            score = parse_score(eval_result.stdout, "overall_score")
            step(f"Chapter {ch} score: {score}")

            if score >= CHAPTER_THRESHOLD:
                commit_hash = git_add_commit(
                    f"ch{ch:02d}: score {score}, {word_count}w")
                log_result(commit_hash, f"ch{ch:02d}", score, word_count,
                           "keep", f"Chapter {ch} (attempt {attempt})")
                state["chapters_drafted"] = ch
                save_state(state)
                drafted = True
                break
            else:
                step(f"Score {score} < {CHAPTER_THRESHOLD}, discarding attempt")
                log_result("discarded", f"ch{ch:02d}", score, word_count,
                           "discard", f"Chapter {ch} attempt {attempt}")
                # Remove the bad chapter file so next attempt starts fresh
                if ch_file.exists():
                    run_tool(f"git checkout -- chapters/ch_{ch:02d}.md", cwd=str(utils.get_project_dir()))

        if not drafted:
            step(f"WARNING: Chapter {ch} failed all {MAX_CHAPTER_ATTEMPTS} attempts, "
                 f"keeping last attempt and moving on")
            # Keep whatever we have and commit it
            ch_file = chapters_dir / f"ch_{ch:02d}.md"
            if ch_file.exists():
                word_count = len(ch_file.read_text(encoding="utf-8").split())
                commit_hash = git_add_commit(
                    f"ch{ch:02d}: best-effort after {MAX_CHAPTER_ATTEMPTS} attempts")
                log_result(commit_hash, f"ch{ch:02d}", "?", word_count,
                           "forced", f"Chapter {ch}: kept after max attempts")
                state["chapters_drafted"] = ch
                save_state(state)

    # All chapters drafted
    state["phase"] = "revision"
    state["current_focus"] = "full_novel"
    state["chapters_drafted"] = total
    state["revision_cycle"] = 0
    save_state(state)

    total_words = count_words_in_chapters()
    banner(f"DRAFTING COMPLETE — {total} chapters, {total_words} words")
    return state


# ---------------------------------------------------------------------------
# PHASE 3 — REVISION
# ---------------------------------------------------------------------------

def parse_panel_consensus(panel_path: Path) -> list[dict]:
    """
    Parse reader_panel.json to find chapters with consensus issues.
    Returns list of dicts: {chapter, question, flagged_by, details}
    sorted by number of readers who flagged (descending).
    """
    if not panel_path.exists():
        return []
    with open(panel_path) as f:
        data = json.load(f)

    items = []

    # Look at disagreements — these are flagged by some but not all readers
    for d in data.get("disagreements", []):
        items.append({
            "chapter": d.get("chapter", 0),
            "question": d.get("question", ""),
            "flagged_by": d.get("flagged_by", []),
            "count": len(d.get("flagged_by", [])),
        })

    # Also scan readers for direct chapter mentions in key questions
    readers = data.get("readers", {})
    chapter_mentions = {}  # ch_num -> count of readers mentioning it

    for reader_key, answers in readers.items():
        for question in ["momentum_loss", "cut_candidate", "worst_scene",
                         "thinnest_character", "missing_scene"]:
            answer = answers.get(question, "")
            if not isinstance(answer, str):
                continue
            chs = re.findall(r'Ch(?:apter)?\s*(\d+)', answer, re.IGNORECASE)
            for ch_str in chs:
                ch_num = int(ch_str)
                key = (ch_num, question)
                if key not in chapter_mentions:
                    chapter_mentions[key] = {"chapter": ch_num, "question": question,
                                             "flagged_by": [], "count": 0}
                chapter_mentions[key]["flagged_by"].append(reader_key)
                chapter_mentions[key]["count"] += 1

    # Merge and deduplicate
    seen = set()
    for item in items:
        seen.add((item["chapter"], item["question"]))
    for key, item in chapter_mentions.items():
        if key not in seen:
            items.append(item)

    # Sort by count descending, take unique chapters
    items.sort(key=lambda x: -x["count"])

    # Deduplicate by chapter (keep highest-count issue per chapter)
    seen_chapters = set()
    unique = []
    for item in items:
        if item["chapter"] not in seen_chapters and item["chapter"] > 0:
            seen_chapters.add(item["chapter"])
            unique.append(item)

    return unique[:5]  # top 3-5 consensus items


def run_revision(state: dict, max_cycles: int = MAX_REVISION_CYCLES) -> dict:
    """
    Revision phase: adversarial editing, reader panel, targeted revisions.
    """
    banner("PHASE 3: REVISION", "=")

    briefs_dir = utils.get_briefs_dir()        # also creates the directory
    edit_logs_dir = utils.get_edit_logs_dir()  # also creates the directory

    prev_score = state.get("novel_score", 0.0)
    start_cycle = state.get("revision_cycle", 0) + 1
    max_cycles = min(max_cycles, MAX_REVISION_CYCLES)

    for cycle in range(start_cycle, max_cycles + 1):
        banner(f"Revision Cycle {cycle}/{max_cycles}", "-")

        # -- Step 1: Adversarial editing pass (parallel per chapter) --
        step("Running adversarial editing on all chapters...")
        total_ch = get_total_chapters(state)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(uv_run, f"adversarial_edit.py {ch}", 300): ch
                for ch in range(1, total_ch + 1)
            }
            for future in as_completed(futures):
                ch = futures[future]
                try:
                    future.result()
                    step(f"  ch {ch}: done")
                except Exception:
                    step(f"  ch {ch}: edit failed, continuing anyway")

        # -- Step 2: Apply mechanical cuts (only if apply_cuts.py exists) --
        apply_cuts = utils.get_root_dir() / "apply_cuts.py"
        if apply_cuts.exists():
            step("Applying mechanical cuts (OVER-EXPLAIN, REDUNDANT)...")
            run_tool("uv run python apply_cuts.py all "
                     "--types OVER-EXPLAIN REDUNDANT --min-fat 15", timeout=300)
        else:
            step("apply_cuts.py not found, skipping mechanical cuts")

        # -- Step 3: Generate arc summary + Reader panel --
        step("Generating arc summary for reader panel...")
        uv_run("build_arc_summary.py", timeout=300)
        step("Running reader panel evaluation...")
        uv_run("reader_panel.py", timeout=600)

        # -- Step 4: Parse panel consensus --
        panel_path = edit_logs_dir / "reader_panel.json"
        consensus_items = parse_panel_consensus(panel_path)

        if consensus_items:
            step(f"Found {len(consensus_items)} consensus items:")
            for item in consensus_items:
                print(f"    Ch {item['chapter']}: {item['question']} "
                      f"(flagged by {item['count']} readers)")
        else:
            step("No strong consensus items found from panel")

        # -- Step 5: Targeted revisions for consensus items --
        for idx, item in enumerate(consensus_items):
            ch_num = item["chapter"]
            question = item["question"]
            banner(f"  Revising Ch {ch_num} ({question}) [{idx+1}/{len(consensus_items)}]", ".")

            # Snapshot the current chapter score for comparison
            pre_eval = uv_run(f"evaluate.py --chapter={ch_num}", timeout=300)
            pre_score = parse_score(pre_eval.stdout, "overall_score")

            # Generate revision brief
            brief_file = briefs_dir / f"ch{ch_num:02d}_cycle{cycle}_{question}.md"
            gen_brief = utils.get_root_dir() / "gen_brief.py"
            if gen_brief.exists():
                step(f"Generating brief for Ch {ch_num}...")
                run_tool(f"uv run python gen_brief.py --panel {ch_num}", timeout=300)
                # gen_brief.py may write to briefs/ — find the most recent brief
                brief_candidates = sorted(
                    briefs_dir.glob(f"ch{ch_num:02d}*.md"),
                    key=lambda p: p.stat().st_mtime, reverse=True)
                if brief_candidates:
                    brief_file = brief_candidates[0]
            else:
                # Create a minimal brief from the panel data
                step(f"gen_brief.py not found, creating minimal brief for Ch {ch_num}...")
                brief_content = (
                    f"# Revision Brief: Chapter {ch_num}\n\n"
                    f"## Issue: {question}\n\n"
                    f"Panel consensus identified this chapter for revision.\n"
                    f"Focus: address the {question.replace('_', ' ')} issue.\n"
                    f"Preserve existing voice, character work, and essential beats.\n"
                )
                brief_file.write_text(brief_content)

            if not brief_file.exists():
                step(f"No brief file found for Ch {ch_num}, skipping")
                continue

            # Run revision
            step(f"Revising Ch {ch_num} with brief {brief_file.name}...")
            uv_run(f"gen_revision.py {ch_num} {brief_file}", timeout=600)

            # Evaluate revised chapter
            post_eval = uv_run(f"evaluate.py --chapter={ch_num}", timeout=300)
            post_score = parse_score(post_eval.stdout, "overall_score")

            ch_file = utils.get_chapters_dir() / f"ch_{ch_num:02d}.md"
            word_count = len(ch_file.read_text(encoding="utf-8").split()) if ch_file.exists() else 0

            step(f"Ch {ch_num}: {pre_score} -> {post_score}")

            if post_score >= pre_score:
                commit_hash = git_add_commit(
                    f"revision cycle {cycle}: ch{ch_num:02d} "
                    f"{question} {pre_score}->{post_score}")
                log_result(commit_hash, f"rev-ch{ch_num:02d}", post_score,
                           word_count, "keep",
                           f"Cycle {cycle}: {question} improved {pre_score}->{post_score}")
            else:
                step(f"Revision made it worse ({post_score} < {pre_score}), reverting")
                git_reset_hard("HEAD")
                log_result("reverted", f"rev-ch{ch_num:02d}", post_score,
                           word_count, "discard",
                           f"Cycle {cycle}: {question} regressed {pre_score}->{post_score}")

        # -- Step 6: Full novel evaluation --
        step("Running full novel evaluation...")
        full_eval = uv_run("evaluate.py --full", timeout=600)
        novel_score = parse_score(full_eval.stdout, "novel_score")

        if novel_score < 0:
            # Fallback: try overall_score
            novel_score = parse_score(full_eval.stdout, "overall_score")

        total_words = count_words_in_chapters()
        step(f"Novel score: {novel_score}  (prev: {prev_score}, words: {total_words})")

        # Commit cycle results
        commit_hash = git_add_commit(
            f"revision cycle {cycle} complete: novel_score {novel_score}")
        log_result(commit_hash, f"revision-cycle-{cycle}", novel_score,
                   total_words, "cycle",
                   f"Cycle {cycle}: novel_score {prev_score}->{novel_score}")

        state["novel_score"] = novel_score
        state["revision_cycle"] = cycle
        save_state(state)

        # -- Step 7: Plateau detection --
        if cycle >= MIN_REVISION_CYCLES and abs(novel_score - prev_score) < PLATEAU_DELTA:
            step(f"Plateau detected (delta {abs(novel_score - prev_score):.2f} "
                 f"< {PLATEAU_DELTA}) after {cycle} cycles — stopping")
            break

        prev_score = novel_score

    # =========================================================
    # PHASE 3b: OPUS REVIEW LOOP (deep, prose-level refinement)
    # =========================================================
    review_py = utils.get_root_dir() / "review.py"
    if review_py.exists():
        banner("PHASE 3b: OPUS REVIEW LOOP", "=")
        
        max_review_rounds = 4
        for rnd in range(1, max_review_rounds + 1):
            banner(f"Opus Review Round {rnd}/{max_review_rounds}", "-")
            
            # Step 1: Generate the review
            step("Sending manuscript to Opus for review...")
            review_result = uv_run(
                f"review.py --output {utils.get_reviews_path()}", timeout=900)
            
            # Step 2: Parse the review
            step("Parsing review...")
            parse_result = run_tool(
                "uv run python review.py --parse", timeout=60)
            print(parse_result.stdout if parse_result else "")
            
            # Step 3: Check stopping condition
            review_logs = sorted(
                utils.get_edit_logs_dir().glob("*_review.json"), reverse=True)
            if review_logs:

                review_data = json.loads(review_logs[0].read_text(encoding="utf-8"))
                stars = review_data.get("stars", 0) or 0
                total_items = review_data.get("total_items", 0)
                major_items = review_data.get("major_items", 0)
                qualified = review_data.get("qualified_items", 0)
                
                step(f"Stars: {stars}, Items: {total_items} "
                     f"({major_items} major, {qualified} qualified)")
                
                # Stop if: ≥4★, no major unqualified items, or >half qualified
                if stars >= 4.5 and major_items == 0:
                    step("★★★★½ with no major items — novel is ready.")
                    break
                if stars >= 4 and total_items > 0 and qualified / total_items > 0.5:
                    step(f"★{'★' * int(stars)} with majority qualified items — novel is ready.")
                    break
            
            # Step 4: Generate briefs from review items and fix
            step("Generating revision briefs from review...")
            gen_brief_py = utils.get_root_dir() / "gen_brief.py"
            if gen_brief_py.exists():
                # Auto mode: picks weakest chapter, cross-references all sources
                run_tool("uv run python gen_brief.py --auto", timeout=300)
                
                # Find any generated briefs and apply the top one
                recent_briefs = sorted(
                    utils.get_briefs_dir().glob("*_auto.md"),
                    key=lambda p: p.stat().st_mtime, reverse=True)
                if recent_briefs:
                    brief = recent_briefs[0]
                    # Extract chapter number from filename
                    ch_match = re.search(r'ch(\d+)', brief.name)
                    if ch_match:
                        ch_num = int(ch_match.group(1))
                        step(f"Revising Ch {ch_num} from review brief...")
                        uv_run(f"gen_revision.py {ch_num} {brief}", timeout=600)
                        git_add_commit(
                            f"review round {rnd}: revise ch{ch_num:02d} from Opus feedback")
            
            # Step 5: Mechanical fixes from review
            # Run slop pass on any mentioned patterns
            step("Running mechanical cleanup pass...")
            apply_cuts_py = utils.get_root_dir() / "apply_cuts.py"
            if apply_cuts_py.exists():
                run_tool(
                    "uv run python apply_cuts.py all --types OVER-EXPLAIN REDUNDANT --min-fat 15",
                    timeout=300)
                git_add_commit(f"review round {rnd}: mechanical cleanup")
            
            step(f"Review round {rnd} complete.")
        
        banner("OPUS REVIEW LOOP COMPLETE")
    
    state["phase"] = "export"
    state["current_focus"] = "export"
    save_state(state)

    banner(f"REVISION COMPLETE — {state.get('revision_cycle', 0)} cycles, "
           f"novel_score {state.get('novel_score', 0)}")
    return state


# ---------------------------------------------------------------------------
# PHASE 4 — EXPORT
# ---------------------------------------------------------------------------

def run_export(state: dict) -> dict:
    """
    Build final deliverables: outline, arc summary, manuscript, PDF.
    """
    banner("PHASE 4: EXPORT", "=")

    root_dir = utils.get_root_dir()
    chapters_dir = utils.get_chapters_dir()
    typeset_dir = utils.get_typeset_dir()

    # 1. Rebuild outline from chapters
    build_outline = root_dir / "build_outline.py"
    if build_outline.exists():
        step("Rebuilding outline from chapters...")
        uv_run("build_outline.py", timeout=300)

    # 2. Build arc summary
    build_arc = root_dir / "build_arc_summary.py"
    if build_arc.exists():
        step("Building arc summary...")
        uv_run("build_arc_summary.py", timeout=300)

    # 3. Concatenate chapters into manuscript.md (written into project dir)
    step("Building manuscript.md...")
    manuscript = utils.get_manuscript_path()
    chapter_files = sorted(chapters_dir.glob("ch_*.md"))

    parts = []
    for ch_file in chapter_files:
        text = ch_file.read_text(encoding="utf-8").strip()
        if text:
            parts.append(text)

    if parts:
        manuscript.write_text("\n\n---\n\n".join(parts) + "\n", encoding="utf-8")
        word_count = sum(len(p.split()) for p in parts)
        step(f"Manuscript: {len(parts)} chapters, {word_count} words")
    else:
        step("WARNING: no chapter files found for manuscript")

    # 4. Build LaTeX
    build_tex = root_dir / "typeset" / "build_tex.py"
    if build_tex.exists():
        step("Building LaTeX content...")
        # Run with cwd set to project typeset dir so aux files stay isolated
        run_tool(f"uv run python {build_tex}", timeout=120, cwd=str(utils.get_typeset_dir()))

        # 5. Typeset with tectonic (if available)
        novel_tex = typeset_dir / "novel.tex"
        if novel_tex.exists():
            import shutil
            if shutil.which("tectonic"):
                step("Typesetting PDF with tectonic...")
                result = run_tool(f"tectonic {novel_tex.name}", timeout=300, cwd=str(utils.get_typeset_dir()))
                if result.returncode == 0:
                    step(f"PDF generated: {typeset_dir / 'novel.pdf'}")
                else:
                    step("WARNING: tectonic typesetting failed")
            else:
                step("tectonic not found, skipping PDF generation")
    else:
        step("typeset/build_tex.py not found, skipping LaTeX")

    # 6. Final commit
    commit_hash = git_add_commit("export: manuscript, outline, arc summary, PDF")
    total_words = count_words_in_chapters()
    log_result(commit_hash, "export", state.get("novel_score", "?"),
               total_words, "export", "Final export")

    state["phase"] = "complete"
    state["current_focus"] = "done"
    save_state(state)

    banner(f"EXPORT COMPLETE — {len(chapter_files)} chapters, {total_words} words")
    return state


# ---------------------------------------------------------------------------
# Sanity check (pre-flight before any LLM call)
# ---------------------------------------------------------------------------

def sanity_check(args):
    """Run pre-flight checks. Exit 1 on critical failures."""
    ok = True
    notes_provided = bool(args.notes)
    root_dir = utils.get_root_dir()

    # 1. .env exists
    if not (root_dir / ".env").exists():
        print("FAIL: .env not found — create one from .env.example", file=sys.stderr)
        ok = False

    # 2. API key loaded (load_dotenv already called at module level)
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("FAIL: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        ok = False

    # 3. API endpoint reachable
    base = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    try:
        httpx.get(base, timeout=5)
    except Exception:
        print(f"WARN: {base} unreachable — continuing anyway", file=sys.stderr)

    # 4. At least one of seed.txt or --notes exists
    if not (root_dir / "seed.txt").exists() and not utils.get_seed_path().exists() and not notes_provided:
        print("FAIL: provide --notes or place a seed.txt in the project root or project folder", file=sys.stderr)
        ok = False

    # 5. Genre is specified (skip if already configured from a previous run)
    if not args.genre and not os.getenv("AUTONOVEL_GENRE"):
        if not utils.get_active_genre_path().exists() and not (root_dir / "active_genre.json").exists():
            print("FAIL: provide --genre or set AUTONOVEL_GENRE in .env", file=sys.stderr)
            ok = False

    # --- Warnings (non-fatal) ---

    # Chapters parseable
    if args.chapters:
        try:
            int(args.chapters)
        except ValueError:
            descriptive = {"short", "story", "novella", "novelette", "epic", "saga"}
            if not any(w in args.chapters.lower() for w in descriptive):
                print(f"WARN: --chapters '{args.chapters}' looks unusual", file=sys.stderr)

    # active_genre.json valid if present
    active_path = utils.get_active_genre_path()
    if not active_path.exists():
        active_path = root_dir / "active_genre.json"
    if active_path.exists():
        try:
            json.loads(active_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"WARN: {active_path.name} is corrupted — delete it and re-run", file=sys.stderr)

    # state.json valid if present and not in --from-scratch mode
    state_path = utils.get_state_path()
    if state_path.exists() and not args.from_scratch:
        try:
            json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("WARN: state.json is corrupted — use --from-scratch to reset", file=sys.stderr)

    if not ok:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(args):
    """Run the full pipeline or a specific phase."""

    # Set active project FIRST so all path helpers resolve correctly
    utils.set_project_name(args.project)
    project_dir = utils.get_project_dir()
    project_dir.mkdir(parents=True, exist_ok=True)

    # Git Option B: guard root .gitignore and init project repo
    ensure_gitignore_projects()
    ensure_project_git(project_dir)

    sanity_check(args)

    root_dir = utils.get_root_dir()

    # Load or initialize state
    if args.from_scratch:
        banner("STARTING FROM SCRATCH")
        import shutil

        # Clean up existing files in the project directory to prevent cross-contamination
        if project_dir.exists():
            for name in ["chapters", "briefs", "edit_logs", "eval_logs", "typeset"]:
                p = project_dir / name
                if p.is_dir():
                    try:
                        shutil.rmtree(p)
                    except Exception as e:
                        print(f"WARN: Failed to clean directory {name}: {e}", file=sys.stderr)
            for name in ["world.md", "characters.md", "outline.md", "canon.md", "manuscript.md", "arc_summary.md", "results.tsv", "state.json", "active_genre.json", "seed.txt"]:
                p = project_dir / name
                if p.is_file():
                    try:
                        p.unlink()
                    except Exception as e:
                        print(f"WARN: Failed to remove file {name}: {e}", file=sys.stderr)

        # Initialize project-specific seed
        seed_dest = utils.get_seed_path()
        if not args.notes:
            if not seed_dest.exists():
                global_seed = root_dir / "seed.txt"
                if global_seed.exists():
                    print(f"\n[WARNING][CONTAMINATION RISK] No project-specific seed.txt found. Copying global seed.txt to {seed_dest}.\n", file=sys.stderr)
                    shutil.copy2(global_seed, seed_dest)
                else:
                    print("ERROR: No seed.txt found in project directory or repository root, and no --notes provided.", file=sys.stderr)
                    sys.exit(1)
        elif not utils.get_seed_path().exists() and not (root_dir / "seed.txt").exists():
            print("ERROR: No seed.txt found in project directory or repository root, and no --notes provided.", file=sys.stderr)
            sys.exit(1)

        state = default_state()
        # Write user-provided chapter count into state before banner
        if args.chapters:
            try:
                state["chapters_total"] = int(args.chapters)
            except ValueError:
                pass  # non-numeric string like "short story" — let genre framework resolve
        
        # Copy template voice.md file to project directory if it exists in root
        voice_template = root_dir / "voice.md"
        if voice_template.exists():
            shutil.copy2(voice_template, utils.get_voice_path())
                
        save_state(state)
    else:
        state = load_state()

    # Ensure directories exist (helpers create them)
    utils.get_chapters_dir()
    utils.get_briefs_dir()
    utils.get_edit_logs_dir()
    utils.get_eval_logs_dir()

    # Apply max_cycles override
    max_cycles = args.max_cycles if args.max_cycles else MAX_REVISION_CYCLES

    # Determine which phases to run
    if args.phase:
        # Single phase mode
        phases = [args.phase]
    else:
        # Run from current state onward
        current = state.get("phase", "foundation")
        if current == "complete":
            print("Pipeline already complete. Use --from-scratch to restart "
                  "or --phase to run a specific phase.")
            return
        try:
            start_idx = PHASE_ORDER.index(current)
        except ValueError:
            start_idx = 0
        phases = PHASE_ORDER[start_idx:]

    banner(f"AUTONOVEL PIPELINE — phases: {', '.join(phases)}")
    print(f"  State: phase={state.get('phase')}, "
          f"foundation_score={state.get('foundation_score', 0)}, "
          f"chapters={state.get('chapters_drafted', 0)}/{state.get('chapters_total', '?')}, "
          f"novel_score={state.get('novel_score', 0)}")

    start_time = datetime.now()

    for phase in phases:
        try:
            if phase == "foundation":
                global CHAPTERS_TOTAL

                # Step 0: Process user notes → auto-create seed.txt
                notes_for_genre = None
                if args.notes:
                    notes_for_genre = process_notes(args.notes, args.genre)
                seed_path = utils.get_seed_path()
                if not seed_path.exists():
                    print(f"ERROR: seed.txt not found at {seed_path}", file=sys.stderr)
                    sys.exit(1)
                # TODO: --continue mode — if pre-written chapters exist, generate
                # an outline that picks up from the last written beat instead of
                # starting from chapter 1.

                # Step 1: Initialize genre configuration
                active_genre_path = utils.get_active_genre_path()
                if (not active_genre_path.exists() or args.from_scratch or args.genre) and args.genre:
                    banner("STEP 1: Initializing genre configuration")
                    cmd = [sys.executable, str(root_dir / "gen_genre_framework.py")]
                    if args.genre:
                        cmd += ["--genre", args.genre]
                    if args.chapters:
                        cmd += ["--chapters", args.chapters]
                    if notes_for_genre:
                        cmd += ["--notes", notes_for_genre]
                    subprocess.run(cmd, check=True)
                    from genre import reload_genre
                    reload_genre()
                    print("Genre config ready.\n")

                # Load genre config for chapter count
                genre_cfg = load_genre()
                CHAPTERS_TOTAL = genre_cfg["generation"]["outline"]["estimated_chapters"]
                state["chapters_total"] = CHAPTERS_TOTAL

                state = run_foundation(state)
            elif phase == "drafting":
                state = run_drafting(state)
            elif phase == "revision":
                state = run_revision(state, max_cycles=max_cycles)
            elif phase == "export":
                state = run_export(state)
            else:
                print(f"Unknown phase: {phase}")
                sys.exit(1)
        except KeyboardInterrupt:
            banner("INTERRUPTED — state saved")
            save_state(state)
            sys.exit(130)
        except Exception as e:
            print(f"\n  FATAL ERROR in {phase}: {e}")
            save_state(state)
            raise

    elapsed = datetime.now() - start_time
    hours = elapsed.total_seconds() / 3600

    # Update project registry with final metadata
    update_registry(args.project, {
        "title": state.get("title", args.project),
        "genre": args.genre or os.getenv("AUTONOVEL_GENRE", "unknown"),
        "created_at": state.get("created_at", datetime.now().isoformat()),
        "last_modified": datetime.now().isoformat(),
        "phase": state.get("phase", "unknown"),
        "novel_score": state.get("novel_score", 0.0),
        "word_count": count_words_in_chapters(),
    })

    banner("PIPELINE COMPLETE")
    print(f"  Project:    {args.project}")
    print(f"  Time:       {hours:.1f} hours")
    print(f"  Phase:      {state.get('phase')}")
    print(f"  Foundation: {state.get('foundation_score', 0)}")
    print(f"  Chapters:   {state.get('chapters_drafted', 0)}/{state.get('chapters_total', '?')}")
    print(f"  Words:      {count_words_in_chapters()}")
    print(f"  Novel:      {state.get('novel_score', 0)}")
    print(f"  Cycles:     {state.get('revision_cycle', 0)}")


def main():
    parser = argparse.ArgumentParser(
        description="Autonovel pipeline orchestrator — seed to finished novel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python run_pipeline.py --project mynovel              # resume from current state
  python run_pipeline.py --project mynovel --from-scratch  # start fresh from seed.txt
  python run_pipeline.py --project mynovel --phase foundation  # run only foundation
  python run_pipeline.py --project mynovel --phase drafting    # run only drafting
  python run_pipeline.py --project mynovel --phase revision    # run only revision
  python run_pipeline.py --project mynovel --phase export      # run only export
  python run_pipeline.py --project mynovel --max-cycles 4      # limit revision to 4 cycles
""")

    parser.add_argument(
        "--project", default=os.environ.get("AUTONOVEL_PROJECT", "default"),
        help="Project name (creates isolated session in projects/<name>/)")
    parser.add_argument(
        "--from-scratch", action="store_true",
        help="Reset state and start from seed.txt")
    parser.add_argument(
        "--phase", choices=PHASE_ORDER,
        help="Run only a specific phase")
    parser.add_argument(
        "--max-cycles", type=int, default=None,
        help=f"Maximum revision cycles (default: {MAX_REVISION_CYCLES})")
    parser.add_argument("--genre", default=os.environ.get("AUTONOVEL_GENRE", ""),
                        help="Genre description (e.g., 'Cyberpunk Noir')")
    parser.add_argument("--chapters", default=os.environ.get("AUTONOVEL_CHAPTERS", "24"),
                        help="Number of chapters (or 'short story', 'novella', etc.)")
    parser.add_argument("--notes", default=os.environ.get("AUTONOVEL_NOTES", ""),
                        help="Story premise or file path (e.g., --notes my_ideas.txt). "
                             "Auto-expands if <300 words, auto-summarizes if >1500.")

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
