#!/usr/bin/env python3
"""
evaluate.py -- Novel evaluation harness.

Usage:
  python evaluate.py --phase=foundation    # Score planning docs only
  python evaluate.py --chapter=5           # Score a single chapter
  python evaluate.py --full                # Score the entire novel

Output: structured scores to stdout + eval_logs/<timestamp>.json

This file is READ-ONLY during autonomous runs. The human edits it
to tune what "good" means. The agent treats it as a black box.
"""

import argparse
import json
import os
import sys
import glob
import re
from datetime import datetime
from pathlib import Path

# --- Configuration ---

# Load .env file if present
from dotenv import load_dotenv
load_dotenv()
from utils import extract_text_from_response, get_max_tokens_with_thinking, call_anthropic
from genre import load_genre
import utils


# ---- Mechanical Slop Detection (no LLM needed) ----

TIER1_BANNED = [
    "delve", "utilize", "leverage", "facilitate", "elucidate",
    "embark", "endeavor", "encompass", "multifaceted", "tapestry",
    "paradigm", "synergy", "synergize", "holistic", "catalyze",
    "catalyst", "juxtapose", "myriad", "plethora",
]

TIER2_SUSPICIOUS = [
    "robust", "comprehensive", "seamless", "seamlessly", "cutting-edge",
    "innovative", "streamline", "empower", "foster", "enhance", "elevate",
    "optimize", "pivotal", "intricate", "profound", "resonate",
    "underscore", "harness", "cultivate", "bolster", "galvanize",
    "cornerstone", "game-changer", "scalable",
]

TIER3_FILLER = [
    r"it'?s worth noting that",
    r"it'?s important to note that",
    r"^importantly,?\s",
    r"^notably,?\s",
    r"^interestingly,?\s",
    r"let'?s dive into",
    r"let'?s explore",
    r"as we can see",
    r"^furthermore,?\s",
    r"^moreover,?\s",
    r"^additionally,?\s",
    r"in today'?s .*(fast-paced|digital|modern)",
    r"at the end of the day",
    r"it goes without saying",
    r"when it comes to",
    r"one might argue that",
    r"not just .+, but",
    # Conversational rhetoric openers (Humanizer #33)
    r"^Honestly\?[\s,]",
    r"^Truthfully[?,]\s",
    r"^Look,?\s",
]

TRANSITION_OPENERS = [
    "however", "furthermore", "additionally", "moreover",
    "nevertheless", "consequently", "nonetheless", "similarly",
]

# Fiction-specific AI tells (prose clichés that betray machine origin)
FICTION_AI_TELLS = [
    r"a sense of \w+",
    r"couldn'?t help but feel",
    r"the weight of \w+",
    r"the air was thick with",
    r"eyes widened",
    r"a wave of \w+ washed over",
    r"a pang of \w+",
    r"heart pounded in (?:his|her|their) chest",
    r"(?:raven|dark|golden|silver) (?:hair|tresses) (?:spilled|cascaded|tumbled|fell)",
    r"piercing (?:blue|green|gray|grey|dark) eyes",
    r"a knowing (?:smile|grin|look|glance)",
    r"(?:he|she|they) felt a (?:surge|rush|wave|pang|flicker) of",
    r"the silence (?:was|hung|stretched|grew) (?:heavy|thick|oppressive|deafening)",
    r"let out a breath (?:he|she|they) didn'?t (?:know|realize)",
    r"something (?:dark|ancient|primal|unnamed) stirred",
    # Copula avoidance -- "serves as" instead of "is" (Humanizer #8)
    r"\b(?:serves as|serves to|stands as|acts as|functions as)\b",
    # Generic capstone conclusions (Humanizer #25)
    r"the future (?:looked|seemed|promised|appeared)",
]

# Structural AI tics -- rhetorical formulas that betray AI composition
STRUCTURAL_AI_TICS = [
    r"(?:I'm|I am) not (?:saying|asking|suggesting) .{3,40}(?:I'm|I am) (?:saying|asking|suggesting)",  # "I'm not saying X. I'm saying Y"
    r"(?:which|that) means either .{3,40} or ",  # "which means either X, or Y"
    r"[Tt]here'?s a (?:difference|distinction)\.",  # formula capper
    r"[Tt]hose are (?:different|not the same) things\.",  # formula capper
    r"[Nn]ot (?:just|merely|simply) .{3,40}, but ",  # "not just X, but Y"
    r"[Nn]ot (?:from|by|because of) .{3,40}, but (?:from|by|because)",  # "not from X, but from Y" in narration
    # Authority framing (Humanizer #27)
    r"^At its core,?",
    r"^The truth is,?",
    r"^What matters is,?",
    r"^The fact (?:is|remains),?",
    # Aphorism formulas (Humanizer #32)
    r"\b(?:is|was) the (?:language|art|science|essence|foundation|soul|hallmark|bedrock|currency) of\b",
]

