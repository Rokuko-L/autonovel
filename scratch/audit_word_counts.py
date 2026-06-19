import argparse
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Audit word count history for a project")
    parser.add_argument("--project", default="serious", help="Project name (under projects/)")
    args = parser.parse_args()

    cwd = Path("projects") / args.project
    if not cwd.exists():
        print(f"Error: Project directory {cwd} does not exist.")
        return
    chapters = sorted((cwd / "chapters").glob("ch_*.md"))
    
    print("Chapter word count history audit:")
    print("==================================")
    
    for ch_path in chapters:
        ch_name = ch_path.name
        # Get all commits modifying this file
        try:
            commits = subprocess.check_output(
                ["git", "log", "--format=%H", "--", f"chapters/{ch_name}"],
                cwd=str(cwd)
            ).decode("utf-8").strip().splitlines()
        except subprocess.CalledProcessError as e:
            print(f"Failed to get git log for {ch_name}: {e}")
            continue
            
        commits.reverse()  # chronological order
        
        history = []
        for c in commits:
            try:
                content = subprocess.check_output(
                    ["git", f"show", f"{c}:chapters/{ch_name}"],
                    cwd=str(cwd)
                ).decode("utf-8", errors="ignore")
                # Remove BOM if present
                content = content.lstrip("\ufeff")
                wc = len(content.split())
                
                # Retrieve commit description/subject
                subject = subprocess.check_output(
                    ["git", "log", "-1", "--format=%s", c],
                    cwd=str(cwd)
                ).decode("utf-8").strip()
                
                history.append((c[:7], wc, subject))
            except Exception as e:
                continue
        
        # Check if there is a downward trend or significant decline
        print(f"\n{ch_name} (Current: {len(ch_path.read_text(encoding='utf-8', errors='ignore').split())} words):")
        for c_abbrev, wc, subject in history:
            print(f"  {c_abbrev}: {wc:4d} words | {subject}")
            
if __name__ == "__main__":
    main()
