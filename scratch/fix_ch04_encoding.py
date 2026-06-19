import subprocess
import sys
from pathlib import Path

def main():
    cwd = Path("projects/serious")
    target_path = cwd / "chapters" / "ch_04.md"
    
    print("Retrieving chapters/ch_04.md directly from git commit 40622cd...")
    try:
        # Run git show and capture raw bytes
        raw_bytes = subprocess.check_output(
            ["git", "show", "40622cd:chapters/ch_04.md"],
            cwd=str(cwd),
            stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e.stderr.decode('utf-8', errors='ignore')}")
        sys.exit(1)
        
    print(f"Read {len(raw_bytes)} bytes from git")
    
    # Decode as UTF-8
    try:
        text = raw_bytes.decode("utf-8")
        print("Successfully decoded as UTF-8")
    except UnicodeDecodeError as e:
        print(f"Failed to decode git output as UTF-8: {e}")
        sys.exit(1)
        
    # Strip BOM if present
    text = text.lstrip("\ufeff")
    
    # Write back to disk as clean UTF-8
    target_path.write_text(text, encoding="utf-8")
    
    word_count = len(text.split())
    print(f"Re-saved {target_path} as clean UTF-8 ({word_count} words)")

if __name__ == "__main__":
    main()