# Show-don't-tell detectors: emotion TELLING patterns
TELLING_PATTERNS = [
    r"\b(?:he|she|they|I|we|[A-Z]\w+) (?:felt|was|seemed|looked|appeared) (?:angry|sad|happy|scared|nervous|excited|jealous|guilty|anxious|lonely|desperate|furious|terrified|elated|miserable|hopeful|confused|relieved|horrified|disgusted|ashamed|proud|bitter|defeated|triumphant)\b",
    r"\b(?:angrily|sadly|happily|nervously|excitedly|desperately|furiously|anxiously|guiltily|bitterly|wearily|miserably)\b",
]


def slop_score(text):
    """
    Mechanical slop detection. Returns a dict with:
      - tier1_hits: list of (word, count)
      - tier2_hits: list of (word, count)
      - tier3_hits: list of (pattern, count)
      - em_dash_density: em dashes per 1000 words
      - sentence_length_cv: coefficient of variation (higher = more human)
      - transition_opener_ratio: fraction of paragraphs starting with transitions
      - slop_penalty: 0-10 deduction (0 = clean, 10 = pure slop)
    """
    words = text.lower().split()
    word_count = len(words) or 1

    # Tier 1
    tier1_hits = []
    for w in TIER1_BANNED:
        c = sum(1 for token in words if token.strip(".,;:!?\"'()") == w)
        if c > 0:
            tier1_hits.append((w, c))

    # Tier 2 -- count per paragraph, flag clusters
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    tier2_hits = []
    tier2_cluster_count = 0
    for w in TIER2_SUSPICIOUS:
        c = sum(1 for token in words if token.strip(".,;:!?\"'()") == w)
        if c > 0:
            tier2_hits.append((w, c))
    for para in paragraphs:
        para_lower = para.lower()
        hits_in_para = sum(1 for w in TIER2_SUSPICIOUS if w in para_lower)
        if hits_in_para >= 3:
            tier2_cluster_count += 1

    # Tier 3
    tier3_hits = []
    for pattern in TIER3_FILLER:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            tier3_hits.append((pattern, len(matches)))

    # Em dash density
    em_dashes = text.count("—") + text.count("--")
    em_dash_density = (em_dashes / word_count) * 1000

    # Sentence length variation (coefficient of variation)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip().split()) > 2]
    if len(sentences) > 2:
        lengths = [len(s.split()) for s in sentences]
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        std_len = variance ** 0.5
        sentence_length_cv = std_len / mean_len if mean_len > 0 else 0
    else:
        sentence_length_cv = 0.5  # not enough data, assume OK

    # Transition opener ratio
    transition_starts = 0
    for para in paragraphs:
        first_word = para.split()[0].lower().strip(".,;:!?\"'()") if para.split() else ""
        if first_word in TRANSITION_OPENERS:
            transition_starts += 1
    transition_ratio = transition_starts / len(paragraphs) if paragraphs else 0

    # Fiction AI tells
    fiction_tells = []
    for pattern in FICTION_AI_TELLS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            fiction_tells.append((pattern[:40], len(matches)))
    fiction_tell_count = sum(c for _, c in fiction_tells)

    # Show-don't-tell violations
    telling_count = 0
    for pattern in TELLING_PATTERNS:
        telling_count += len(re.findall(pattern, text, re.IGNORECASE))

    # Structural AI tics (rhetorical formulas)
    structural_tics = []
    for pattern in STRUCTURAL_AI_TICS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            structural_tics.append((pattern[:40], len(matches)))
    structural_tic_count = sum(c for _, c in structural_tics)

    # Staccato punchline detector (Humanizer #31) — 3+ consecutive sentences ≤4 words
    staccato_runs = 0
    for para in paragraphs:
        para_sents = [s.strip() for s in re.split(r'[.!?]+', para) if len(s.strip().split()) > 0]
        run = 0
        for s in para_sents:
            if len(s.split()) <= 4:
                run += 1
                if run == 3:
                    staccato_runs += 1
            else:
                run = 0

    # Composite penalty (0 = clean, 10 = disaster)
    penalty = 0.0
    penalty += min(len(tier1_hits) * 1.5, 4.0)       # tier1: up to 4 pts
    penalty += min(tier2_cluster_count * 1.0, 2.0)    # tier2 clusters: up to 2 pts
    penalty += min(sum(c for _, c in tier3_hits) * 0.3, 2.0)  # tier3: up to 2 pts
    if em_dash_density > 15:
        penalty += min((em_dash_density - 15) * 0.3, 1.0)  # em dashes: up to 1 pt (threshold raised for voice)
    if sentence_length_cv < 0.3:
        penalty += 1.0  # uniform sentence length: 1 pt
    if transition_ratio > 0.3:
        penalty += min(transition_ratio * 2, 1.0)  # transition abuse: up to 1 pt
    penalty += min(fiction_tell_count * 0.3, 2.0)     # fiction AI tells: up to 2 pts
    penalty += min(telling_count * 0.2, 1.5)          # show-don't-tell: up to 1.5 pts
    penalty += min(structural_tic_count * 0.5, 2.0)   # structural AI tics: up to 2 pts
    penalty += min(staccato_runs * 0.5, 1.0)          # staccato punchlines: up to 1 pt

    penalty = min(penalty, 10.0)

    return {
        "tier1_hits": tier1_hits,
        "tier2_hits": tier2_hits,
        "tier2_clusters": tier2_cluster_count,
        "tier3_hits": tier3_hits,
        "fiction_ai_tells": fiction_tells,
        "structural_ai_tics": structural_tics,
        "staccato_runs": staccato_runs,
        "telling_violations": telling_count,
        "em_dash_density": round(em_dash_density, 2),
        "sentence_length_cv": round(sentence_length_cv, 3),
        "transition_opener_ratio": round(transition_ratio, 3),
        "slop_penalty": round(penalty, 2),
    }


