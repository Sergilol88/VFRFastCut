# SPDX-License-Identifier: MIT

import unittest

from vfr_keyframes import (
    TimestampRepairProbeError,
    analyze_video_timestamps,
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


class TimestampRepairTests(unittest.TestCase):
    def setUp(self):
        self.stream_60 = {
            "r_frame_rate": "60/1",
            "avg_frame_rate": "60/1",
        }

    @staticmethod
    def _packets(pts_values, dts_values):
        return [
            {"pts_time": str(pts), "dts_time": str(dts)}
            for pts, dts in zip(pts_values, dts_values)
        ]

    def test_matroska_style_dts_equal_pts_is_repaired(self):
        pts = [0.000, 0.050, 0.017, 0.033, 0.100, 0.067, 0.083]
        plan = analyze_video_timestamps(
            self.stream_60,
            self._packets(pts, pts),
        )
        self.assertTrue(plan.required)
        self.assertGreater(plan.dts_regressions, 0)
        self.assertEqual(plan.frame_rate_expr, "60/1")
        self.assertEqual(plan.guard_frames, 2)
        self.assertEqual(
            plan.filter_spec,
            "setts=pts=PTS:dts=(N-2)/((60/1)*TB)",
        )

    def test_valid_b_frame_dts_are_left_untouched(self):
        pts = [0.000, 0.050, 0.017, 0.033, 0.100, 0.067, 0.083]
        dts = [-0.033, -0.017, 0.000, 0.017, 0.033, 0.050, 0.067]
        plan = analyze_video_timestamps(
            self.stream_60,
            self._packets(pts, dts),
        )
        self.assertFalse(plan.required)
        self.assertEqual(plan.dts_regressions, 0)
        self.assertGreater(plan.pts_regressions, 0)
        self.assertEqual(plan.filter_spec, "")

    def test_monotonic_video_is_left_untouched(self):
        pts = [0.000, 0.017, 0.033, 0.050]
        plan = analyze_video_timestamps(
            self.stream_60,
            self._packets(pts, pts),
        )
        self.assertFalse(plan.required)

    def test_absurd_nominal_rate_falls_back_to_average_rate(self):
        stream = {
            "r_frame_rate": "1000/1",
            "avg_frame_rate": "60/1",
        }
        pts = [0.000, 0.050, 0.017, 0.033, 0.100, 0.067, 0.083]
        plan = analyze_video_timestamps(
            stream,
            self._packets(pts, pts),
        )
        self.assertTrue(plan.required)
        self.assertEqual(plan.frame_rate_expr, "60/1")

    def test_missing_rate_uses_pts_span_fallback(self):
        pts = [0.000, 0.050, 0.017, 0.033, 0.100, 0.067, 0.083]
        plan = analyze_video_timestamps(
            {},
            self._packets(pts, pts),
        )
        self.assertTrue(plan.required)
        self.assertGreater(plan.frame_rate, 50.0)
        self.assertLess(plan.frame_rate, 70.0)

    def test_reordered_pts_without_dts_still_requests_repair(self):
        packets = [
            {"pts_time": value, "dts_time": "N/A"}
            for value in ("0.000", "0.050", "0.017", "0.033")
        ]
        plan = analyze_video_timestamps(self.stream_60, packets)
        self.assertTrue(plan.required)

    def test_unresolvable_rate_raises_only_for_broken_timestamps(self):
        packets = [
            {"pts_time": "0.0", "dts_time": "0.0"},
            {"pts_time": "-1.0", "dts_time": "-1.0"},
        ]
        with self.assertRaises(TimestampRepairProbeError):
            analyze_video_timestamps({}, packets)


if __name__ == "__main__":
    unittest.main()
