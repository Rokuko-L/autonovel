#!/usr/bin/env python3
"""Facade over the split utility modules.

Historically this file was a 1600-line monolith. It is now split by concern:

  paths.py      -- project root/state resolution, folder + file path helpers,
                   prompt loader, registry atomic writes
  llm.py        -- Anthropic client, response extraction, JSON repair
  outline.py    -- outline text ops: chapter headings, premise beats,
                   plants/harvests validation, debts
  textstats.py  -- context windows, repetition detection
  novel_tex.py  -- default LaTeX template generation

Every pipeline script does `import utils` or `from utils import X`, so this
facade re-exports all public names to keep every call site working. New code
should import from the specific module instead.
"""

from paths import *  # noqa: F401,F403
from paths import BASE_DIR  # noqa: F401  (backward-compat constant)

from llm import *  # noqa: F401,F403
from outline import *  # noqa: F401,F403
from textstats import *  # noqa: F401,F403
from novel_tex import generate_default_novel_tex  # noqa: F401
