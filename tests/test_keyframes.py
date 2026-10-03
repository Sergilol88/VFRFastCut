# SPDX-License-Identifier: MIT

import unittest

from vfr_keyframes import (
    resolve_preview_playback_position,
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


class EditedPreviewRangeTests(unittest.TestCase):
    def setUp(self):
        self.ranges = [(0.0, 10.0), (20.0, 30.0), (40.0, 50.0)]

    def test_position_inside_kept_range_continues_without_jump(self):
        index, target = resolve_preview_playback_position(self.ranges, 24.0)
        self.assertEqual(index, 1)
        self.assertIsNone(target)

    def test_position_in_deleted_gap_jumps_to_next_kept_range(self):
        index, target = resolve_preview_playback_position(self.ranges, 15.0)
        self.assertEqual(index, -1)
        self.assertEqual(target, 20.0)

    def test_position_before_first_kept_range_jumps_to_first_range(self):
        ranges = [(5.0, 10.0), (20.0, 30.0)]
        index, target = resolve_preview_playback_position(ranges, 1.0)
        self.assertEqual(index, -1)
        self.assertEqual(target, 5.0)

    def test_range_end_is_treated_as_removed_gap(self):
        index, target = resolve_preview_playback_position(self.ranges, 10.0)
        self.assertEqual(index, -1)
        self.assertEqual(target, 20.0)

    def test_after_last_kept_range_has_no_future_target(self):
        index, target = resolve_preview_playback_position(self.ranges, 55.0)
        self.assertEqual(index, -1)
        self.assertIsNone(target)

    def test_all_deleted_has_no_target(self):
        index, target = resolve_preview_playback_position([], 3.0)
        self.assertEqual(index, -1)
        self.assertIsNone(target)


if __name__ == "__main__":
    unittest.main()
