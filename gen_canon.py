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

    genre_cfg = load_genre()
    prompt = format_prompt(
        genre_cfg["generation"]["gen_canon_prompt"],
        seed=seed, world=world, characters=characters
    )

    print("Calling writer model...", file=sys.stderr)
    result = call_writer(prompt)
    utils.get_canon_path().write_text(result, encoding="utf-8")
    print(result)

if __name__ == "__main__":
    main()