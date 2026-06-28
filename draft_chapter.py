#!/usr/bin/env python3
"""
Draft a single chapter using the writer model.
Usage: python draft_chapter.py 1
"""
import json
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
import utils
from utils import call_anthropic, get_novel_title, parse_premise_beats, check_structural_repetition, TruncationError
from genre import load_genre

load_dotenv()

def call_writer(prompt, max_tokens=None):
    genre_cfg = load_genre()
    chapter_system = genre_cfg["identity"]["chapter_system"]
    estimated_words = genre_cfg["generation"]["outline"]["estimated_words"]
    chapter_count = genre_cfg["generation"]["outline"]["estimated_chapters"]
    target_words = estimated_words // chapter_count
    # Cap output tokens at ~3.25x target word count to prevent runaway generation
    if max_tokens is None:
        max_tokens = int(target_words * 3.25)
    system_prompt = chapter_system + f"\n\nWRITING REQUIREMENT: This chapter must be approximately {target_words} words. Write fully, expansively, and completely to hit this target. Flesh out every scene with sensory details, full dialogues, and deep character interiority. Avoid summarizing events, skipping actions, or rushing through the narrative. Pacing should be slow, detailed, and immersive."
    return call_anthropic(prompt=prompt, system=system_prompt, model_key="writer", max_tokens=max_tokens, beta_context=True, timeout=600, temperature=0.8, raise_on_truncation=True)

def load_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def parse_canon(canon_text: str):
    """Split canon.md into Foundation, Core Canon, and recent As-of Chapter sections.

    Returns (foundation, core_canon, disclosure_ceiling):
      - foundation:     `## Foundation` section (background truth, always included)
      - core_canon:     `## Core Canon` section (permanent established facts, always included)
      - disclosure:     last 5 `## As of Chapter N` sections (incremental reveals, trimmed)
    """
    foundation = ""
    core_canon = ""
    as_of_sections = []
    current = ""
    current_header = ""
    for line in canon_text.splitlines(keepends=True):
        if line.startswith("## "):
            if current.strip() and current_header:
                if current_header.startswith("## Foundation"):
                    foundation = current
                elif current_header.startswith("## Core Canon"):
                    core_canon = current
                elif current_header.startswith("## As of Chapter"):
                    as_of_sections.append(current)
            current = ""
            current_header = line.strip()
        if current_header:
            current += line
    if current.strip() and current_header:
        if current_header.startswith("## Foundation"):
            foundation = current
        elif current_header.startswith("## Core Canon"):
            core_canon = current
        elif current_header.startswith("## As of Chapter"):
            as_of_sections.append(current)
    disclosure = "\n\n".join(as_of_sections[-5:]) if as_of_sections else ""
    return foundation, core_canon, disclosure

def extract_chapter_outline(outline_text, chapter_num):
    """Extract a specific chapter's outline entry."""
    pattern = rf'### Ch {chapter_num}:.*?(?=### Ch {chapter_num + 1}:|## Foreshadowing|$)'
    match = re.search(pattern, outline_text, re.DOTALL)
    return match.group(0).strip() if match else "(not found)"

def extract_next_chapter_outline(outline_text, chapter_num):
    """Extract the next chapter's outline (just first few lines for continuity)."""
    next_entry = extract_chapter_outline(outline_text, chapter_num + 1)
    if next_entry == "(not found)":
        return "(final chapter)"
    lines = next_entry.split('\n')[:10]
    return '\n'.join(lines)

