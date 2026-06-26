#!/usr/bin/env python3
"""Generate outline.md from seed + world + characters + mystery + craft."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import utils
from utils import call_anthropic, get_max_tokens_with_thinking, format_prompt
from genre import load_genre

load_dotenv()

def call_writer(prompt, max_tokens=get_max_tokens_with_thinking(16000)):
    return call_anthropic(prompt=prompt, model_key="writer", max_tokens=max_tokens, beta_context=True, timeout=600)

def main():
    root = utils.get_root_dir()
    required = {
        "seed.txt": utils.get_seed_path(),
        "world.md": utils.get_world_path(),
        "characters.md": utils.get_characters_path(),
        "MYSTERY.md": root / "MYSTERY.md",
        "CRAFT.md": root / "CRAFT.md",
        "voice.md": utils.get_voice_path(),
    }
    for name, p in required.items():
        if not p.exists():
            print(f"ERROR: {name} not found at {p}", file=sys.stderr)
            sys.exit(1)

    seed = required["seed.txt"].read_text()
    world = required["world.md"].read_text()
    characters = required["characters.md"].read_text()
    mystery = required["MYSTERY.md"].read_text()
    craft = required["CRAFT.md"].read_text()

    voice = required["voice.md"].read_text()
    voice_lines = voice.split('\n')
    part2_start = next(i for i, l in enumerate(voice_lines) if 'Part 2' in l)
    voice_part2 = '\n'.join(voice_lines[part2_start:])

    genre_cfg = load_genre()
    prompt = format_prompt(
        genre_cfg["generation"]["gen_outline_prompt"],
        seed=seed, world=world, characters=characters,
        mystery=mystery, voice_part2=voice_part2, craft=craft
    )

    print("Calling writer model...", file=sys.stderr)
    for attempt in range(2):
        result = call_writer(prompt)
        try:
            utils.validate_generator_output(result, "gen_outline.py", min_len=500, expected_headers=["# ", "### "])
            break
        except RuntimeError as e:
            if attempt == 0:
                print(f"  WARN: {e}, retrying...", file=sys.stderr)
            else:
                raise
    utils.get_outline_path().write_text(result, encoding="utf-8")
    (utils.get_project_dir() / ".outline_part1.md").write_text(result, encoding="utf-8")
    print(result)

if __name__ == "__main__":
    main()