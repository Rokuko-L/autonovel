#!/usr/bin/env python3
"""Regression tests for the foundation plateau detector.

Bug being guarded: the keep/discard check used score >= best_score, so a TIE
reset foundation_stall_count. A judge returning identical 6.0 every iteration
(the exact motivating case for plateau detection) looped forever. The decision
now lives in pipeline_infra.foundation_plateau with strict improvement, and
these tests simulate full iteration sequences through it.

Run: uv run python -m unittest scratch.test_scoring_guards
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_infra import (
    FOUNDATION_PLATEAU_ITERS,
    foundation_plateau,
)


def run_foundation_loop(scores, start_best=0.0, threshold=7.5):
    """Simulate the run_foundation keep/discard/exit logic offline."""
    best, stall = start_best, 0
    for i, score in enumerate(scores, 1):
        keep, best, stall = foundation_plateau(score, best, stall)
        if best >= threshold:
            return f"passed@{i}"
        if stall >= FOUNDATION_PLATEAU_ITERS:
            return f"plateau@{i}"
    return "exhausted"


class PlateauDetectorTest(unittest.TestCase):
    def test_tie_is_a_stall(self):
        keep, best, stall = foundation_plateau(6.0, 6.0, 0)
        self.assertFalse(keep)
        self.assertEqual(best, 6.0)
        self.assertEqual(stall, 1)

    def test_strict_improvement_resets_stall(self):
        keep, best, stall = foundation_plateau(6.5, 6.0, 2)
        self.assertTrue(keep)
        self.assertEqual(best, 6.5)
        self.assertEqual(stall, 0)

    def test_decrease_discards_and_stalls(self):
        keep, best, stall = foundation_plateau(5.5, 6.0, 1)
        self.assertFalse(keep)
        self.assertEqual(best, 6.0)
        self.assertEqual(stall, 2)

    def test_flat_scores_exit_early(self):
        """The motivating bug: identical 6.0 across 5 iterations must hit the
        plateau exit instead of burning all iterations."""
        self.assertEqual(run_foundation_loop([6.0] * 5), "plateau@4")

    def test_flat_scores_from_resume_state(self):
        """Same, starting from a prior best (resume mid-run)."""
        self.assertEqual(run_foundation_loop([6.0] * 5, start_best=6.0),
                         "plateau@3")

    def test_decrease_then_ties_accumulate(self):
        """A discard followed by ties accumulates stalls into an exit."""
        self.assertEqual(run_foundation_loop([6.5, 6.0, 6.0, 6.0]), "plateau@4")

    def test_real_progress_passes_threshold(self):
        self.assertEqual(
            run_foundation_loop([6.0, 6.8, 7.0, 7.6]), "passed@4")

    def test_improving_scores_never_plateau(self):
        self.assertEqual(run_foundation_loop([5.0 + 0.1 * i for i in range(10)]),
                         "exhausted")


if __name__ == "__main__":
    unittest.main()
