#!/usr/bin/env python3
"""
One-shot world.md generator for foundation phase.
Reads seed.txt + voice.md, calls the writer model, outputs world.md content.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from utils import call_anthropic, get_max_tokens_with_thinking
from genre import load_genre

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def call_writer(prompt, max_tokens=get_max_tokens_with_thinking(16000)):
    return call_anthropic(prompt=prompt, model_key="writer", max_tokens=max_tokens, timeout=300)

def main():
    seed_path = BASE_DIR / "seed.txt"
    voice_path = BASE_DIR / "voice.md"
    craft_path = BASE_DIR / "CRAFT.md"

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
    prompt = genre["generation"]["gen_world_prompt"].format(seed=seed, voice_part2=voice_part2)

    print("Calling writer model...", file=sys.stderr)
    result = call_writer(prompt)
    (BASE_DIR / "world.md").write_text(result, encoding="utf-8")
    print(result)

if __name__ == "__main__":
    main()