#!/usr/bin/env python3
"""Targeted mechanical-slop repair for a single chapter.

When a chapter's raw judge score is good but the mechanical slop detector
(staccato runs, "not X but Y", stacked negation, x_of_y frames, etc.) drags
the final score below the keep bar, blind regeneration wastes attempts and
often regresses content quality. Instead, repair IN PLACE:

1. Detect flagged paragraphs + the exact offending phrases, with line numbers.
2. Wrap each flagged paragraph in unique markers (<<<SLOP_N>>> ... <<</SLOP_N>>>)
   and ask the LLM to rewrite ONLY the marked paragraphs, keeping markers intact.
3. Verify every marker survives the round trip (guards against the LLM
   dropping or merging paragraphs).
4. Mechanically splice the cleaned paragraphs back into the chapter.
5. Run evaluate.py --chapter=N so the pipeline can re-judge the repair.

Usage: python repair_slop.py <chapter_number>
Exit code 0 = repair applied (caller should re-evaluate); 1 = nothing to repair
or LLM output invalid (caller falls back to regeneration).
"""
import re
import sys
from pathlib import Path

import _utf8
import utils
from evaluate import (
    PROSE_TIC_PATTERNS,
    FICTION_AI_TELLS,
    STRUCTURAL_AI_TICS,
    TIER1_BANNED,
    TIER2_SUSPICIOUS,
    TIER3_FILLER,
    TRANSITION_OPENERS,
)

OPEN, CLOSE = "<<<SLOP_{i}>>>", "<<</SLOP_{i}>>>"

ALL_PATTERNS = (
    [("prose_tic", name, pat) for name, pat in PROSE_TIC_PATTERNS]
    + [("fiction_tell", f"fiction#{k}", pat) for k, pat in enumerate(FICTION_AI_TELLS)]
    + [("structural_tic", f"structural#{k}", pat) for k, pat in enumerate(STRUCTURAL_AI_TICS)]
    + [("tier3", f"tier3#{k}", pat) for k, pat in enumerate(TIER3_FILLER)]
)


def split_paragraphs(text: str):
    """Return list of (start_line_1based, end_line_1based_inclusive, para_text)."""
    lines = text.split("\n")
    paras = []
    cur_start = None
    buf = []
    for i, line in enumerate(lines):
        if line.strip():
            if cur_start is None:
                cur_start = i + 1
            buf.append(line)
        else:
            if cur_start is not None:
                paras.append((cur_start, i, "\n".join(buf)))
                cur_start = None
                buf = []
    if cur_start is not None:
        paras.append((cur_start, len(lines), "\n".join(buf)))
    return paras


def scan_paragraph(para_text: str):
    """Return list of (pattern_label, matched_phrase) found in a paragraph."""
    hits = []
    for label, name, pattern in ALL_PATTERNS:
        for m in re.finditer(pattern, para_text, re.IGNORECASE):
            snippet = para_text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
            hits.append((f"{label}:{name}", snippet.strip()))
    for w in TIER1_BANNED:
        if re.search(rf"\b{re.escape(w)}\b", para_text, re.IGNORECASE):
            hits.append(("tier1", w))
    for w in TIER2_SUSPICIOUS:
        if re.search(rf"\b{re.escape(w)}\b", para_text, re.IGNORECASE):
            hits.append(("tier2", w))
    return hits


def staccato_paragraph(para_text: str) -> int:
    """Count staccato runs (3+ consecutive sentences <=4 words) in a paragraph."""
    para_clean = para_text.replace("...", " ").replace("..", " ")
    sents = [s.strip() for s in re.split(r"[.!?]+", para_clean) if any(c.isalnum() for c in s)]
    runs = 0
    run = 0
    for s in sents:
        if len(s.split()) <= 4:
            run += 1
        else:
            if run >= 3:
                runs += run - 2
            run = 0
    if run >= 3:
        runs += run - 2
    return runs


def transition_opener_paragraph(para_text: str) -> bool:
    first = para_text.split()[0].lower().strip(".,;:!?\"'()") if para_text.split() else ""
    return first in TRANSITION_OPENERS


