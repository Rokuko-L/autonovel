#!/usr/bin/env python3
"""
Adversarial editing pass: ask the judge to CUT 500 words from each chapter.
What gets cut reveals what's weakest. The cut list IS the revision plan.

Usage: python adversarial_edit.py 1        # single chapter
       python adversarial_edit.py all      # all chapters
"""
import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv
import utils
from utils import extract_text_from_response, get_max_tokens_with_thinking, call_anthropic

load_dotenv()

def call_judge(prompt, max_tokens=8000):
    return call_anthropic(prompt=prompt, system="You are a ruthless literary editor. You cut fat from prose. You have no sentiment about good-enough sentences -- if a sentence isn't earning its place, it goes. You quote exactly from the text. You never invent or paraphrase. Always respond with valid JSON.", model_key="judge", max_tokens=max_tokens, temperature=0.3, timeout=300)

def parse_json(text):
    return utils.parse_json_response(text)

EDIT_PROMPT = """You are editing a fantasy novel chapter. Your job: identify exactly
what to cut or rewrite to make this chapter tighter, sharper, more alive.

THE CHAPTER ({word_count} words):
{chapter_text}

DISCLOSURE CEILING (everything established on the page through prior chapters):
{canon_context}

YOUR TASK:
1. Find 10-20 specific passages that should be CUT or REWRITTEN.
   For each, quote the EXACT text (minimum 10 words of the quote so
   it's unambiguous), explain why it's weak, and classify it.

2. Classify each cut as one of:
   - FAT: adds nothing, could be removed with no loss
   - REDUNDANT: restates what a previous sentence/scene already showed
   - OVER-EXPLAIN: narrator explaining what the scene already demonstrated
    - GENERIC: could appear in any novel, not specific to this world/character.
      Includes aphorism formulas ("X is the language of Y"), authority framings
      ("At its core, what matters is..."), and generic capstone sentences
      ("The future looked bright.")
    - TELL: names an emotion or state instead of showing it
    - STACCATO: manufactured punchlines — 3+ consecutive ultra-short sentences
      for artificial dramatic effect ("It had no preference. No prior. No nostalgia.")
   - STRUCTURAL: paragraph/section that disrupts pacing or rhythm
   - UNGROUNDED: uses a name, title, term, or concept without it having been
     established in the disclosure ceiling above. Example: a character is addressed
     as "the Saint" but no prior chapter has explained what a Saint is.

3. For REWRITE candidates (not cuts), provide a specific revision.

4. Estimate how many words could be cut total without losing anything
   the chapter needs.

Respond with JSON:
{{
  "cuts": [
    {{
      "quote": "exact text from the chapter (10+ words)",
      "type": "FAT|REDUNDANT|OVER-EXPLAIN|GENERIC|TELL|STRUCTURAL",
      "reason": "why this should go",
      "action": "CUT or REWRITE",
      "rewrite": "replacement text if action is REWRITE, null if CUT"
    }}
  ],
  "total_cuttable_words": N,
  "tightest_passage": "quote the best 2-3 sentences in the chapter -- the ones you'd never touch",
  "loosest_passage": "quote the worst 2-3 sentences -- the ones that most need work",
  "overall_fat_percentage": N,
  "one_sentence_verdict": "what this chapter does well and what drags it down, in one sentence"
}}

IMPORTANT: After you finish your first pass, do a second read.
Ask yourself: "Does any sentence here still feel like an LLM wrote it?"
If yes, flag those too. Trust the instinct — if it sounds clean, generic,
or too perfectly balanced, it's probably AI-slop.
"""

