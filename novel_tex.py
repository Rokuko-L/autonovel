"""Default LaTeX novel.tex template generation."""

import re
from pathlib import Path

from paths import get_seed_path, get_novel_title


def generate_default_novel_tex(dest_path: Path):
    """Generate a default novel.tex wrapper template for LaTeX typesetting."""
    seed_path = get_seed_path()

    # Try to extract title from state.json (pipeline stores the real title here)
    title = "A Novel"
    try:
        state_title = get_novel_title()
        if state_title and state_title.lower() not in ("a novel", "the novel", "untitled"):
            title = state_title
    except Exception:
        pass
    if title == "A Novel":
        # Fallback to seed.txt first line
        if seed_path.exists():
            try:
                with open(seed_path, encoding="utf-8") as f:
                    first_line = f.readline()
                    if first_line.startswith("#"):
                        title = first_line.lstrip("#").strip()
            except Exception:
                pass

    # Try to resolve author name from git config
    author = "Author Name"
    try:
        import subprocess
        author = subprocess.check_output(["git", "config", "user.name"], text=True).strip()
    except Exception:
        pass

    # Basic clean formatting
    title_escaped = title.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")
    author_escaped = author.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")

    # Load epigraph if theme exists
    epigraph_block = ""
    if seed_path.exists():
        try:
            import re
            content = seed_path.read_text(encoding="utf-8")
            # Look for thematic core paragraph
            match = re.search(r"##\s*Thematic\s*Core\s*\n\n(.*?)(?:\n\n|\Z)", content, re.DOTALL | re.IGNORECASE)
            if match:
                theme_text = match.group(1).strip()
                # Split lines for poetry-like typesetting in epigraph
                theme_lines = theme_text.split(". ")
                theme_lines_tex = "\\\\\n  ".join(line.strip() + "." if not line.endswith(".") else line.strip() for line in theme_lines if line.strip())
                epigraph_block = f"""% === EPIGRAPH ===
\\newcommand{{\\makeepigraph}}{{%
  \\thispagestyle{{empty}}
  \\vspace*{{2.5in}}
  \\begin{{center}}
  \\begin{{minipage}}{{3in}}
  \\begin{{center}}
  \\itshape
  {theme_lines_tex}\\\\[12pt]
  \\end{{center}}
  \\end{{minipage}}
  \\end{{center}}
  \\clearpage
}}"""
        except Exception:
            pass

    # If no epigraph was extracted, create a simple empty one
    if not epigraph_block:
        epigraph_block = """% === EPIGRAPH ===
\\newcommand{\\makeepigraph}{%
  \\thispagestyle{empty}
  \\clearpage
}"""

    # Generate standard template content
    template = f"""\\documentclass[11pt, openany]{{book}}

% === GEOMETRY: Trade paperback (5.5 x 8.5 inches) ===
\\usepackage[
  paperwidth=5.5in,
  paperheight=8.5in,
  inner=0.85in,
  outer=0.65in,
  top=0.75in,
  bottom=0.85in,
  headheight=14pt
]{{geometry}}

% === FONTS ===
\\usepackage{{fontspec}}
\\setmainfont{{EBGaramond}}[
  UprightFont = EBGaramond-Regular,
  ItalicFont  = EBGaramond-Italic,
  BoldFont    = EBGaramond-Regular,
  BoldItalicFont = EBGaramond-Italic,
]

% === TYPOGRAPHY ===
\\usepackage{{microtype}}
\\usepackage{{setspace}}
\\setstretch{{1.12}}
\\usepackage{{parskip}}
\\setlength{{\\parindent}}{{1.5em}}
\\setlength{{\\parskip}}{{0pt}}

% === GRAPHICS ===
\\usepackage{{graphicx}}

% === DROP CAPS ===
\\usepackage{{lettrine}}
\\setcounter{{DefaultLines}}{{2}}

% === HEADERS AND FOOTERS ===
\\usepackage{{fancyhdr}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\fancyhead[LE]{{\\small\\textsc{{{title_escaped.lower()}}}}}
\\fancyhead[RO]{{\\small\\textit{{\\leftmark}}}}
\\fancyfoot[C]{{\\thepage}}
\\renewcommand{{\\headrulewidth}}{{0pt}}

\\fancypagestyle{{plain}}{{
  \\fancyhf{{}}
  \\fancyfoot[C]{{\\thepage}}
  \\renewcommand{{\\headrulewidth}}{{0pt}}
}}

% === CHAPTER STYLE ===
\\usepackage{{titlesec}}

% Ornamental bell motif (using dingbats)
\\newcommand{{\\bellornament}}{{%
  \\par\\noindent\\vspace{{6pt}}%
  \\hfill{{\\large\\symbol{{"2756}}}}\\hfill\\null%
  \\vspace{{6pt}}\\par%
}}

% Scene break ornament
\\newcommand{{\\scenebreak}}{{%
  \\par\\vspace{{0.6\\baselineskip}}%
  \\noindent\\hfil%
  \\IfFileExists{{../art/pdf/scene_break.pdf}}{{%
    \\includegraphics[width=1.2in]{{../art/pdf/scene_break.pdf}}%
  }}{{%
  \\IfFileExists{{../art/scene_break.png}}{{%
    \\includegraphics[width=1.2in]{{../art/scene_break.png}}%
  }}{{%
    {{\\small\\symbol{{"2022}}\\quad\\symbol{{"2022}}\\quad\\symbol{{"2022}}}}%
  }}}}%
  \\hfil%
  \\par\\vspace{{0.6\\baselineskip}}%
}}

\\renewcommand{{\\thechapter}}{{\\Roman{{chapter}}}}
\\titleformat{{\\chapter}}[display]
  {{\\normalfont\\centering}}
  {{\\vspace*{{1.5in}}\\footnotesize\\textsc{{chapter \\thechapter}}}}
  {{4pt}}
  {{\\Large\\itshape}}
  [\\vspace{{8pt}}{{\\small--- $\\diamond$ ---}}\\vspace{{0.5in}}]

\\titlespacing*{{\\chapter}}{{0pt}}{{0pt}}{{0pt}}

% Lowercase chapter name in header
\\renewcommand{{\\chaptermark}}[1]{{\\markboth{{#1}}{{}}}}

% === TITLE PAGE DESIGN ===
\\newcommand{{\\makenoveltitle}}{{%
  \\thispagestyle{{empty}}
  \\begin{{center}}
  \\vspace*{{2in}}
  
  {{\\Huge\\textsc{{{title_escaped}}}}}\\\\[0.4in]
  
  {{\\small------\\quad$\\diamond$\\quad------}}\\\\[0.5in]
  
  {{\\large\\textit{{A Novel}}}}\\\\[1in]
  
  {{\\Large\\textsc{{{author_escaped}}}}}\\\\[1.5in]
  
  \\end{{center}}
  \\clearpage
}}

{epigraph_block}

% === HALF TITLE ===
\\newcommand{{\\makehalftitle}}{{%
  \\thispagestyle{{empty}}
  \\vspace*{{3in}}
  \\begin{{center}}
  {{\\large\\textsc{{{title_escaped}}}}}
  \\end{{center}}
  \\clearpage
}}

% === PDF METADATA ===
\\usepackage{{hyperref}}
\\hypersetup{{
  pdftitle={{{title_escaped}}},
  pdfauthor={{{author_escaped}}},
  hidelinks
}}

% === BEGIN DOCUMENT ===
\\begin{{document}}

\\frontmatter

% Full-bleed cover image (if exists)
\\IfFileExists{{../art/cover.png}}{{%
  \\thispagestyle{{empty}}
  \\newgeometry{{margin=0pt}}
  \\noindent\\includegraphics[width=\\paperwidth, height=\\paperheight, keepaspectratio]{{../art/cover.png}}%
  \\restoregeometry%
  \\clearpage%
}}{{}}

% Half title
\\makehalftitle

% Blank verso
\\thispagestyle{{empty}}
\\mbox{{}}
\\clearpage

% Title page
\\makenoveltitle

% Copyright / colophon
\\thispagestyle{{empty}}
\\vspace*{{\\fill}}
\\begin{{center}}

{{\\small This is a work of fiction.}}\\\\[18pt]

\\end{{center}}
\\vspace*{{\\fill}}
\\clearpage

% Epigraph
\\makeepigraph

% Blank verso before main text
\\thispagestyle{{empty}}
\\mbox{{}}
\\clearpage

\\mainmatter

% === CHAPTERS ===
\\input{{chapters_content.tex}}

% === END MATTER ===
\\backmatter

\\thispagestyle{{empty}}
\\vspace*{{3in}}
\\begin{{center}}
{{\\small------\\quad$\\diamond$\\quad------}}\\\\[0.3in]
{{\\small\\textit{{The page turned.}}}}
\\end{{center}}

\\end{{document}}
"""
    dest_path.write_text(template, encoding="utf-8")
