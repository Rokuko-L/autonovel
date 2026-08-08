#!/usr/bin/env python3
"""
One-shot world.md generator for foundation phase.
Reads seed.txt + voice.md, calls the writer model, outputs world.md content.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import utils
from utils import call_anthropic, get_max_tokens_with_thinking, format_prompt, TruncationError
from genre import load_genre

load_dotenv()

def call_writer(prompt, max_tokens=get_max_tokens_with_thinking(16000)):
    return call_anthropic(prompt=prompt, model_key="writer", max_tokens=max_tokens, timeout=300)

def main():
    seed_path = utils.get_seed_path()
    voice_path = utils.get_voice_path()
    craft_path = utils.get_root_dir() / "CRAFT.md"

    if not seed_path.exists():
        print(f"ERROR: seed.txt not found at {seed_path}", file=sys.stderr)
        sys.exit(1)
    if not voice_path.exists():
        print(f"ERROR: voice.md not found at {voice_path}", file=sys.stderr)
        sys.exit(1)
    if not craft_path.exists():
        print(f"ERROR: CRAFT.md not found at {craft_path}", file=sys.stderr)
        sys.exit(1)

    seed = seed_path.read_text()
    voice = voice_path.read_text()
    craft = craft_path.read_text()

    voice_lines = voice.split('\n')
    part2_start = next(i for i, l in enumerate(voice_lines) if 'Part 2' in l)
    voice_part2 = '\n'.join(voice_lines[part2_start:])

    genre = load_genre()
    perspective_line = ""
    perspective = genre.get("perspective", "")
    if perspective == "first_person":
        perspective_line = ("MANDATORY PERSPECTIVE: The novel is FIRST-PERSON. The world bible must "
                            "state Kaelen narrates in first-person 'I/me/my'. Do not describe the "
                            "narration as third-person or limited-third.")
    elif perspective == "third_person":
        perspective_line = ("MANDATORY PERSPECTIVE: The novel is THIRD-PERSON (close limited). The "
                            "world bible must state the narration stays in the POV character's head.")
    prompt = format_prompt(genre["generation"]["gen_world_prompt"], seed=seed, voice_part2=voice_part2)
    if perspective_line:
        prompt = f"{perspective_line}\n\n{prompt}"

    print("Calling writer model...", file=sys.stderr)
    for attempt in range(2):
        try:
            result = call_writer(prompt)
        except TruncationError as e:
            print(f"  WARN: {e}, retrying...", file=sys.stderr)
            continue
        try:
            utils.validate_generator_output(result, "gen_world.py", min_len=500, expected_headers=["# ", "## "])
            break
        except RuntimeError as e:
            if attempt == 0:
                print(f"  WARN: {e}, retrying...", file=sys.stderr)
            else:
                raise
    utils.get_world_path().write_text(result, encoding="utf-8")
    print(result)

if __name__ == "__main__":
    main()