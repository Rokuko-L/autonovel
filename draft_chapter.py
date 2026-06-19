#!/usr/bin/env python3
"""
Draft a single chapter using the writer model.
Usage: python draft_chapter.py 1
"""
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
import utils
from utils import call_anthropic, get_novel_title
from genre import load_genre

load_dotenv()

def call_writer(prompt, max_tokens=16000):
    genre_cfg = load_genre()
    chapter_system = genre_cfg["identity"]["chapter_system"]
    estimated_words = genre_cfg["generation"]["outline"]["estimated_words"]
    chapter_count = genre_cfg["generation"]["outline"]["estimated_chapters"]
    target_words = estimated_words // chapter_count
    system_prompt = chapter_system + f"\n\nWRITING REQUIREMENT: This chapter must be approximately {target_words} words. Write fully and completely to hit this target."
    return call_anthropic(prompt=prompt, system=system_prompt, model_key="writer", max_tokens=max_tokens, beta_context=True, timeout=600, temperature=0.8)

def load_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""

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
    canon = load_file(utils.get_canon_path())
    
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

WRITING INSTRUCTIONS:
{load_genre()["generation"]["draft_chapter_instructions"]}

Write the chapter now. Full text, beginning to end.
"""

    print(f"Drafting Chapter {chapter_num}...", file=sys.stderr)
    result = call_writer(prompt)
    
    # Save
    out_path = chapters_dir / f"ch_{chapter_num:02d}.md"
    out_path.write_text(result, encoding="utf-8")
    print(f"Saved to {out_path}", file=sys.stderr)
    print(f"Word count: {len(result.split())}", file=sys.stderr)
    print(result)

if __name__ == "__main__":
    main()
