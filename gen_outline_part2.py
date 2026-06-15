#!/usr/bin/env python3
"""Generate remaining chapters + foreshadowing ledger."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import utils
from utils import call_anthropic, get_max_tokens_with_thinking, format_prompt
from genre import load_genre

load_dotenv()

def call_writer(prompt, max_tokens=get_max_tokens_with_thinking(16000)):
    return call_anthropic(prompt=prompt, model_key="writer", max_tokens=max_tokens, timeout=600)

def main():
    root = utils.get_root_dir()
    part1_path = utils.get_project_dir() / ".outline_part1.md"
    mystery_path = root / "MYSTERY.md"

    if not part1_path.exists():
        print(f"ERROR: .outline_part1.md not found at {part1_path} — run gen_outline.py first", file=sys.stderr)
        sys.exit(1)
    if not mystery_path.exists():
        print(f"WARNING: MYSTERY.md not found at {mystery_path}, proceeding without mystery", file=sys.stderr)

    part1 = part1_path.read_text()
    mystery = mystery_path.read_text() if mystery_path.exists() else ""

    genre_cfg = load_genre()
    prompt = format_prompt(
        genre_cfg["generation"]["gen_outline_part2_prompt"],
        part1=part1, mystery=mystery
    )

    print("Calling writer model...", file=sys.stderr)
    result = call_writer(prompt)
    utils.get_outline_path().write_text(part1 + "\n\n" + result, encoding="utf-8")
    print(result)

if __name__ == "__main__":
    main()