#!/usr/bin/env python3
"""
gen_novel_tex.py — Generate a custom novel.tex via LLM.
Calls the writer model with project context, outputs a designed LaTeX template.

Usage: uv run python gen_novel_tex.py
       uv run python gen_novel_tex.py --project brothersister
"""

import re
import sys
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

import utils
from utils import call_anthropic, get_novel_title

load_dotenv()

ROOT = Path(__file__).resolve().parent


def load_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def extract_thematic_core(seed_text: str) -> str:
    """Extract the ## Thematic Core section from seed.txt."""
    m = re.search(
        r"##\s*Thematic\s*Core\s*\n\n(.*?)(?:\n\n##\s|\Z)",
        seed_text, re.DOTALL | re.IGNORECASE
    )
    if m:
        return m.group(1).strip()
    # fallback: look for any standalone paragraph that reads like a theme
    lines = [l.strip() for l in seed_text.split('\n') if l.strip()]
    for line in lines:
        if line.startswith('"') and line.count('.') > 1:
            return line
    return ""


def extract_title(seed_text: str, state: dict) -> str:
    """Extract title from seed.txt first line or state.json."""
    title = state.get("title", "")
    if title and title.lower() not in ("a novel", "the novel", "untitled"):
        return title
    first_line = seed_text.strip().split('\n')[0] if seed_text.strip() else ""
    if first_line.startswith("#"):
        return first_line.lstrip("#").strip()
    return utils.get_project_name().replace("_", " ").title()


def get_author() -> str:
    """Get author name from git config."""
    try:
        return subprocess.check_output(
            ["git", "config", "user.name"], text=True
        ).strip()
    except Exception:
        return "Author Name"


def get_genre_summary(genre_cfg: dict) -> str:
    """Extract a readable summary of the genre configuration."""
    parts = []
    name = genre_cfg.get("genre_name", "Unknown")
    parts.append(f"Genre: {name}")
    identity = genre_cfg.get("identity", {})
    for key in ("chapter_system", "world_system"):
        val = identity.get(key, "")
        if val:
            parts.append(f"{key}: {val[:200]}")
    framework = genre_cfg.get("framework", {})
    for key in ("lore_priorities",):
        val = framework.get(key, "")
        if val:
            parts.append(f"{key}: {val[:200]}")
    user_notes = genre_cfg.get("user_directives", "")
    if user_notes:
        parts.append(f"User notes: {user_notes[:300]}")
    return "\n\n".join(parts)


def extract_voice_part2(voice_text: str) -> str:
    """Extract everything after the Part 2 header."""
    idx = voice_text.find("## Part 2:")
    if idx == -1:
        idx = voice_text.find("## Part 2 ")
    if idx == -1:
        return ""
    return voice_text[idx:]


def build_prompt(
    title: str,
    author: str,
    genre_summary: str,
    voice_part2: str,
    thematic_core: str,
    seed_text: str,
    char_text: str,
    world_text: str,
    voice_text: str,
) -> str:
    """Build the full prompt for the LLM."""

    parts = []

    # Title block
    parts.append(f"TITLE: {title}")
    parts.append(f"AUTHOR: {author}")

    # Genre block
    parts.append(f"\nGENRE CONFIGURATION:\n{genre_summary}")

    # Voice block
    if voice_part2.strip() and "<!-- Generated" not in voice_part2:
        parts.append(f"\nVOICE IDENTITY (novel's tone and POV):\n{voice_part2[:1500]}")
    else:
        parts.append(f"\nVOICE IDENTITY:\n(No voice identity filled yet for this novel.)")

    # Thematic core
    if thematic_core:
        parts.append(f"\nTHEMATIC CORE (use for epigraph and design inspiration):\n{thematic_core}")

    # World flavor (brief)
    if world_text:
        short_world = world_text[:800]
        parts.append(f"\nWORLD FLAVOR:\n{short_world}")

    # Characters (brief)
    if char_text:
        short_char = char_text[:600]
        parts.append(f"\nCHARACTERS:\n{short_char}")

    # Seed premise
    if seed_text:
        short_seed = seed_text[:1000]
        parts.append(f"\nSTORY PREMISE:\n{short_seed}")

    return "\n\n".join(parts)


