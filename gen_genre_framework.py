#!/usr/bin/env python3
"""
gen_genre_framework.py — Step 0: Initialize genre configuration.
Reads genre description + chapter count + user notes, calls LLM with meta-prompt,
validates output, writes active_genre.json.
"""

import os
import re
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Load env
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

# Import utils for thinking token handling
from utils import extract_text_from_response, get_max_tokens_with_thinking, call_anthropic


# Shared system prompt (handles identity and mapping/translation table)
SYSTEM_PROMPT = """You are an expert literary theorist and narrative designer configuring
an AI novel-writing pipeline for ANY genre.

When mapping genre concepts, use this translation table:

Fantasy concept       →  Your genre equivalent
────────────────────────────────────────────
Magic system          →  Core genre-specific system (social rules, infection, corruption, technology)
Worldbuilding lore    →  Setting depth (school culture, city atmosphere, survival geography)
Magic costs           →  Costs of the core activity (social, moral, resource)
Bestiary / Flora      →  What's unique about this world's creatures/dangers
Factions & Politics   →  Power groups relevant to this genre
History / Timeline    →  Backstory that creates PRESENT-DAY tensions
Sensory geography     →  Locations with specific sensory signatures
Magic system rules    →  Hard rules of the core system (with costs and limitations)
Lore interconnection →  How all setting elements affect each other

Output ONLY valid JSON. No markdown fences, no preamble, no explanatory text."""


PASS1_META_PROMPT = """=== USER INPUT ===
Genre: {genre_description}
Target length: {chapter_count} chapters (~{estimated_words} words, ~{words_per_chapter} words/chapter)
{user_directives_block}

=== YOUR TASK ===
Generate the structural genre configuration as valid JSON. Do not write any generation prompt templates, focus areas, sections, or instructions. Generate only these fields:

1. "genre_name": "str — name of the genre"
2. "identity": {{
     "seed_system": "str — system prompt for seed generator",
     "world_system": "str — system prompt for world bible generator",
     "character_system": "str — system prompt for character designer",
     "outline_system": "str — system prompt for outline generator",
     "chapter_system": "str — system prompt for chapter drafter",
     "revision_system": "str — system prompt for revision writer",
     "canon_system": "str — system prompt for canon extractor",
     "evaluator_system": "str — must start with 'You are a literary critic and novel editor.'"
   }}
3. "evaluation": {{
     "foundation": {{
       "overall_calibration": "str — overall foundation calibration",
       "dimensions": [
         {{"key": "world_depth", "weight": 0.25, "criteria": "str"}},
         {{"key": "character_depth", "weight": 0.25, "criteria": "str"}},
         {{"key": "plot_structure", "weight": 0.15, "criteria": "str"}},
         {{"key": "internal_consistency", "weight": 0.1, "criteria": "str"}},
         {{"key": "voice_clarity", "weight": 0.15, "criteria": "str"}},
         {{"key": "canon_coverage", "weight": 0.1, "criteria": "str"}}
       ]
     }},
     "chapter": {{
       "overall_calibration": "str — overall chapter calibration",
       "dimensions": [
         {{"key": "voice_adherence", "weight": 0.2, "criteria": "str"}},
         {{"key": "beat_coverage", "weight": 0.15, "criteria": "str"}},
         {{"key": "character_voice", "weight": 0.2, "criteria": "str"}},
         {{"key": "prose_quality", "weight": 0.2, "criteria": "str"}},
         {{"key": "engagement", "weight": 0.15, "criteria": "str"}},
         {{"key": "continuity", "weight": 0.1, "criteria": "str"}}
       ]
     }},
     "reader_panel": {{
       "genre_reader_identity": "str — system prompt for reader panel",
       "prompt_modifications": {{
         "earned_ending_hint": "str",
         "extra_questions": {{}}
       }}
     }}
   }}
4. "framework": {{
     "lore_priorities": "str",
     "stability_trap_applies": true,
     "character_framework": "str",
     "plot_framework": "str"
   }}

=== RULES ===
- Dimension KEYS in evaluation are FIXED (world_depth, character_depth, plot_structure, internal_consistency, voice_clarity, canon_coverage, and voice_adherence, beat_coverage, character_voice, prose_quality, engagement, continuity).
- Dimension weights must sum to 1.0 (allow ±0.02).
- Criteria strings must be specific and actionable (30+ characters).
- evaluator_system must start with "You are a literary critic and novel editor."
"""


