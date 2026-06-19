import os
import sys
import re
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import utils
from utils import call_anthropic

utils.set_project_name("serious")

def get_current_chapters():
    chapters_dir = utils.get_chapters_dir()
    return sorted(chapters_dir.glob("ch_*.md"))

def generate_title(ch_num, summary):
    prompt = f"""You are the author of a political dark comedy/fantasy novel "The Baroness Problem" about Elara Voss establishing her feudal authority.
Here is the summary of Chapter {ch_num}:
{summary}

Generate a short, elegant, thematic, and witty chapter title (e.g. in the style of "The Weight of Paper", "The Arithmetic of Precedent", "The Performance", "The Document and the Sword", "The Bond", "The Charter").
Output only the title string itself, nothing else. No quotes, no markdown, no preamble."""
    response = call_anthropic(prompt=prompt, model_key="judge", max_tokens=100)
    return response.strip().strip('"').strip("'").strip()

def process_chapter_title(path, ch_num, summary, clean_title):
    new_title = generate_title(ch_num, summary)
    text = path.read_text(encoding="utf-8")
    lines = text.split('\n')
    lines[0] = f"# Chapter {ch_num}: {new_title}"
    path.write_text('\n'.join(lines), encoding="utf-8")
    print(f"Chapter {ch_num} updated: '{clean_title}' -> '{new_title}'")

def main():
    chapters = get_current_chapters()
    
    # Load outline.md to parse current summaries
    outline_path = utils.get_outline_path()
    outline_text = outline_path.read_text(encoding="utf-8")
    
    # Simple regex to extract summaries from outline
    blocks = re.split(r'### Ch \d+:', outline_text)
    summaries = {}
    for i, block in enumerate(blocks[1:], start=1):
        match = re.search(r'\*\*Summary:\*\*\s*(.*?)(?:\n\n|\Z)', block)
        if match:
            summaries[i] = match.group(1).strip()
            
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    tasks = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        for path in chapters:
            m = re.search(r"ch_(\d+)\.md", path.name)
            if not m:
                continue
            ch_num = int(m.group(1))
            
            text = path.read_text(encoding="utf-8")
            first_line = text.split('\n')[0].strip()
            
            # Check if the title is generic
            clean_title = first_line.lstrip('# ').strip()
            is_generic = False
            if clean_title.lower() in [f"chapter {ch_num}", f"chapter {ch_num}: chapter {ch_num}", "chapter twelve"]:
                is_generic = True
            elif not ":" in clean_title:
                is_generic = True
                
            if is_generic:
                summary = summaries.get(ch_num, "Elara Voss manages her barony's challenges.")
                print(f"Scheduling Chapter {ch_num} for title generation (current: '{clean_title}')...")
                tasks.append(executor.submit(process_chapter_title, path, ch_num, summary, clean_title))
                
        for future in as_completed(tasks):
            try:
                future.result()
            except Exception as e:
                print(f"Error processing chapter: {e}")
            
if __name__ == "__main__":
    main()