def build_repair_prompt(flagged: list, chapter_num: int, title_line: str) -> str:
    blocks = []
    for i, (start_line, _, para_text, reasons) in enumerate(flagged, start=1):
        reason_lines = "\n".join(f"  - {lab}: '{ph}'" for lab, ph in reasons[:6])
        if not reason_lines:
            reason_lines = "  - mechanical pattern (see paragraph)"
        blocks.append(
            f"{OPEN.format(i=i)} (original lines {start_line}-?)\n"
            f"{para_text}\n"
            f"{CLOSE.format(i=i)}\n"
            f"REASONS (lines {start_line}):\n{reason_lines}"
        )
    return f"""You are a surgical prose editor. Rewrite the following paragraphs from Chapter {chapter_num} ("{title_line}") of a novel to remove the listed mechanical AI-slop patterns.

HARD RULES:
- Rewrite ONLY the text between each pair of markers (<<<SLOP_N>>> ... <<</SLOP_N>>>).
- Do NOT add, remove, reorder, rename, or merge the markers. Every marker must appear EXACTLY once, in the SAME order, in your output.
- Preserve the meaning, the scene content, the emotional register, the characters, dialogue, and roughly the same length. Tighten where the pattern demanded it.
- Convert banned constructions to natural, varied prose (positive statements instead of stacked negation; concrete detail instead of 'the X of Y' frames; break staccato runs by merging or expanding).
- Do NOT change anything else in the chapter. Only output the marked paragraphs, one marker block after another.

MARKED PARAGRAPHS:
{chr(10).join(blocks)}
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python repair_slop.py <chapter_number>", file=sys.stderr)
        sys.exit(1)
    chapter_num = int(sys.argv[1])

    chapters_dir = utils.get_chapters_dir()
    ch_path = chapters_dir / f"ch_{chapter_num:02d}.md"
    if not ch_path.exists():
        print(f"ERROR: {ch_path} not found", file=sys.stderr)
        sys.exit(1)
    text = ch_path.read_text(encoding="utf-8")
    title_line = text.strip().split("\n")[0].lstrip("#* ").strip()

    paragraphs = split_paragraphs(text)
    flagged = []
    for start_line, end_line, para_text in paragraphs:
        if start_line == 1 and para_text.lstrip().startswith("#"):
            continue  # markdown title header, not prose
        hits = scan_paragraph(para_text)
        stacc = staccato_paragraph(para_text)
        trans = transition_opener_paragraph(para_text)
        reasons = []
        if stacc >= 1:
            reasons.append((f"staccato_runs:{stacc}", f"{stacc} run(s) of 3+ consecutive short sentences"))
        if trans:
            reasons.append(("transition_opener", "paragraph starts with a transition word"))
        reasons += hits
        if reasons:
            flagged.append((start_line, end_line, para_text, reasons))

    if not flagged:
        print(f"NO_SLOP Chapter {chapter_num} — nothing to repair", file=sys.stderr)
        sys.exit(1)

    print(f"REPAIR Chapter {chapter_num}: {len(flagged)} flagged paragraph(s)", file=sys.stderr)
    for start_line, _, _, reasons in flagged:
        labels = ", ".join(lab for lab, _ in reasons[:4])
        print(f"  lines {start_line}: {labels}", file=sys.stderr)

    prompt = build_repair_prompt(flagged, chapter_num, title_line)
    raw = utils.call_anthropic(
        prompt=prompt,
        model_key="writer",
        max_tokens=6000,
        temperature=0.6,
        timeout=300,
    )
    if not raw or len(raw.strip()) < 50:
        print("REPAIR_FAILED empty LLM response", file=sys.stderr)
        sys.exit(1)

    # Verify every marker is intact, exactly once, in order
    n = len(flagged)
    opens = re.findall(OPEN.replace("{i}", r"(\d+)"), raw)
    closes = re.findall(CLOSE.replace("{i}", r"(\d+)"), raw)
    if [int(x) for x in opens] != list(range(1, n + 1)) or [int(x) for x in closes] != list(range(1, n + 1)):
        print(f"REPAIR_FAILED marker mismatch — opens={opens} closes={closes}", file=sys.stderr)
        sys.exit(1)

    # Extract repaired blocks keyed by index
    repaired = {}
    for i in range(1, n + 1):
        o = re.search(OPEN.format(i=i) + r"\n(.*?)\n" + CLOSE.format(i=i), raw, re.DOTALL)
        if not o:
            print(f"REPAIR_FAILED cannot extract block {i}", file=sys.stderr)
            sys.exit(1)
        repaired[i] = o.group(1).strip()

    # Splice back mechanically: replace each flagged paragraph's line range
    lines = text.split("\n")
    for idx, (start_line, end_line, para_text, _) in enumerate(flagged, start=1):
        new_text = repaired[idx]
        # Keep paragraph spacing consistent: same leading/trailing blanks
        lines[start_line - 1:end_line] = new_text.split("\n")

    ch_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"REPAIRED Chapter {chapter_num}: {n} paragraph(s) rewritten in place", file=sys.stderr)
    print(f"Word count: {len(('\\n'.join(lines)).split())}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
