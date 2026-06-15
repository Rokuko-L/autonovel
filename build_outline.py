#!/usr/bin/env python3
"""
Rebuild outline.md from the actual chapters.
Reads each chapter, calls the LLM for a structured summary,
and assembles into an outline that reflects the novel as-written.
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

def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    start = text.find('{')
    if start == -1:
        raise ValueError("No JSON object found in response")
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == '\\' and in_string:
            escape = True
            continue
        if c == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i+1], strict=False)
    return json.loads(text[start:], strict=False)


def call_model(prompt, max_tokens=1500):
    return call_anthropic(prompt=prompt, system="You produce structured outline entries for novel chapters. Be precise about what HAPPENS, what CHANGES, and what threads are planted/harvested. Output valid JSON only.", model_key="judge", max_tokens=max_tokens, temperature=0.1, timeout=120)

def main():
    # Load supporting docs for context
    characters = utils.get_characters_path().read_text(encoding="utf-8")[:3000]
    
    chapters_dir = utils.get_chapters_dir()
    chapter_files = sorted(chapters_dir.glob("ch_*.md"))
    if not chapter_files:
        print("No chapter files found!")
        return

    entries = []
    
    for path in chapter_files:
        m = re.search(r"ch_(\d+)\.md", path.name)
        if not m:
            continue
        ch = int(m.group(1))
        
        text = path.read_text(encoding="utf-8")
        wc = len(text.split())
        
        title_line = text.strip().split('\n')[0].lstrip('# ').strip()
        
        prompt = f"""Analyze this chapter and produce a structured outline entry.

CHAPTER {ch}: "{title_line}" ({wc} words)

{text}

Return JSON with these fields:
- "title": the chapter title (string)
- "location": primary setting (string)
- "characters": list of characters who appear (list of strings)
- "summary": 2-3 sentence summary of what happens (string)
- "beats": list of 3-5 key story beats in order (list of strings)
- "try_fail": the try-fail cycle type: "yes-but", "no-and", "yes-and", or "no-but" (string)
- "plants": foreshadowing threads PLANTED in this chapter (list of strings)
- "harvests": foreshadowing threads PAID OFF in this chapter (list of strings)
- "emotional_arc": one sentence describing the emotional movement (string)
- "chapter_question": the question left open at chapter's end (string)

JSON only, no other text."""

        raw_data = call_model(prompt)
        data = parse_json(raw_data)
        data["num"] = ch
        data["words"] = wc
        entries.append(data)
        print(f"  {ch:2d}. {title_line} ({wc}w)")
    
    # Load existing outline header info
    try:
        old_outline = utils.get_outline_path().read_text(encoding="utf-8", errors="ignore")
    except Exception:
        old_outline = ""
    
    # Load dynamic title and cycle
    title = utils.get_novel_title()
    cycle_str = ""
    state_path = utils.get_state_path()
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            cycle = state.get("revision_cycle", 0)
            cycle_str = f", Cycle {cycle}"
        except Exception:
            pass

    # Build new outline
    lines = []
    lines.append(f"# {title.upper()}")
    lines.append("## Chapter Outline (reflects actual novel as-written)")
    lines.append("")
    lines.append(f"**{len(entries)} chapters, {sum(e['words'] for e in entries):,} words**")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    for e in entries:
        lines.append(f"### Ch {e['num']}: {e['title']}")
        lines.append(f"**{e['words']} words** | **Location:** {e.get('location', 'N/A')}")
        lines.append(f"- **Characters:** {', '.join(e.get('characters', []))}")
        lines.append(f"- **Try-fail cycle:** {e.get('try_fail', 'N/A')}")
        lines.append(f"- **Emotional arc:** {e.get('emotional_arc', 'N/A')}")
        lines.append("")
        lines.append(f"**Summary:** {e.get('summary', 'N/A')}")
        lines.append("")
        lines.append("**Beats:**")
        for b in e.get("beats", []):
            lines.append(f"1. {b}")
        lines.append("")
        if e.get("plants"):
            lines.append("**Plants:**")
            for p in e["plants"]:
                lines.append(f"- {p}")
            lines.append("")
        if e.get("harvests"):
            lines.append("**Harvests:**")
            for h in e["harvests"]:
                lines.append(f"- {h}")
            lines.append("")
        lines.append(f"**Chapter question:** {e.get('chapter_question', 'N/A')}")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # Foreshadowing ledger
    lines.append("## FORESHADOWING LEDGER")
    lines.append("")
    lines.append("| Thread | Planted | Harvested |")
    lines.append("|--------|---------|-----------|")
    
    # Collect all plants and harvests
    all_plants = {}
    all_harvests = {}
    for e in entries:
        for p in e.get("plants", []):
            key = p[:60]
            if key not in all_plants:
                all_plants[key] = []
            all_plants[key].append(e["num"])
        for h in e.get("harvests", []):
            key = h[:60]
            if key not in all_harvests:
                all_harvests[key] = []
            all_harvests[key].append(e["num"])
    
    # Match plants to harvests by keyword overlap
    all_threads = set(list(all_plants.keys()) + list(all_harvests.keys()))
    for thread in sorted(all_threads):
        planted = ", ".join(f"Ch {n}" for n in all_plants.get(thread, []))
        harvested = ", ".join(f"Ch {n}" for n in all_harvests.get(thread, []))
        lines.append(f"| {thread} | {planted} | {harvested} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Outline rebuilt from actual chapters{cycle_str}.*")
    
    out = '\n'.join(lines)
    utils.get_outline_path().write_text(out, encoding="utf-8")
    print(f"\nSaved outline.md ({len(out.split())} words)")

if __name__ == "__main__":
    main()
