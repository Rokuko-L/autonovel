#!/usr/bin/env python3
"""
gen_genre_framework.py — Step 0: Initialize genre configuration.
Reads genre description + chapter count + user notes, calls LLM with meta-prompt,
validates output, writes active_genre.json.

Usage:
  python gen_genre_framework.py --genre "Cyberpunk Noir" --chapters 12
  python gen_genre_framework.py --genre "High School Romance" --chapters 8 --notes "MC is a pianist, love interest is a graffiti artist"
  python gen_genre_framework.py --genre "Zombie Apocalypse" --chapters 30 --notes "Zombies are fungal-based, slow but strategic"
"""

import os
import re
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Load env
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

# Import utils for thinking token handling
from utils import extract_text_from_response, get_max_tokens_with_thinking, call_anthropic


META_PROMPT = """You are an expert literary theorist and narrative designer. You are configuring an AI novel-writing pipeline to handle ANY genre, not just fantasy.

=== USER INPUT ===
Genre: {genre_description}
Target length: {chapter_count} chapters
{user_directives_block}

=== YOUR TASK ===
Generate a complete genre configuration as valid JSON. This config will be loaded by every script in the pipeline (world builder, character designer, chapter drafter, evaluator, etc.) so they know what "good" means for THIS genre.

=== MAPPING RULE ===
The original pipeline was built for fantasy. For your genre, TRANSLATE each fantasy concept to its equivalent:

Fantasy concept       →  Your genre equivalent
────────────────────────────────────────────
Magic system          →  Core genre-specific system (social rules for romance, infection for zombie, corruption for noir, technology for cyberpunk)
Worldbuilding lore    →  Setting depth (school culture, city atmosphere, survival geography)
Magic costs           →  Costs of the core activity (social cost, moral cost, resource cost)
Bestiary / Flora      →  What's unique about this world's creatures/dangers
Factions & Politics   →  Power groups relevant to this genre
History / Timeline    →  Backstory that creates PRESENT-DAY tensions
Sensory geography     →  Locations with specific sensory signatures
Magic system rules    →  Hard rules of the core system (with costs and limitations)
Lore interconnection →  How all setting elements affect each other

=== CHAPTER COUNT NOTES ===
- {chapter_count} chapters total
- For a romance: Act I (~25%) = meet-cute + setup, Act II (~50%) = rising tension + crisis, Act III (~25%) = resolution
- For a mystery/noir: Act I = case arrives + investigation begins, Act II = leads + setbacks + danger, Act III = revelation + confrontation
- For a thriller: shorter chapters, higher pace. Act I shorter (~20%), Act II longer (~60%)
- For a literary/slice-of-life: looser structure, more character beats than plot beats
- Include pacing guidance in the outline.notes specific to this chapter count

=== REQUIRED OUTPUT SCHEMA ===
Output a JSON object with these exact fields:

1. "genre_name": "str — the name of this genre"
2. "user_directives": "str — the user's specific notes (empty string if none)"
3. "identity": {
     "seed_system": "str — system prompt for the seed generator",
     "world_system": "str — system prompt for the world/setting builder",
     "character_system": "str — system prompt for the character designer",
     "outline_system": "str — system prompt for the outline generator",
     "chapter_system": "str — system prompt for the chapter drafter",
     "revision_system": "str — system prompt for the revision writer",
     "canon_system": "str — system prompt for the canon extractor",
     "evaluator_system": "str — must start with 'You are a literary critic and novel editor.'"
   }
4. "generation": {
     "world": { "description": "str", "sections": ["list of section headers for the world/setting document"] },
     "character": { "description": "str", "focus_areas": ["list of character development focus areas"] },
     "outline": {
       "description": "str",
       "estimated_chapters": {chapter_count},
       "estimated_words": {estimated_words},
       "notes": ["list of structural notes specific to this genre's plot"]
     },
     "seed_generate_prompt": "str — complete prompt for seed.py to generate concepts in this genre",
     "seed_riff_prompt": "str — complete prompt for seed.py to riff on an idea in this genre",
     "gen_world_prompt": "str — complete prompt for gen_world.py to build the setting (use {{seed}} and {{voice_part2}} as placeholders)",
     "gen_characters_prompt": "str — complete prompt for gen_characters.py to create characters (use {{seed}}, {{world}}, {{voice_part2}} as placeholders)",
     "gen_outline_prompt": "str — complete prompt for gen_outline.py (use {{seed}}, {{world}}, {{characters}}, {{mystery}}, {{voice_part2}}, {{craft}} placeholders)",
     "gen_outline_part2_prompt": "str — complete prompt for gen_outline_part2.py (use {{part1}}, {{mystery}} placeholders)",
     "gen_canon_prompt": "str — complete prompt for gen_canon.py (use {{seed}}, {{world}}, {{characters}} placeholders)",
     "gen_revision_prompt": "str — complete prompt for gen_revision.py (use {{brief}}, {{voice}}, {{characters}}, {{world}}, {{prev_tail}}, {{next_head}}, {{old_text}} placeholders)",
     "draft_chapter_instructions": "str — writing instructions for the chapter drafter (numbered list style)",
     "anti_pattern_rules": "str — anti-pattern rules for the revision step (numbered list)",
     "canon_categories": ["list of category headers for the canon document"],
     "arc_summary_premise": "str — 2-3 sentence premise description for the arc summary"
   }
5. "evaluation": {
     "foundation": {
       "overall_calibration": "str — scoring calibration (9-10: ..., 7-8: ..., etc.)",
       "dimensions": [
         {"key": "world_depth", "weight": 0.0-1.0, "criteria": "str — what world_depth means in this genre, how to score it"},
         {"key": "character_depth", "weight": 0.0-1.0, "criteria": "str"},
         {"key": "plot_structure", "weight": 0.0-1.0, "criteria": "str"},
         {"key": "internal_consistency", "weight": 0.0-1.0, "criteria": "str"},
         {"key": "voice_clarity", "weight": 0.0-1.0, "criteria": "str"},
         {"key": "canon_coverage", "weight": 0.0-1.0, "criteria": "str"}
       ]
     },
     "chapter": {
       "overall_calibration": "str — scoring calibration for individual chapters",
       "dimensions": [
         {"key": "voice_adherence", "weight": 0.0-1.0, "criteria": "str"},
         {"key": "beat_coverage", "weight": 0.0-1.0, "criteria": "str"},
         {"key": "character_voice", "weight": 0.0-1.0, "criteria": "str"},
         {"key": "prose_quality", "weight": 0.0-1.0, "criteria": "str"},
         {"key": "engagement", "weight": 0.0-1.0, "criteria": "str"},
         {"key": "continuity", "weight": 0.0-1.0, "criteria": "str"}
       ]
     },
     "reader_panel": {
       "genre_reader_identity": "str — system prompt for the genre reader persona (e.g., 'You are an avid fantasy reader...')",
       "prompt_modifications": {
         "earned_ending_hint": "str — genre-specific ending question",
         "extra_questions": {}
       }
     }
   }
6. "framework": {
     "lore_priorities": "str — what matters most for this genre's setting evaluation",
     "stability_trap_applies": true,
     "character_framework": "str — character development requirements for this genre",
     "plot_framework": "str — plot structure requirements for this genre"
   }

=== RULES ===
- The dimension KEYS in evaluation are FIXED. Never change them. Only change their criteria and weights.
- All 6 foundation keys (world_depth, character_depth, plot_structure, internal_consistency, voice_clarity, canon_coverage) must ALWAYS be present.
- All 6 chapter keys (voice_adherence, beat_coverage, character_voice, prose_quality, engagement, continuity) must ALWAYS be present.
- Weights in each dimension group must sum to approximately 1.0 (allow ±0.02 tolerance).
- Every criteria string must be SPECIFIC and ACTIONABLE (30+ characters minimum). A writer should know what a "7" means vs a "4".
- Prompt strings must be substantial (100+ characters). Use {{variable}} syntax for placeholders (double braces for Python .format() compatibility).
- estimated_chapters must equal {chapter_count}. estimated_words = {estimated_words}.
- The evaluator_system must start with "You are a literary critic and novel editor."
- Every string should be ≥20 characters. Be specific. No generic filler.

Output ONLY valid JSON. No markdown fences, no preamble, no explanatory text."""