def main():
    chapter_num = int(sys.argv[1])
    
    # Load all context
    voice = load_file(utils.get_voice_path())
    world = load_file(utils.get_world_path())
    characters = load_file(utils.get_characters_path())
    outline = load_file(utils.get_outline_path())
    canon_text = load_file(utils.get_canon_path())
    canon_foundation, canon_core, canon_disclosure = parse_canon(canon_text)
    
    # Chapter-specific context
    chapter_outline = extract_chapter_outline(outline, chapter_num)
    next_chapter = extract_next_chapter_outline(outline, chapter_num)
    
    # Previous chapter (if exists)
    chapters_dir = utils.get_chapters_dir()
    prev_path = chapters_dir / f"ch_{chapter_num - 1:02d}.md"
    if prev_path.exists():
        prev_text = prev_path.read_text(encoding="utf-8")
        prev_tail = prev_text[-2000:] if len(prev_text) > 2000 else prev_text
    else:
        prev_tail = "(first chapter -- no previous)"

    title = get_novel_title()

    # Build structural guardrails (applied to EVERY chapter)
    structural_guardrails = """
STRUCTURAL RULES (apply to every chapter):
- If a scene involves a list (multiple rules, observations, items), present them
  together in ONE consolidated scene. Do NOT repeat the surrounding scene-setting
  (checking a UI, looking at a calendar, etc.) for each sub-item.
- Each beat should introduce content that hasn't appeared in an earlier beat.
  Do not have the character re-discover, re-read, or re-react to the same object,
  document, or realization in more than one beat.
- The reader must be grounded at the start of this chapter. Every name, title,
  location, and relationship must be established through events — not assumed.
"""

    # Chapter 1 premise-beat guardrail — enumerate beats from the validated outline
    premise_guardrail = ""
    if chapter_num == 1:
        beats = parse_premise_beats(outline)
        if beats:
            beat_lines = "\n".join(
                f"  {i+1}. {b['beat']} — {b['scene_summary']}"
                for i, b in enumerate(beats)
            )
            premise_guardrail = f"""
CHAPTER 1 READER ORIENTATION:
Your outline for this chapter contains these required premise-establishment
beats, in order. You MUST draft prose for each beat before moving to the
chapter's main plot scenes. Each beat gets real scene treatment — do not
compress, skip, or summarize a beat in a single sentence.

PREMISE BEATS:
{beat_lines}

CRITICAL: These beat names (e.g. "ordinary_world", "observer_reveal") are
internal labels for your planning only. Do NOT print them, bold them,
reference them, or use them as section headers in the chapter output.
Write continuous prose with no section breaks between beats — the transition
between beats should be a natural prose transition, not a labeled divider.
"""
        # Check premise validation flag
        prem_val_path = utils.get_project_dir() / "premise_validation.json"
        if prem_val_path.exists():
            prem_val = json.loads(prem_val_path.read_text(encoding="utf-8"))
            if not prem_val.get("passed"):
                premise_guardrail += (
                    "\nNOTE: This chapter's outline did not pass automated premise-beat "
                    "validation. The beats listed above may be incomplete or out of order. "
                    "Weigh reader-grounding with extra scrutiny — ensure every concept is "
                    "properly introduced on the page.\n"
                )
    prompt = f"""Write Chapter {chapter_num} of "{title}."

VOICE DEFINITION (follow this exactly):
{voice}

THIS CHAPTER'S OUTLINE (hit every beat):
{chapter_outline}

NEXT CHAPTER'S OUTLINE (for continuity -- end this chapter so it flows into the next):
{next_chapter}

PREVIOUS CHAPTER'S ENDING (continue from here):
{prev_tail}

WORLD BIBLE (reference for worldbuilding details):
{world}

CHARACTER REGISTRY (reference for speech patterns and behavior):
{characters}
"""

    if canon_foundation:
        prompt += f"""
FOUNDATION CANON (private author truth — this shapes how characters think and act,
but is NOT something they or the narration may state as already established):
{canon_foundation}
"""

    if canon_core:
        prompt += f"""
CORE CANON (permanent established facts — relationships, world rules, secrets
that the reader already knows. Reference these naturally; do not re-introduce them):
{canon_core}
"""

    if canon_disclosure:
        prompt += f"""
DISCLOSURE CEILING (everything that has been put on the page so far. Anything not listed here,
including anything from the world/character bible, must be introduced through this chapter's
events — not assumed, not name-dropped):
{canon_disclosure}
"""

    prompt += f"""
WRITING INSTRUCTIONS:
{load_genre()["generation"]["draft_chapter_instructions"]}

{structural_guardrails}
{premise_guardrail}
Write the chapter now. Full text, beginning to end.
"""

    MAX_REP_ATTEMPTS = 2
    repetition_feedback = ""

    for attempt in range(1, MAX_REP_ATTEMPTS + 1):
        print(f"Drafting Chapter {chapter_num} (regen check {attempt}/{MAX_REP_ATTEMPTS})...", file=sys.stderr)
        try:
            result = call_writer(prompt + repetition_feedback)
        except TruncationError as e:
            print(f"TRUNCATION_DETECTED: {e}", file=sys.stderr)
            sys.exit(2)

        rep_regen, rep_feedback, rep_sidecar = check_structural_repetition(result)

        # Write sidecar
        rep_path = chapters_dir / "repetition_check.json"
        rep_path.write_text(json.dumps(rep_sidecar, indent=2), encoding="utf-8")

        if not rep_regen or attempt == MAX_REP_ATTEMPTS:
            break

        # Build targeted feedback for regen
        repetition_feedback = "\n\nREPETITION FIX REQUIRED:\n" + "\n".join(rep_feedback)
        print(f"  Structural repetition detected — retrying...", file=sys.stderr)

    # Save
    out_path = chapters_dir / f"ch_{chapter_num:02d}.md"
    out_path.write_text(result, encoding="utf-8")
    print(f"Saved to {out_path}", file=sys.stderr)
    print(f"Word count: {len(result.split())}", file=sys.stderr)
    print(result)

if __name__ == "__main__":
    main()