SYSTEM_PROMPT = """You are a professional book designer and LaTeX expert.
Given a novel's metadata and creative context, generate a complete novel.tex
file that produces a beautifully typeset PDF book.

DESIGN GUIDELINES BY GENRE:
- Dark fantasy / horror: heavier serif fonts, dark ornamental chapter decorations, restrained elegance
- Light novel / isekai: cleaner lines, playful chapter headings, lighter feel
- Political drama / literary: classical restrained typography, minimal ornamentation
- Romance: warm, slightly decorative, elegant but not cold
- Sci-fi / cyberpunk: geometric, slightly asymmetric, tech-influenced ornamentation
- Comedy: playful chapter headings, slightly looser layout

RULES (non-negotiable — must follow exactly):
1. Must compile with tectonic. Use \\usepackage{ebgaramond} for the font (do NOT use fontspec).
2. Do NOT load fontspec — the ebgaramond package handles font loading.
3. Use \\usepackage[a5paper, inner=0.85in, outer=0.65in, top=0.75in, bottom=0.85in, headheight=14pt]{geometry}
   Do NOT use manual \\setlength for page dimensions.
4. Must load these packages (in any order): graphicx, ebgaramond, geometry, titlesec, fancyhdr, lettrine, hyperref, setspace, microtype, xcolor, amssymb, tikz
5. Must define ALL of these commands with NO arguments (zero arguments):
   \\newcommand{\\scenebreak}{...}
   \\newcommand{\\makenoveltitle}{...}
   \\newcommand{\\makeepigraph}{...}
   \\newcommand{\\makehalftitle}{...}
6. \\makeepigraph must contain the epigraph TEXT inside its definition (not take arguments).
7. Must include \\input{chapters_content.tex} inside \\mainmatter
8. Frontmatter order: half title -> blank verso -> title page -> colophon -> epigraph -> blank verso
9. Backmatter: end ornament + closing line
10. Use \\leftmark for chapter titles in headers (fancyhdr), NOT \\thechapter.
11. Use \\MakeUppercase or plain text in chapter headings. Do NOT use \\MakeTextUppercase.
12. Colophon must include only the author name (nothing else).
13. When using decorative math symbols (stars, arrows, card suits like \spadesuit, \clubsuit, \diamondsuit, \heartsuit, etc.) in chapter headings, ornaments, or text, they MUST be wrapped in math mode (e.g., \(\spadesuit\) or \(\diamondsuit\) or $\clubsuit$). Do NOT use them in raw text mode. Only use standard symbols from amssymb or basic LaTeX, and do NOT use non-standard variations or prefixes (e.g. do NOT use \varspadesuit, \varclubsuit, \vardiamondsuit, \varheartsuit).
14. The title from context is the EXACT novel title — use it as the primary heading on the title page and half-title page. Never replace it with "A Novel", "A NOVEL", or any placeholder text. Never relegate it to a subtitle.
15. Do NOT invoke the standard LaTeX `\maketitle` command anywhere in the document body. Since custom commands are defined and used for the title pages, calling `\maketitle` will crash compilation due to missing standard title declarations.

CREATIVE FREEDOM (you decide):
- Title page layout: multi-line, decorative, thematic — match the novel's tone
- Title and author come from the context — use them exactly
- Chapter heading style: via \\titleformat — font size, shape, ornament
- Header/footer content and style
- Epigraph formatting: matching the thematic core
- Ornament symbols and spacing
- Color palette via xcolor that fits the genre
- PDF metadata: title, author, subject keywords from genre

Output ONLY valid LaTeX code inside ```latex ... ``` fences."""

PROMPT_TEMPLATE = """Generate a novel.tex for this novel:

{context}

Use the genre, voice, and premise to design the typography, title page, chapter headings, and overall layout. Every design choice should feel intentional for THIS novel, not generic. Output the complete file inside ```latex ... ```."""


def main():
    # Parse optional --project flag
    if "--project" in sys.argv:
        idx = sys.argv.index("--project")
        if idx + 1 < len(sys.argv):
            project_name = sys.argv[idx + 1]
            utils.set_project_name(project_name)

    # Load project context
    seed_text = load_file(utils.get_seed_path())
    voice_text = load_file(utils.get_voice_path())
    world_text = load_file(utils.get_world_path())
    char_text = load_file(utils.get_characters_path())

    state = {}
    try:
        state = json.loads(load_file(utils.get_state_path()))
    except (json.JSONDecodeError, ValueError):
        pass

    genre_cfg = {}
    try:
        genre_cfg = json.loads(load_file(utils.get_active_genre_path()))
    except (json.JSONDecodeError, ValueError):
        pass

    title = extract_title(seed_text, state)
    author = get_author()
    genre_summary = get_genre_summary(genre_cfg)
    voice_part2 = extract_voice_part2(voice_text)
    thematic_core = extract_thematic_core(seed_text)

    context = build_prompt(
        title=title,
        author=author,
        genre_summary=genre_summary,
        voice_part2=voice_part2,
        thematic_core=thematic_core,
        seed_text=seed_text,
        char_text=char_text,
        world_text=world_text,
        voice_text=voice_text,
    )

    prompt = PROMPT_TEMPLATE.format(context=context)

    print(f"Generating novel.tex for: {title}", file=sys.stderr)
    print(f"  Author: {author}", file=sys.stderr)
    print(f"  Context size: {len(context)} chars", file=sys.stderr)

    # Write to typeset directory
    typeset_dir = utils.get_typeset_dir()
    dest = typeset_dir / "novel.tex"

    # Call LLM
    raw = call_anthropic(
        prompt=prompt,
        system=SYSTEM_PROMPT,
        model_key="writer",
        max_tokens=16000,
        temperature=0.7,
        timeout=300,
    )

    # Extract LaTeX from code fences
    latex = raw.strip()
    m = re.search(r"```(?:latex|tex)?\s*\n(.*?)```", raw, re.DOTALL)
    if m:
        latex = m.group(1).strip()
    else:
        # Try to find \documentclass as anchor
        m2 = re.search(r"(\\documentclass[^]*?\\end\{document\})", raw, re.DOTALL)
        if m2:
            latex = m2.group(1).strip()

    if not latex or len(latex) < 200:
        print(f"ERROR: LLM returned invalid LaTeX (fence extraction produced {len(latex)} chars)", file=sys.stderr)
        sys.exit(1)

    dest.write_text(latex, encoding="utf-8")
    print(f"Wrote novel.tex ({len(latex)} bytes) to {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()