PASS2_META_PROMPT = """=== STRUCTURAL CONFIGURATION ===
{genre_config}

=== USER INPUT ===
Genre: {genre_description}
Target length: {chapter_count} chapters (~{estimated_words} words, ~{words_per_chapter} words/chapter)
{user_directives_block}

=== YOUR TASK ===
Generate the complete content generation configuration block ("generation") as valid JSON, including prompts, world bibles structure, character registry structure, and chapter instructions. You must generate:

1. "generation": {{
     "world": {{ "description": "...", "sections": ["list of section headers"] }},
     "character": {{ "description": "...", "focus_areas": ["list of focus areas"] }},
     "outline": {{ "description": "...", "estimated_chapters": {chapter_count}, "estimated_words": {estimated_words}, "notes": ["structural notes"] }},
     "seed_generate_prompt": "...",
     "seed_riff_prompt": "...",
     "gen_world_prompt": "...",
     "gen_characters_prompt": "...",
     "gen_outline_prompt": "...",
     "gen_outline_part2_prompt": "...",
     "gen_canon_prompt": "...",
     "draft_chapter_instructions": "...",
     "anti_pattern_rules": "...",
     "canon_categories": ["list of category headers"],
     "arc_summary_premise": "..."
   }}

=== RULES ===
- Prompt strings must be substantial (100+ characters).
- Prompts MUST use the template parameters as required (using either single braces like {{placeholder}} or double braces like {{{{placeholder}}}}). Specifically:
  * "gen_world_prompt" MUST contain: {{seed}} AND {{voice_part2}}
  * "gen_characters_prompt" MUST contain: {{seed}} AND {{world}} AND {{voice_part2}}
  * "gen_outline_prompt" MUST contain: {{seed}} AND {{world}} AND {{characters}} AND {{voice_part2}}
  * "gen_outline_part2_prompt" MUST contain: {{part1}}
  * "gen_canon_prompt" MUST contain: {{seed}} AND {{world}} AND {{characters}}
- "gen_outline_prompt" and "gen_outline_part2_prompt" MUST explicitly instruct the outline writer to generate a unique, evocative, and thematic chapter title for every single chapter (e.g., in the format "Chapter N: Title") instead of using generic titles like "Chapter N".
- "draft_chapter_instructions" MUST instruct the writer to start the chapter markdown file with a top-level header including both the chapter number and the specific title from the outline (e.g., "# Chapter N: [Title]").
- "draft_chapter_instructions" must weave in a firm requirement that each chapter is approximately {words_per_chapter} words.
- All section headers and focus areas must align directly with what the prompt templates require.

"""


def strip_json_fences(text):
    """Strip markdown code fences if present."""
    text = text.strip()
    match = re.match(r'^```(?:json)?\s*\n(.*?)\n```\s*$', text, re.DOTALL)
    return match.group(1).strip() if match else text


REQUIRED_PLACEHOLDERS = {
    "gen_world_prompt":          ["{seed}", "{voice_part2}"],
    "gen_characters_prompt":     ["{seed}", "{world}", "{voice_part2}"],
    "gen_outline_prompt":        ["{seed}", "{world}", "{characters}", "{voice_part2}"],
    "gen_outline_part2_prompt":  ["{part1}"],
    "gen_canon_prompt":          ["{seed}", "{world}", "{characters}"],
}