def edit_chapter(ch_num):
    chapters_dir = utils.get_chapters_dir()
    edit_log_dir = utils.get_edit_logs_dir()
    ch_path = chapters_dir / f"ch_{ch_num:02d}.md"
    text = ch_path.read_text(encoding="utf-8")
    word_count = len(text.split())

    # Load canon disclosure ceiling (everything revealed through prior chapters)
    canon_text = ""
    canon_path = utils.get_canon_path()
    if canon_path.exists():
        raw = canon_path.read_text(encoding="utf-8")
        as_of_sections = re.findall(r'(## As of Chapter \d+.*?)(?=\n## |\Z)', raw, re.DOTALL)
        if as_of_sections:
            prior = [s for s in as_of_sections
                     if re.search(r'## As of Chapter (\d+)', s)
                     and int(re.search(r'## As of Chapter (\d+)', s).group(1)) < ch_num]
            if prior:
                canon_text = prior[-1]

    prompt = EDIT_PROMPT.format(chapter_text=text, word_count=word_count, canon_context=canon_text or "(first chapter or no canon established yet)")
    raw = call_judge(prompt)
    result = parse_json(raw)
    
    # Save log
    log_path = edit_log_dir / f"ch{ch_num:02d}_cuts.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Validate LLM quotes match chapter text
    cuts = result.get("cuts", [])
    fat_pct = result.get("overall_fat_percentage", 0)
    print(f"  [DEBUG] Chapter {ch_num:02d} fat score generated: {fat_pct}%", file=sys.stderr)
    
    matched_count = 0
    failed_cuts = []
    for cut in cuts:
        quote = cut.get("quote", "")
        if not quote.strip():
            continue
        # Normalize whitespace to check presence
        norm_quote = re.sub(r"\s+", " ", quote).strip()
        norm_text = re.sub(r"\s+", " ", text).strip()
        if norm_quote in norm_text:
            matched_count += 1
        else:
            failed_cuts.append(quote)
            
    print(f"  [DEBUG] Quote Match Validation: {matched_count}/{len(cuts)} quotes matched in chapter text.", file=sys.stderr)
    if failed_cuts:
        print(f"  [DEBUG][WARN] {len(failed_cuts)} recommended cuts do NOT match the chapter text exactly (LLM alignment issue).", file=sys.stderr)
        for i, fq in enumerate(failed_cuts[:3]):
            print(f"    - Misaligned quote {i+1}: {fq[:60]}...", file=sys.stderr)
    
    return result, word_count

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Adversarial edit a chapter or all chapters")
    parser.add_argument("chapter", help="Chapter number (integer) or 'all'")
    parser.add_argument("--project", default=None, help="Project name (under projects/)")
    args = parser.parse_args()

    if args.project:
        utils.set_project_name(args.project)

    if args.chapter == "all":
        chapters = sorted([int(m.group(1)) for p in utils.get_chapters_dir().glob("ch_*.md") if (m := re.match(r"ch_(\d+)\.md", p.name))])
    else:
        try:
            chapters = [int(args.chapter)]
        except ValueError:
            print("Error: chapter must be an integer or 'all'")
            sys.exit(1)
    
    for ch in chapters:
        print(f"\n{'='*50}")
        print(f"EDITING CH {ch}")
        print(f"{'='*50}")
        
        try:
            result, wc = edit_chapter(ch)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        
        cuts = result.get("cuts", [])
        cuttable = result.get("total_cuttable_words", 0)
        fat_pct = result.get("overall_fat_percentage", 0)
        verdict = result.get("one_sentence_verdict", "")
        
        # Count by type
        type_counts = {}
        for c in cuts:
            t = c.get("type", "?")
            type_counts[t] = type_counts.get(t, 0) + 1
        
        print(f"  Words: {wc}")
        print(f"  Cuts found: {len(cuts)}")
        print(f"  Cuttable words: ~{cuttable} ({fat_pct}% fat)")
        print(f"  By type: {type_counts}")
        print(f"  Verdict: {verdict}")
        print(f"  Tightest: {result.get('tightest_passage', '')[:100]}...")
        print(f"  Loosest:  {result.get('loosest_passage', '')[:100]}...")

if __name__ == "__main__":
    main()
