#!/usr/bin/env python3
"""
Build a condensed arc summary for full-novel evaluation.
For each chapter: first 150 words, last 150 words, plus any dialogue.
Gives the reader panel enough to evaluate the ARC without 72k tokens.
"""
import re
from pathlib import Path
from dotenv import load_dotenv
import utils
from utils import call_anthropic, get_novel_title
from genre import load_genre

load_dotenv()

def call_writer(prompt, max_tokens=4000):
    return call_anthropic(prompt=prompt, system="You summarize novel chapters precisely. State what HAPPENS, what CHANGES, and what QUESTIONS are left open. No evaluation. No praise. Just events and shifts.", model_key="writer", max_tokens=max_tokens, timeout=120, temperature=0.1)

def extract_key_passages(text):
    """Get opening, closing, and best dialogue from a chapter."""
    words = text.split()
    opening = ' '.join(words[:150])
    closing = ' '.join(words[-150:])
    
    # Extract dialogue lines
    dialogue = re.findall(r'["""]([^"""]{20,})["""]', text)
    # Pick up to 3 longest dialogue lines
    dialogue.sort(key=len, reverse=True)
    top_dialogue = dialogue[:3]
    
    return opening, closing, top_dialogue

def main():
    chapters_dir = utils.get_chapters_dir()
    chapter_files = sorted(chapters_dir.glob("ch_*.md"))
    if not chapter_files:
        print("No chapter files found!")
        return

    summaries = []
    
    for path in chapter_files:
        m = re.search(r"ch_(\d+)\.md", path.name)
        if not m:
            continue
        ch = int(m.group(1))
        
        text = path.read_text(encoding="utf-8")
        wc = len(text.split())
        opening, closing, dialogue = extract_key_passages(text)
        
        # Get a 100-word summary from the model
        summary = call_writer(
            f"Summarize this chapter in exactly 3 sentences. What happens, what changes, what question is left open.\n\nCHAPTER {ch}:\n{text}",
            max_tokens=200
        )
        
        entry = f"""### Chapter {ch} ({wc} words)
**Summary:** {summary}

**Opening:** {opening}...

**Closing:** ...{closing}

**Key dialogue:**
"""
        for d in dialogue:
            entry += f'> "{d}"\n\n'
        
        summaries.append(entry)
        print(f"Ch {ch}: summarized ({wc}w)")
    
    # Calculate total word count
    total_wc = sum(len(p.read_text(encoding="utf-8").split()) for p in chapter_files)
    num_chapters = len(chapter_files)
    
    # Assemble
    title = get_novel_title()
    full = f"""# {title.upper()}
## Full-Arc Summary for Reader Panel

This document contains chapter summaries, opening/closing passages,
and key dialogue for all {num_chapters} chapters. Total novel: {total_wc:,} words.

PREMISE: {load_genre()["generation"]["arc_summary_premise"]}

---

"""
    full += '\n---\n\n'.join(summaries)
    
    out_path = utils.get_arc_summary_path()
    out_path.write_text(full, encoding="utf-8")
    print(f"\nSaved to {out_path} ({len(full.split())} words)")

if __name__ == "__main__":
    main()
