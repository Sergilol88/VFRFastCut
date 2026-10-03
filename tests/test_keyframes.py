# SPDX-License-Identifier: MIT

import unittest

from vfr_keyframes import (
    snap_range_to_keyframes,
    snap_ranges_to_keyframes,
)


class KeyframeSnapTests(unittest.TestCase):
    def setUp(self):
        self.keyframes = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]
        self.duration = 10.0

    def test_range_snaps_inward_like_legacy_export(self):
        self.assertEqual(
            snap_range_to_keyframes(3.1, 8.9, self.keyframes, self.duration),
            (4.0, 8.0),
        )

    def test_project_edges_remain_exact(self):
        self.assertEqual(
            snap_range_to_keyframes(0.0, 10.0, self.keyframes, self.duration),
            (0.0, 10.0),
        )

    def test_too_small_range_disappears_after_snapping(self):
        self.assertIsNone(
            snap_range_to_keyframes(2.1, 3.9, self.keyframes, self.duration)
        )

    def test_multiple_ranges_merge_when_snapped_boundaries_touch(self):
        ranges, max_shift = snap_ranges_to_keyframes(
            [(0.0, 4.1), (3.9, 8.1)],
            self.keyframes,
            self.duration,
        )
        self.assertEqual(ranges, [(0.0, 8.0)])
        self.assertAlmostEqual(max_shift, 0.1, places=6)

    def test_unrepresentable_ranges_are_skipped(self):
        ranges, _ = snap_ranges_to_keyframes(
            [(2.1, 3.9), (4.1, 7.9)],
            self.keyframes,
            self.duration,
        )
        self.assertEqual(ranges, [])


if __name__ == "__main__":
    unittest.main()
