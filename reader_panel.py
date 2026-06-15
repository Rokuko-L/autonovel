#!/usr/bin/env python3
"""
4-reader panel for full-arc novel evaluation.
Each reader has a distinct persona and evaluates the NOVEL, not chapters.
The disagreements between readers are where editorial decisions live.

Usage: python reader_panel.py
"""
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from utils import call_anthropic
from genre import load_genre

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

READERS = {
    "editor": {
        "name": "The Editor",
        "system": (
            "You are a senior fiction editor at a major publishing house. "
            "You've edited 200+ novels. You care about prose texture, subtext, "
            "sentence-level craft, and whether the voice is consistent and earned. "
            "You notice when the narrator over-explains, when dialogue sounds "
            "written rather than spoken, when a metaphor is borrowed rather than "
            "earned. You are not cruel but you are precise. You've seen enough "
            "competent prose to know the difference between good and alive. "
            "You respond with valid JSON only."
        ),
    },
    "genre_reader": {
        "name": "The Genre Reader",
        "system": load_genre()["evaluation"]["reader_panel"]["genre_reader_identity"],
    },
    "writer": {
        "name": "The Writer",
        "system": (
            "You are a published fantasy author with 5 novels and a Hugo nomination. "
            "You read as a craftsperson. You notice structure: where the beats fall, "
            "whether foreshadowing pays off, whether character arcs complete. You "
            "notice when technique shows versus when it disappears into the story. "
            "The highest compliment you give is 'I forgot I was reading.' The worst "
            "thing you can say is 'I can see the outline.' You care about the gap "
            "between what a novel attempts and what it achieves. You respond with "
            "valid JSON only."
        ),
    },
    "first_reader": {
        "name": "The First Reader",
        "system": (
            "You are a thoughtful general reader. Not a writer, not an editor, "
            "not a genre expert. You read for the experience. You know what you "
            "feel but not always why. You notice when you're moved, when you're "
            "bored, when you're confused, when you want to tell someone about "
            "what you just read. You don't use craft terminology. You say things "
            "like 'I didn't care about this part' and 'I had to put the book down "
            "after this scene because I needed a minute.' Your feedback is emotional "
            "and honest, not analytical. You respond with valid JSON only."
        ),
    },
}

def build_reader_prompt():
    cfg = load_genre()
    mods = cfg["evaluation"]["reader_panel"].get("prompt_modifications", {}) or {}
    earned_hint = mods.get("earned_ending_hint", "Does the ending feel earned by everything before it?")

    prompt = f"""You have just read a complete novel in summary form.
The summaries include chapter-by-chapter events, opening and closing passages
from each chapter, and key dialogue. The full novel is {{word_count:,}} words across
{{chapter_count}} chapters.

{{arc_summary}}

Now answer these questions about the NOVEL AS A WHOLE. Be specific.
Quote passages when you can. Name chapter numbers.

Respond with JSON:
{{{{
  "momentum_loss": "Where does the story lose momentum?...",

  "earned_ending": "{earned_hint}",

  "cut_candidate": "If the novel had to be 10% shorter (~{{cut_words:,}} words), which chapter or section would you cut first?...",

  "missing_scene": "Is there a scene the novel NEEDS that it doesn't have?...",

  "thinnest_character": "Which character feels thinnest?...",

  "best_scene": "What's the single best scene?...",

  "worst_scene": "What's the single weakest scene?...",

  "would_recommend": "Would you recommend this novel?...",

  "haunts_you": "Is there a line or moment that stays with you?...",

  "next_book": "Would you read the author's next book?..."
"""
    extra_qs = mods.get("extra_questions", {}) or {}
    for qkey, qtext in extra_qs.items():
        prompt += f'\n  "{qkey}": "{qtext}",'

    prompt += "\n}}"
    return prompt