def validate_placeholders(config):
    """Check that generated prompt strings contain their required placeholders."""
    errors = []
    generation = config.get("generation", {})
    for field, required in REQUIRED_PLACEHOLDERS.items():
        prompt_str = generation.get(field, "")
        for placeholder in required:
            # LLM writes {{seed}} (double-brace), which becomes {seed} after escaping
            if placeholder not in prompt_str and placeholder.replace("{", "{{").replace("}", "}}") not in prompt_str:
                errors.append(f"generation.{field} is missing required placeholder '{placeholder}'")
    return errors


def validate_output(config):
    """Basic validation before writing. Returns list of errors."""
    from genre import validate as full_validate
    errors = []
    try:
        full_validate(config)
    except ValueError as e:
        errors.append(str(e))
    errors.extend(validate_placeholders(config))
    return errors


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Initialize genre configuration for the novel pipeline")
    parser.add_argument("--genre", default=os.environ.get("AUTONOVEL_GENRE", ""),
                        help="Genre description (e.g., 'Cyberpunk Noir', 'High School Romance')")
    parser.add_argument("--chapters", default=os.environ.get("AUTONOVEL_CHAPTERS", "24"),
                        help="Number of chapters (or 'short story', 'novella', 'epic 40-chapter saga')")
    parser.add_argument("--words-per-chapter", type=int, default=3200,
                        help="Target word count per chapter (default: 3200)")
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

    estimated_words = chapter_count * args.words_per_chapter

    # Build user directives block
    if args.notes:
        user_block = f"\n=== USER DIRECTIVES ===\nThe user has provided specific ideas for this novel:\n{args.notes}\n\nYou MUST incorporate these into the generation descriptions, character focus_areas, and outline.notes so the pipeline preserves them."
        user_field = args.notes
    else:
        user_block = ""
        user_field = ""

    print(f"Generating genre config for: {args.genre} ({chapter_count} chapters, {estimated_words:,} words)...", file=sys.stderr)
    if args.notes:
        print(f"User notes: {args.notes}", file=sys.stderr)

    # ==========================================
    # PASS 1: Generate structural config
    # ==========================================
    pass1_prompt = PASS1_META_PROMPT.format(
        genre_description=args.genre,
        chapter_count=chapter_count,
        estimated_words=estimated_words,
        words_per_chapter=args.words_per_chapter,
        user_directives_block=user_block
    )

    config1 = None
    print(f"Executing Pass 1 (Structural Design)...", file=sys.stderr)
    for attempt in range(3):
        print(f"  Pass 1 Attempt {attempt + 1}...", file=sys.stderr)
        raw1 = call_anthropic(
            prompt=pass1_prompt,
            system=SYSTEM_PROMPT,
            model_key="judge",  # Premium model for Pass 1
            max_tokens=16000,
            temperature=0.7,
            timeout=300
        )
        cleaned1 = strip_json_fences(raw1)
        try:
            config1 = json.loads(cleaned1)
            
            # Structural validate
            errors = []
            for key in ["genre_name", "identity", "evaluation", "framework"]:
                if key not in config1:
                    errors.append(f"Missing top-level key: {key}")
            if errors:
                raise ValueError("Structural keys missing: " + ", ".join(errors))
            
            # Temporary full validate check with mock generation block
            temp_config = dict(config1)
            temp_config["generation"] = {
                "world": {"description": "temp world building bible description", "sections": []},
                "character": {"description": "temp character description", "focus_areas": []},
                "outline": {"description": "temp outline", "estimated_chapters": chapter_count, "estimated_words": estimated_words, "notes": []},
                "seed_generate_prompt": "temp template with at least fifty characters in length to pass validations",
                "seed_riff_prompt": "temp template with at least fifty characters in length to pass validations",
                "gen_world_prompt": "temp template with at least fifty characters in length to pass validations",
                "gen_characters_prompt": "temp template with at least fifty characters in length to pass validations",
                "gen_outline_prompt": "temp template with at least fifty characters in length to pass validations",
                "gen_outline_part2_prompt": "temp template with at least fifty characters in length to pass validations",
                "gen_canon_prompt": "temp template with at least fifty characters in length to pass validations",
                "draft_chapter_instructions": "temp template with at least fifty characters in length to pass validations",
                "anti_pattern_rules": "temp template with at least fifty characters in length to pass validations",
                "canon_categories": [],
                "arc_summary_premise": "temp template with at least fifty characters in length to pass validations"
            }
            from genre import validate as full_validate
            full_validate(temp_config)
            
            print("  Pass 1 successful.", file=sys.stderr)
            break
        except Exception as e:
            print(f"  Pass 1 error: {e}", file=sys.stderr)
            if attempt < 2:
                # Add validation error feedback
                pass1_prompt += f"\n\n=== FEEDBACK (attempt {attempt + 1}) ===\nThe previous output had this error: {e}\nPlease fix this and output valid JSON matching the schema rules."
            else:
                print(f"  Failed after 3 attempts. Raw output saved to {BASE_DIR / 'genre_fail.json'}", file=sys.stderr)
                (BASE_DIR / "genre_fail.json").write_text(raw1)
                sys.exit(1)

    # ==========================================
    # PASS 2: Generate prompts & generation config
    # ==========================================
    pass2_prompt = PASS2_META_PROMPT.format(
        genre_config=json.dumps(config1, indent=2),
        genre_description=args.genre,
        chapter_count=chapter_count,
        estimated_words=estimated_words,
        words_per_chapter=args.words_per_chapter,
        user_directives_block=user_block
    )

    config2 = None
    print(f"Executing Pass 2 (Content Generation & Prompts)...", file=sys.stderr)
    for attempt in range(3):
        print(f"  Pass 2 Attempt {attempt + 1}...", file=sys.stderr)
        raw2 = call_anthropic(
            prompt=pass2_prompt,
            system=SYSTEM_PROMPT,
            model_key="writer",  # Creative writer model for prompt templates
            max_tokens=16000,
            temperature=0.7,
            timeout=300
        )
        cleaned2 = strip_json_fences(raw2)
        try:
            config2 = json.loads(cleaned2)
            
            # Explicit key check for generation
            if "generation" not in config2:
                raise ValueError("Pass 2 output missing top-level 'generation' key")
            
            # Merge Pass 2 generation into Pass 1 structure
            merged_config = dict(config1)
            merged_config["generation"] = config2["generation"]
            merged_config["user_directives"] = user_field

            # Correct chapter counts and estimated words
            if "outline" in merged_config["generation"]:
                merged_config["generation"]["outline"]["estimated_chapters"] = chapter_count
                merged_config["generation"]["outline"]["estimated_words"] = estimated_words

            # Run full validation including placeholder checks
            errors = validate_output(merged_config)
            if errors:
                raise ValueError("\n".join(errors))

            config1 = merged_config
            print("  Pass 2 successful.", file=sys.stderr)
            break
        except Exception as e:
            print(f"  Pass 2 error: {e}", file=sys.stderr)
            if attempt < 2:
                # Add validation error feedback
                pass2_prompt += f"\n\n=== FEEDBACK (attempt {attempt + 1}) ===\nThe previous output had these errors: {e}\nPlease fix these and output valid JSON matching the schema rules."
            else:
                print(f"  Failed after 3 attempts. Raw output saved to {BASE_DIR / 'genre_fail.json'}", file=sys.stderr)
                (BASE_DIR / "genre_fail.json").write_text(raw2)
                sys.exit(1)

    # Success — write active_genre.json
    import utils
    out_path = utils.get_active_genre_path()
    out_path.write_text(json.dumps(config1, indent=2))
    print(f"✅ Genre config written to {out_path}", file=sys.stderr)
    print(f"   Genre: {config1['genre_name']}")
    print(f"   Chapters: {chapter_count}, ~{estimated_words:,} words")
    print(f"   Foundation dims: {[d['key'] for d in config1['evaluation']['foundation']['dimensions']]}")
    print(f"   Chapter dims: {[d['key'] for d in config1['evaluation']['chapter']['dimensions']]}")


if __name__ == "__main__":
    main()