def load_file(path):
    """Load a text file, return empty string if missing, with robust encoding recovery and self-healing."""
    path = Path(path)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = path.read_bytes()
        for enc in ("utf-16", "utf-16-le", "utf-16-be", "latin-1"):
            try:
                text = raw.decode(enc).lstrip("\ufeff")
                # Self-heal: rewrite as clean UTF-8
                path.write_text(text, encoding="utf-8")
                print(f"[ENCODING] Repaired {path.name}: was {enc}, now UTF-8", file=sys.stderr)
                return text
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode {path} with any known encoding")


def load_layer_files():
    """Load all planning layer files from the active project directory."""
    return {
        "voice": load_file(utils.get_voice_path()),
        "world": load_file(utils.get_world_path()),
        "characters": load_file(utils.get_characters_path()),
        "outline": load_file(utils.get_outline_path()),
        "canon": load_file(utils.get_canon_path()),
    }


def load_chapter(n):
    """Load a single chapter file from the active project."""
    return load_file(utils.get_chapters_dir() / f"ch_{n:02d}.md")


def load_all_chapters():
    """Load all chapter files in order from the active project."""
    chapters_dir = utils.get_chapters_dir()
    chapters = {}
    for f in sorted(glob.glob(str(chapters_dir / "ch_*.md"))):
        num = int(re.search(r'ch_(\d+)', f).group(1))
        try:
            chapters[num] = load_file(Path(f))
        except ValueError as e:
            raise RuntimeError(f"FATAL: chapter file {f} (ch {num}) is unreadable: {e}")
    return chapters


def call_judge(prompt, max_tokens=2000):
    return call_anthropic(prompt=prompt, system=load_genre()["identity"]["evaluator_system"], model_key="judge", max_tokens=max_tokens, beta_context=True, timeout=180)


def parse_json_response(text):
    return utils.parse_json_response(text)