def call_reader(reader_key, arc_summary):
    reader = READERS[reader_key]
    ch_files = sorted(BASE_DIR.glob("chapters/ch_*.md"))
    chapter_count = len(ch_files)
    word_count = sum(len(f.read_text().split()) for f in ch_files) if ch_files else 0
    cut_words = int(word_count * 0.1) if word_count else 7000
    prompt = build_reader_prompt().format(arc_summary=arc_summary, word_count=word_count, chapter_count=chapter_count, cut_words=cut_words)
    raw = call_anthropic(prompt=prompt, system=reader["system"], model_key="judge", max_tokens=4000, timeout=300, temperature=0.7)
    
    # Parse JSON
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r'^```\w*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw)
    start = raw.find('{')
    if start >= 0:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(raw)):
            c = raw[i]
            if escape: escape = False; continue
            if c == '\\' and in_string: escape = True; continue
            if c == '"' and not escape: in_string = not in_string; continue
            if in_string: continue
            if c == '{': depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return json.loads(raw[start:i+1], strict=False)
    return json.loads(raw, strict=False)

def find_disagreements(results):
    """Find where readers disagree -- that's where the editorial decisions live."""
    disagreements = []
    
    for question in ["momentum_loss", "cut_candidate", "thinnest_character", "worst_scene"]:
        answers = {k: v.get(question, "") for k, v in results.items()}
        # Extract chapter numbers mentioned
        chapters_mentioned = {}
        for reader, answer in answers.items():
            chs = set(re.findall(r'Ch(?:apter)?\s*(\d+)', answer, re.IGNORECASE))
            chapters_mentioned[reader] = chs
        
        # Find chapters where only some readers flagged an issue
        all_chs = set()
        for chs in chapters_mentioned.values():
            all_chs.update(chs)
        
        for ch in all_chs:
            flagged_by = [r for r, chs in chapters_mentioned.items() if ch in chs]
            not_flagged = [r for r, chs in chapters_mentioned.items() if ch not in chs]
            if flagged_by and not_flagged:
                disagreements.append({
                    "question": question,
                    "chapter": int(ch),
                    "flagged_by": flagged_by,
                    "not_flagged": not_flagged,
                    "details": {r: answers[r][:200] for r in flagged_by}
                })
    
    return disagreements

def main():
    arc_summary = (BASE_DIR / "arc_summary.md").read_text()
    
    results = {}
    for reader_key, reader_info in READERS.items():
        print(f"\n{'='*50}")
        print(f"READING: {reader_info['name']}")
        print(f"{'='*50}")
        
        try:
            result = call_reader(reader_key, arc_summary)
            results[reader_key] = result
            
            # Print highlights
            print(f"  Momentum loss: {result.get('momentum_loss', '')[:150]}...")
            print(f"  Best scene: {result.get('best_scene', '')[:150]}...")
            print(f"  Would recommend: {result.get('would_recommend', '')[:150]}...")
        except Exception as e:
            print(f"  ERROR: {e}")
    
    # Find disagreements
    disagreements = find_disagreements(results)
    
    # Print consensus and disagreement
    print(f"\n{'='*60}")
    print("READER PANEL RESULTS")
    print(f"{'='*60}")
    
    for question in ["momentum_loss", "earned_ending", "cut_candidate", "missing_scene", 
                      "thinnest_character", "best_scene", "worst_scene", "would_recommend",
                      "haunts_you", "next_book"]:
        print(f"\n--- {question.upper()} ---")
        for reader_key in READERS:
            if reader_key in results:
                answer = results[reader_key].get(question, "N/A")
                print(f"  [{READERS[reader_key]['name']}]: {answer[:300]}")
    
    if disagreements:
        print(f"\n{'='*60}")
        print("DISAGREEMENTS (editorial decisions needed)")
        print(f"{'='*60}")
        for d in disagreements:
            print(f"\n  {d['question']} -- Ch {d['chapter']}")
            print(f"    Flagged by: {', '.join(d['flagged_by'])}")
            print(f"    Not flagged: {', '.join(d['not_flagged'])}")
    
    # Save full results
    output = {
        "readers": results,
        "disagreements": disagreements,
        "timestamp": datetime.now().isoformat()
    }
    out_path = BASE_DIR / "edit_logs" / "reader_panel.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {out_path}")

if __name__ == "__main__":
    main()
