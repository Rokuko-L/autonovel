#!/usr/bin/env python3
"""Static analysis gate: ruff pyflakes rules over the whole repo.

Catches the bug class the import-integrity scanner can't: names USED but
never imported (F821) — e.g. process_notes() calling call_llm with no
import, which only NameErrors when that code path first runs. Also flags
accidental redefinitions (F811).

Run: uv run python -m unittest scratch.test_static_analysis
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class StaticAnalysisTest(unittest.TestCase):
    def test_ruff_pyflakes_clean(self):
        cmd = [
            sys.executable, "-m", "ruff", "check", ".",
            "--select", "F821,F811",
            "--no-cache",
            "--output-format", "concise",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(
            proc.returncode, 0,
            f"ruff found undefined/redefined names:\n{proc.stdout}\n{proc.stderr}"
        )


if __name__ == "__main__":
    unittest.main()