def call_llm(prompt, max_tokens=16000):
    return call_anthropic(prompt=prompt, system="You are an expert literary theorist and narrative designer. You generate structured JSON genre configurations for an AI novel-writing pipeline. You are precise, specific, and creative. You always output valid JSON.", model_key="writer", max_tokens=max_tokens, temperature=0.7, timeout=300)


def strip_json_fences(text):
    """Strip markdown code fences if present."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        # Find the first newline after ```
        first_nl = text.find("\n")
        if first_nl > 0:
            text = text[first_nl:]
        # Remove trailing ```
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return text


def validate_output(config):
    """Basic validation before writing. Returns list of errors."""
    from genre import validate as full_validate
    try:
        full_validate(config)
        return []
    except ValueError as e:
        return [str(e)]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Initialize genre configuration for the novel pipeline")
    parser.add_argument("--genre", default=os.environ.get("AUTONOVEL_GENRE", ""),
                        help="Genre description (e.g., 'Cyberpunk Noir', 'High School Romance')")
    parser.add_argument("--chapters", default=os.environ.get("AUTONOVEL_CHAPTERS", "24"),
                        help="Number of chapters (or 'short story', 'novella', 'epic 40-chapter saga')")
    parser.add_argument("--notes", default=os.environ.get("AUTONOVEL_NOTES", ""),
                        help="User's specific ideas: character names, plot twists, Chekhov's guns")
    args = parser.parse_args()

    if not args.genre:
        print("ERROR: No genre specified. Use --genre or set AUTONOVEL_GENRE env var.", file=sys.stderr)
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY", ""):
        print("ERROR: Set ANTHROPIC_API_KEY in .env first", file=sys.stderr)
        sys.exit(1)

    # Parse chapter count
    chapter_count_raw = args.chapters.strip().lower()
    try:
        chapter_count = int(chapter_count_raw)
    except ValueError:
        # Parse descriptive length
        if "short" in chapter_count_raw or "story" in chapter_count_raw:
            chapter_count = 8
        elif "novella" in chapter_count_raw or "novelette" in chapter_count_raw:
            chapter_count = 14
        elif "epic" in chapter_count_raw or "saga" in chapter_count_raw:
            # Try to extract number
            import re as re2
            nums = re2.findall(r'\d+', chapter_count_raw)
            chapter_count = int(nums[0]) if nums else 40
        else:
            print(f"WARNING: Could not parse chapter count '{args.chapters}', defaulting to 24", file=sys.stderr)
            chapter_count = 24

    estimated_words = chapter_count * 3200

    # Build user directives block
    if args.notes:
        user_block = f"\n=== USER DIRECTIVES ===\nThe user has provided specific ideas for this novel:\n{args.notes}\n\nYou MUST incorporate these into the generation descriptions, character focus_areas, and outline.notes so the pipeline preserves them."
        user_field = args.notes
    else:
        user_block = ""
        user_field = ""

    # Build the meta-prompt
    prompt = META_PROMPT
    prompt = prompt.replace("{genre_description}", args.genre)
    prompt = prompt.replace("{chapter_count}", str(chapter_count))
    prompt = prompt.replace("{estimated_words}", str(estimated_words))
    prompt = prompt.replace("{user_directives_block}", user_block)

    print(f"Generating genre config for: {args.genre} ({chapter_count} chapters, {estimated_words:,} words)...", file=sys.stderr)
    if args.notes:
        print(f"User notes: {args.notes}", file=sys.stderr)

    # Try up to 3 times
    for attempt in range(3):
        print(f"  Attempt {attempt + 1}...", file=sys.stderr)
        raw = call_llm(prompt, max_tokens=16000)
        cleaned = strip_json_fences(raw)

        try:
            config = json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}", file=sys.stderr)
            if attempt < 2:
                print(f"  Raw output (first 500 chars): {raw[:500]}", file=sys.stderr)
                continue
            else:
                print(f"  Failed after 3 attempts. Raw output saved to /tmp/genre_fail.json", file=sys.stderr)
                Path("/tmp/genre_fail.json").write_text(raw)
                sys.exit(1)

        # Inject user directives and correct chapter count
        config["user_directives"] = user_field
        if "generation" in config and "outline" in config["generation"]:
            config["generation"]["outline"]["estimated_chapters"] = chapter_count
            config["generation"]["outline"]["estimated_words"] = estimated_words

        # Validate
        errors = validate_output(config)
        if errors:
            print(f"  Validation errors:", file=sys.stderr)
            for e in errors:
                print(f"    - {e}", file=sys.stderr)
            if attempt < 2:
                # Feed error back to LLM
                prompt += f"\n\n=== FEEDBACK (attempt {attempt + 1}) ===\nThe previous output had these validation errors:\n" + "\n".join(errors) + "\nPlease fix these and output the corrected JSON."
                continue
            else:
                print(f"  Failed after 3 validation attempts.", file=sys.stderr)
                Path("/tmp/genre_fail.json").write_text(json.dumps(config, indent=2))
                sys.exit(1)

        # Success — write active_genre.json
        out_path = BASE_DIR / "active_genre.json"
        out_path.write_text(json.dumps(config, indent=2))
        print(f"✅ Genre config written to {out_path}", file=sys.stderr)
        print(f"   Genre: {config['genre_name']}")
        print(f"   Chapters: {chapter_count}, ~{estimated_words:,} words")
        print(f"   Foundation dims: {[d['key'] for d in config['evaluation']['foundation']['dimensions']]}")
        print(f"   Chapter dims: {[d['key'] for d in config['evaluation']['chapter']['dimensions']]}")
        return

    print("ERROR: Failed to generate valid genre config", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
