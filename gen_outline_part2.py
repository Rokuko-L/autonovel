#!/usr/bin/env python3
"""Generate remaining chapters + foreshadowing ledger."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from utils import call_anthropic, BASE_DIR, get_max_tokens_with_thinking
from genre import load_genre

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

def call_writer(prompt, max_tokens=get_max_tokens_with_thinking(16000)):
    return call_anthropic(prompt=prompt, model_key="writer", max_tokens=max_tokens, timeout=600)

part1 = open('/tmp/outline_output.md').read()
mystery = (BASE_DIR / "MYSTERY.md").read_text()

genre_cfg = load_genre()
prompt = genre_cfg["generation"]["gen_outline_part2_prompt"].format(
    part1=part1, mystery=mystery
)

print("Calling writer model...", file=sys.stderr)
result = call_writer(prompt)
(BASE_DIR / "outline.md").write_text(part1 + "\n\n" + result, encoding="utf-8")
print(result)
