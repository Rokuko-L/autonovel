#!/usr/bin/env python3
"""
Generate canon.md by extracting all hard facts from world.md + characters.md.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from utils import call_anthropic, BASE_DIR, get_max_tokens_with_thinking
from genre import load_genre

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def call_writer(prompt, max_tokens=get_max_tokens_with_thinking(16000)):
    return call_anthropic(prompt=prompt, model_key="writer", max_tokens=max_tokens, timeout=300)

def main():
    required = {
        "world.md": BASE_DIR / "world.md",
        "characters.md": BASE_DIR / "characters.md",
        "seed.txt": BASE_DIR / "seed.txt",
    }
    for name, p in required.items():
        if not p.exists():
            print(f"ERROR: {name} not found at {p}", file=sys.stderr)
            sys.exit(1)

    world = required["world.md"].read_text()
    characters = required["characters.md"].read_text()
    seed = required["seed.txt"].read_text()

    genre_cfg = load_genre()
    prompt = genre_cfg["generation"]["gen_canon_prompt"].format(
        seed=seed, world=world, characters=characters
    )

    print("Calling writer model...", file=sys.stderr)
    result = call_writer(prompt)
    (BASE_DIR / "canon.md").write_text(result, encoding="utf-8")
    print(result)

if __name__ == "__main__":
    main()