def call_judge_json(prompt, max_tokens=8000, retries=3):
    last_raw = None
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            if attempt == 1:
                raw = call_judge(prompt, max_tokens)
            else:
                # Ask the model to fix its previous response (using a cheap, lightweight context prompt)
                fix_prompt = f"""You previously returned a response that had invalid JSON syntax.
The parser returned this error: {last_error}

YOUR PREVIOUS RESPONSE:
{last_raw}

TASK:
Correct the JSON syntax errors in your previous response. Respond ONLY with the corrected, valid JSON object. Do not include any explanation or conversational text outside the JSON. Ensure all quotes inside string values are properly escaped (e.g. use \\" instead of ")."""
                # Dynamically calculate a token limit for the fix call
                tokens_needed = max(2000, (len(last_raw) // 3) + 200)
                max_tokens_fix = min(max_tokens, tokens_needed)
                
                raw = call_judge(fix_prompt, max_tokens_fix)
            
            last_raw = raw
            return parse_json_response(raw)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = str(e)
            if attempt == retries:
                raise e
            print(f"JSON decode failed on attempt {attempt}/{retries}: {e}. Retrying LLM self-correction...", file=sys.stderr)


# --- Foundation Evaluation ---

def build_foundation_prompt():
    cfg = load_genre()
    ecfg = cfg["evaluation"]["foundation"]
    prompt = ecfg["overall_calibration"] + "\n\n"

    prompt += """VOICE DEFINITION:
{voice}

WORLD BIBLE:
{world}

CHARACTER REGISTRY:
{characters}

OUTLINE:
{outline}

CANON (established facts):
{canon}

CROSS-CHECKS (perform these before scoring):
1. Check all example dialogue lines against ANTI-SLOP patterns
2. Check for missing NEGATIVE SPACE
3. Check for CONVENIENT GAPS vs DELIBERATE MYSTERY
4. Check the canon for INTERNAL CONTRADICTIONS

Score these dimensions (gap + improvement required for each):

"""
    for dim in ecfg["dimensions"]:
        prompt += f"- {dim['key'].replace('_', ' ').title()}: {dim['criteria']}\n\n"

    prompt += f"""
Respond with JSON:
{{
{chr(10).join(f'  "{dim["key"]}": {{"score": N, "gap": "...", "fix": "...", "note": "..."}},' for dim in ecfg["dimensions"])}
  "slop_in_planning_docs": {{"found": ["list any AI slop patterns"], "note": "..."}},
  "contradictions_found": ["list any factual contradictions"],
  "overall_score": N,
  "lore_score": N,
  "weakest_dimension": "...",
  "top_3_improvements": ["ranked list of improvements"]
}}

CRITICAL FORMATTING GUIDELINES:
1. Output ONLY valid JSON matching the exact schema above.
2. Escape any double quotes within your JSON string values with a backslash (e.g., use \\" instead of " when referencing characters, quotes, or dialogue).
3. Do not include any preamble, introduction, or conversation outside the JSON object.

WEIGHTING: {" + ".join(f'{dim["key"].replace("_"," ").title()} {dim["weight"]*100:.0f}%' for dim in ecfg["dimensions"])}.

FINAL CHECK: If your overall_score is above 7, re-read your gap lists.
If any gap describes a problem that would force a writer to stop and
invent something during drafting, your score is too high. Revise down.
"""
    return prompt


def evaluate_foundation():
    layers = load_layer_files()
    prompt = build_foundation_prompt()
    for key, val in layers.items():
        prompt = prompt.replace(f"{{{key}}}", val)
    return call_judge_json(prompt, max_tokens=16000)


# --- Chapter Evaluation ---

def build_chapter_prompt(voice, world, characters, canon, chapter_outline, prev_chapter_tail, chapter_text, disclosure_ceiling=""):
    cfg = load_genre()
    ccfg = cfg["evaluation"]["chapter"]
    prompt = ccfg["overall_calibration"] + "\n\n"

    prompt += f"""VOICE DEFINITION:
{voice}

WORLD BIBLE (summary):
{world}

CHARACTER REGISTRY:
{characters}

CANON (established hard facts -- violations are bugs):
{canon}

CHAPTER OUTLINE ENTRY:
{chapter_outline}

PREVIOUS CHAPTER (last 1500 words):
{prev_chapter_tail}

THE CHAPTER TO EVALUATE:
{chapter_text}

DISCLOSURE CEILING (everything that has been put on the page through the prior chapter):
{disclosure_ceiling}

CANON-GROUNDING RULES (read before scoring):
- new_canon_entries: Record only what was explicitly shown or stated in this chapter's text.
  Never record background facts from the world/character bible that haven't been put on the page.
- unexplained_references: Names, titles, or terms used in this chapter whose meaning
  a first-time reader would not yet understand (e.g. if a character is addressed as "the Saint"
  but the role hasn't been explained yet).

CROSS-CHECKS (perform before scoring):
1. QUOTE TEST: Find the 3 best sentences and 3 weakest sentences.
2. DIALOGUE REALISM: Read all dialogue aloud (mentally).
3. SCENE VS SUMMARY: How much is in-scene vs summary?
4. AI PATTERN CHECK: Common AI writing patterns.
5. EARNED VS GIVEN: Is tension earned or asserted?

Score these dimensions:

"""
    for dim in ccfg["dimensions"]:
        prompt += f"- {dim['key'].replace('_', ' ').title()}: {dim['criteria']}\n\n"

    prompt += f"""
Respond with JSON:
{{
{chr(10).join(f'  "{dim["key"]}": {{"score": N, "weakest_moment": "...", "fix": "...", "note": "..."}},' for dim in ccfg["dimensions"])}
  "three_weakest_sentences": ["quote 1", "quote 2", "quote 3"],
  "three_strongest_sentences": ["quote 1", "quote 2", "quote 3"],
  "ai_patterns_detected": ["list any AI writing patterns found"],
  "overall_score": N,
  "weakest_dimension": "...",
  "top_3_revisions": ["specific revision 1", "revision 2", "revision 3"],
  "new_canon_entries": ["any new facts established"],
  "unexplained_references": ["names, titles, or terms used in this chapter that were not explained"]
}}

CRITICAL FORMATTING GUIDELINES:
1. Output ONLY valid JSON matching the exact schema above.
2. Escape any double quotes within your JSON string values with a backslash (e.g., use \\" instead of " when referencing characters, quotes, or dialogue).
3. Do not include any preamble, introduction, or conversation outside the JSON object.

FINAL CHECK: If your overall_score is above 7, re-read your weakest_moment
quotes. If any describe a problem an editor would flag, your score is too high.
"""
    return prompt


def evaluate_chapter(chapter_num):
    layers = load_layer_files()
    chapter_text = load_chapter(chapter_num)
    if not chapter_text.strip():
        return {"error": f"Chapter {chapter_num} is empty or missing",
                "overall_score": 0.0}

    # Extract this chapter's outline entry (rough heuristic)
    outline = layers["outline"]
    ch_pattern = rf'###\s*Ch\s*{chapter_num}\b.*?(?=###\s*Ch\s*\d|## Act|## Foreshadowing|$)'
    ch_match = re.search(ch_pattern, outline, re.DOTALL)
    chapter_outline = ch_match.group(0) if ch_match else "(outline entry not found)"

    # Load previous chapter tail
    prev_text = load_chapter(chapter_num - 1) if chapter_num > 1 else "(first chapter)"
    prev_tail = prev_text[-3000:] if len(prev_text) > 3000 else prev_text

    # Extract disclosure ceiling from canon (everything revealed through chapter N-1)
    disclosure_ceiling = ""
    canon_text = layers["canon"]
    if canon_text.strip():
        as_of_sections = re.findall(r'(## As of Chapter \d+.*?)(?=\n## |\Z)', canon_text, re.DOTALL)
        if as_of_sections:
            # Filter to chapters before the current one
            prior_sections = [s for s in as_of_sections
                             if re.search(rf'## As of Chapter (\d+)', s)
                             and int(re.search(r'## As of Chapter (\d+)', s).group(1)) < chapter_num]
            if prior_sections:
                disclosure_ceiling = prior_sections[-1]

    prompt = build_chapter_prompt(
        voice=layers["voice"],
        world=layers["world"][:4000],  # truncate world bible
        characters=layers["characters"],
        canon=layers["canon"],
        chapter_outline=chapter_outline,
        prev_chapter_tail=prev_tail,
        chapter_text=chapter_text,
        disclosure_ceiling=disclosure_ceiling,
    )
    result = call_judge_json(prompt, max_tokens=8000)

    # Mechanical slop check -- adjusts score independently of judge
    slop = slop_score(chapter_text)
    result["slop"] = slop
    if "overall_score" in result:
        adjusted = max(0, result["overall_score"] - slop["slop_penalty"])
        
        # Word count penalty
        genre_cfg = load_genre()
        estimated_words = genre_cfg["generation"]["outline"]["estimated_words"]
        chapter_count = genre_cfg["generation"]["outline"]["estimated_chapters"]
        target_words = estimated_words // chapter_count
        actual_words = len(chapter_text.split())
        
        length_penalty = 0.0
        if actual_words < target_words:
            length_penalty = max(0, (1 - actual_words / target_words)) * 3.0
            adjusted = max(0, adjusted - length_penalty)
            
        print(f"  [LENGTH] {actual_words}/{target_words} words — penalty: -{length_penalty:.2f}", file=sys.stderr)
        result["length_penalty"] = length_penalty
        result["raw_judge_score"] = result["overall_score"]
        result["overall_score"] = round(adjusted, 2)

    return result


# --- Full Novel Evaluation ---

FULL_NOVEL_PROMPT = """Evaluate this complete fantasy novel holistically.
You have the planning docs and ALL chapter summaries with their individual scores.

VOICE DEFINITION:
{voice}

WORLD BIBLE:
{world_summary}

CHARACTER REGISTRY:
{characters}

OUTLINE + FORESHADOWING LEDGER:
{outline}

CHAPTER SUMMARIES AND SCORES:
{chapter_summaries}

Score these novel-level dimensions 0-10:
- arc_completion: Do character arcs resolve satisfyingly?
- pacing_curve: Does tension build properly across the book?
- theme_coherence: Are themes explored consistently?
- foreshadowing_resolution: Are all planted threads harvested?
- world_consistency: Any lore contradictions across chapters?
- voice_consistency: Is the voice steady throughout?
- overall_engagement: Is this a compelling read start to finish?

Respond with JSON:
{{
  "arc_completion": {{"score": N, "note": "..."}},
  "pacing_curve": {{"score": N, "note": "..."}},
  "theme_coherence": {{"score": N, "note": "..."}},
  "foreshadowing_resolution": {{"score": N, "note": "..."}},
  "world_consistency": {{"score": N, "note": "..."}},
  "voice_consistency": {{"score": N, "note": "..."}},
  "overall_engagement": {{"score": N, "note": "..."}},
  "novel_score": N,
  "weakest_dimension": "...",
  "weakest_chapter": N,
  "top_suggestion": "..."
}}
"""


def evaluate_full():
    layers = load_layer_files()
    chapters = load_all_chapters()

    if not chapters:
        return {"error": "No chapters found", "novel_score": 0.0}

    # Build chapter summaries (first/last 500 chars of each)
    summaries = []
    for num in sorted(chapters.keys()):
        text = chapters[num]
        word_count = len(text.split())
        head = text[:500]
        tail = text[-500:] if len(text) > 500 else ""
        summaries.append(
            f"Chapter {num} ({word_count} words):\n"
            f"  Opening: {head}...\n"
            f"  Closing: ...{tail}\n"
        )

    prompt = FULL_NOVEL_PROMPT.format(
        voice=layers["voice"],
        world_summary=layers["world"][:3000],
        characters=layers["characters"],
        outline=layers["outline"],
        chapter_summaries="\n".join(summaries),
    )
    return call_judge_json(prompt)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Evaluate the novel")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--phase", choices=["foundation"],
                       help="Evaluate planning documents")
    group.add_argument("--chapter", type=int,
                       help="Evaluate a specific chapter number")
    group.add_argument("--full", action="store_true",
                       help="Evaluate the entire novel")
    parser.add_argument("--project", default=None, help="Project name (under projects/)")
    args = parser.parse_args()

    if args.project:
        utils.set_project_name(args.project)

    if args.phase == "foundation":
        result = evaluate_foundation()
        score_key = "overall_score"
    elif args.chapter is not None:
        result = evaluate_chapter(args.chapter)
        score_key = "overall_score"
    elif args.full:
        result = evaluate_full()
        score_key = "novel_score"

    # Print structured output
    print("---")
    if score_key in result:
        print(f"{score_key}: {result[score_key]}")
    for key, val in result.items():
        if key == score_key:
            continue
        if isinstance(val, dict):
            print(f"{key}: {val.get('score', 'N/A')} -- {val.get('note', '')}")
        else:
            print(f"{key}: {val}")

    # Save full eval log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = args.phase or (f"ch{args.chapter:02d}" if args.chapter else "full")
    eval_log_dir = utils.get_eval_logs_dir()  # also creates the directory
    log_path = eval_log_dir / f"{timestamp}_{mode}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\neval_log: {log_path}")


if __name__ == "__main__":
    main()
