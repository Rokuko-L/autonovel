#!/usr/bin/env python3
"""
Generate canon.md by extracting all hard facts from world.md + characters.md.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import utils
from utils import call_anthropic, get_max_tokens_with_thinking, format_prompt
from genre import load_genre

load_dotenv()

def call_writer(prompt, max_tokens=get_max_tokens_with_thinking(16000)):
    return call_anthropic(prompt=prompt, model_key="writer", max_tokens=max_tokens, timeout=300)

FOUNDATION_CANON_PROMPT = """Extract baseline canon facts from the seed concept, world bible, and character registry below. These facts are true from the start of the story but have not yet been revealed to any reader. Output structured facts only. Do not repeat world-building verbatim; extract only what a writer needs to track as immutable truth: character relationships, hidden backstory, magic system rules, faction alignments, secret histories, key locations, and their significance.

Seed: {seed}

World Bible:
{world}

Character Registry:
{characters}

Output the canon facts as a structured list."""


def main():
    required = {
        "world.md": utils.get_world_path(),
        "characters.md": utils.get_characters_path(),
        "seed.txt": utils.get_seed_path(),
    }
    for name, p in required.items():
        if not p.exists():
            print(f"ERROR: {name} not found at {p}", file=sys.stderr)
            sys.exit(1)

    world = required["world.md"].read_text(encoding="utf-8")
    characters = required["characters.md"].read_text(encoding="utf-8")
    seed = required["seed.txt"].read_text(encoding="utf-8")

    prompt = FOUNDATION_CANON_PROMPT.format(seed=seed, world=world, characters=characters)

    print("Calling writer model...", file=sys.stderr)
    for attempt in range(2):
        result = call_writer(prompt)
        try:
            utils.validate_generator_output(result, "gen_canon.py", min_len=100, expected_headers=None)
            break
        except RuntimeError as e:
            if attempt == 0:
                print(f"  WARN: {e}, retrying...", file=sys.stderr)
            else:
                raise

    result = "## Foundation (background truth, not yet revealed to readers)\n\n" + result
    utils.get_canon_path().write_text(result, encoding="utf-8")
    print(result)

if __name__ == "__main__":
    main()