#!/usr/bin/env python3
"""
test_path_contamination.py — Verifies no pipeline files leak to root.

Mocks all LLM calls via unittest.mock.patch on utils.call_anthropic.
Runs path helpers in isolation and asserts zero new files appear in the
root codebase directory (outside of projects/).

Run with: python scratch/test_path_contamination.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import utils

PASS = "[PASS]"
FAIL = "[FAIL]"
_failed = []


def check(label, condition, detail=""):
    if condition:
        print(f"  {PASS} {label}")
    else:
        msg = f"  {FAIL} {label}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        _failed.append(label)


def snapshot_root(root: Path, exclude: set = None) -> set:
    """
    Recursively collect all paths under root, excluding specified subdirs.
    Returns a set of relative path strings.
    """
    exclude = exclude or set()
    result = set()
    for item in root.rglob("*"):
        try:
            rel = item.relative_to(root)
        except ValueError:
            continue
        parts = rel.parts
        if parts and parts[0] in exclude:
            continue
        result.add(str(rel))
    return result


def test_no_root_contamination(tmp_root: Path, project_name: str = "contamination_test"):
    """
    After a mock pipeline run, zero new files should exist in tmp_root
    outside of the projects/ and .git/ directories.
    """
    orig_root = utils._root_dir
    orig_name = utils._project_name
    utils._root_dir = tmp_root
    utils.set_project_name(project_name)

    # Snapshot root BEFORE
    before = snapshot_root(tmp_root, exclude={"projects", ".git"})

    # Simulate path helpers being called (as they would be during a pipeline run)
    chapters_dir = utils.get_chapters_dir()
    edit_logs_dir = utils.get_edit_logs_dir()
    eval_logs_dir = utils.get_eval_logs_dir()
    briefs_dir = utils.get_briefs_dir()
    typeset_dir = utils.get_typeset_dir()

    # Simulate writing project files
    (chapters_dir / "ch_01.md").write_text("# Chapter 1\n\nContent.", encoding="utf-8")
    (edit_logs_dir / "ch01_cuts.json").write_text('{"cuts": []}', encoding="utf-8")
    (eval_logs_dir / "20250101_foundation.json").write_text('{"overall_score": 8.0}', encoding="utf-8")
    (briefs_dir / "ch01_panel.md").write_text("# Brief\n\nDetails.", encoding="utf-8")
    utils.get_outline_path().write_text("# Outline", encoding="utf-8")
    utils.get_state_path().write_text('{"phase": "foundation"}', encoding="utf-8")
    utils.get_world_path().write_text("# World", encoding="utf-8")
    utils.get_reviews_path().write_text("# Review", encoding="utf-8")

    # Snapshot root AFTER, excluding projects/ and .git/
    after = snapshot_root(tmp_root, exclude={"projects", ".git"})

    new_files = after - before
    check("no new files in root (outside projects/)", len(new_files) == 0,
          f"Leaked files: {new_files}")

    # Verify files ARE in projects/ subdirectory
    proj_dir = utils.get_project_dir()
    check("project dir is inside projects/",
          str(proj_dir).startswith(str(tmp_root / "projects")))
    check("chapter file is inside project dir",
          (chapters_dir / "ch_01.md").exists())
    check("project dir is relative to root/projects",
          proj_dir.is_relative_to(tmp_root / "projects"))

    # Restore
    utils._root_dir = orig_root
    utils._project_name = orig_name


def test_two_projects_no_cross_contamination(tmp_root: Path):
    """Files from project A should not appear in project B's directory."""
    orig_root = utils._root_dir
    orig_name = utils._project_name
    utils._root_dir = tmp_root

    try:
        # Set up project A
        utils.set_project_name("project_a")
        ch_a = utils.get_chapters_dir()
        (ch_a / "ch_01.md").write_text("# Alpha Chapter 1", encoding="utf-8")
        (ch_a / "ch_02.md").write_text("# Alpha Chapter 2", encoding="utf-8")

        # Set up project B
        utils.set_project_name("project_b")
        ch_b = utils.get_chapters_dir()
        ch_b.mkdir(parents=True, exist_ok=True)

        # Project B's chapters dir should not contain project A's files
        b_files = list(ch_b.glob("ch_*.md"))
        check("project B chapters dir is empty (no A contamination)",
              len(b_files) == 0, f"Found: {b_files}")

        # Project A's world.md should not be visible from B
        utils.set_project_name("project_a")
        utils.get_world_path().write_text("# Alpha World", encoding="utf-8")

        utils.set_project_name("project_b")
        b_world = utils.get_world_path()
        check("project B world.md does not exist (no A contamination)",
              not b_world.exists(), str(b_world))

    finally:
        utils._root_dir = orig_root
        utils._project_name = orig_name


def test_mock_call_anthropic():
    """utils.call_anthropic can be patched via unittest.mock.patch."""
    with patch("utils.call_anthropic", return_value="mocked LLM response") as mock_fn:
        result = utils.call_anthropic("test prompt")
        check("call_anthropic patchable via mock.patch", result == "mocked LLM response")
        check("mock was called once", mock_fn.call_count == 1)


def test_registry_path_is_in_projects():
    """Registry path should always resolve inside projects/, never at root."""
    orig_root = utils._root_dir
    with tempfile.TemporaryDirectory(prefix="autonovel_reg_") as tmp:
        tmp_root = Path(tmp)
        utils._root_dir = tmp_root
        (tmp_root / ".env").write_text("ANTHROPIC_API_KEY=test")
        reg_path = utils.get_registry_path()
        check("registry is under projects/",
              str(reg_path).startswith(str(tmp_root / "projects")),
              str(reg_path))
    utils._root_dir = orig_root


def main():
    print("\n=== test_path_contamination.py ===\n")

    with tempfile.TemporaryDirectory(prefix="autonovel_cont_") as tmp:
        tmp_root = Path(tmp)
        # Minimal project root marker
        (tmp_root / "pyproject.toml").write_text("[tool.autonovel]")

        print("1. No root contamination after mock pipeline run:")
        test_no_root_contamination(tmp_root)

        print("\n2. Two-project cross-contamination check:")
        test_two_projects_no_cross_contamination(tmp_root)

    print("\n3. LLM call patchability:")
    test_mock_call_anthropic()

    print("\n4. Registry path isolation:")
    test_registry_path_is_in_projects()

    print()
    if _failed:
        print(f"\033[91mFAILED {len(_failed)} checks:\033[0m")
        for f in _failed:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("\033[92mAll checks passed.\033[0m")


if __name__ == "__main__":
    main()
