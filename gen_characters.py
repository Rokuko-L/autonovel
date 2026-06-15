#!/usr/bin/env python3
"""
One-shot characters.md generator for foundation phase.
Reads seed.txt + voice.md + world.md + CRAFT.md, calls writer model.
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
    seed_path = utils.get_seed_path()
    world_path = utils.get_world_path()
    voice_path = utils.get_voice_path()

    for name, p in [("seed.txt", seed_path), ("world.md", world_path), ("voice.md", voice_path)]:
        if not p.exists():
            print(f"ERROR: {name} not found at {p}", file=sys.stderr)
            sys.exit(1)

    seed = seed_path.read_text()
    world = world_path.read_text()
    voice = voice_path.read_text()

    voice_lines = voice.split('\n')
    part2_start = next(i for i, l in enumerate(voice_lines) if 'Part 2' in l)
    voice_part2 = '\n'.join(voice_lines[part2_start:])

    genre = load_genre()
    prompt = format_prompt(genre["generation"]["gen_characters_prompt"], seed=seed, world=world, voice_part2=voice_part2)

    print("Calling writer model...", file=sys.stderr)
    result = call_writer(prompt)
    utils.get_characters_path().write_text(result, encoding="utf-8")
    print(result)

if __name__ == "__main__":
    main()