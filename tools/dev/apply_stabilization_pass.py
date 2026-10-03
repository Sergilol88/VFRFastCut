# SPDX-License-Identifier: MIT
"""Apply low-risk 0.5.0 stabilization cleanups to vfr_fastcut.py.

This helper is intentionally narrow and idempotent.  It removes one stale Qt
import, avoids expensive keyframe-density work on zoomed-out long VODs, caches
the edited-preview deletion state, and makes preview fades use the same
effective keyframe-snapped ranges as Edited Preview/export.
"""

from __future__ import annotations

from pathlib import Path


MARKER = "self._edited_preview_has_deletions = False"
DENSITY_MARKER = "A dense viewport can be rejected without slicing"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "vfr_fastcut.py"
    if not target.is_file():
        raise RuntimeError(f"vfr_fastcut.py not found at {target}")

    text = target.read_text(encoding="utf-8")
    if (
        MARKER in text
        and DENSITY_MARKER in text
        and "    QStackedWidget,\n" not in text
    ):
        print("0.5.0 stabilization pass is already applied; nothing to do.")
        return 0

    # QStackedWidget belonged to the old in-window Export/Cancel stack and is
    # no longer referenced after the Task Progress Dialog refactor.
    text = replace_once(
        text,
        "    QStatusBar,\n    QStackedWidget,\n    QTextBrowser,\n",
        "    QStatusBar,\n    QTextBrowser,\n",
        "remove stale QStackedWidget import",
    )

    # Cache whether the edit actually contains deleted source ranges.  This is
    # read from every QMediaPlayer position update, so avoid scanning the whole
    # segment list on each frame for projects with many cuts.
    text = replace_once(
        text,
        "        self._edited_preview_ranges: list[tuple[float, float]] = []\n"
        "        self._edited_preview_ranges_exact = False\n"
        "        self._edited_preview_jump_active = False\n",
        "        self._edited_preview_ranges: list[tuple[float, float]] = []\n"
        "        self._edited_preview_ranges_exact = False\n"
        "        self._edited_preview_has_deletions = False\n"
        "        self._edited_preview_jump_active = False\n",
        "edited-preview cached deletion state",
    )

    text = replace_once(
        text,
        "        self._edited_preview_ranges.clear()\n"
        "        self._edited_preview_ranges_exact = False\n"
        "        self.selected_index = -1\n",
        "        self._edited_preview_ranges.clear()\n"
        "        self._edited_preview_ranges_exact = False\n"
        "        self._edited_preview_has_deletions = False\n"
        "        self.selected_index = -1\n",
        "clear cached deletion state",
    )

    old_preview_refresh = '''    def _refresh_edited_preview_ranges(self):
        """Rebuild playable source-time ranges for edited-result preview."""
        kept = kept_ranges_from_segments(self.segments)
        if not kept:
            self._edited_preview_ranges = []
            self._edited_preview_ranges_exact = bool(self.keyframes)
            return

        if self.keyframes and self.duration > 0:
            ranges, _max_shift = snap_ranges_to_keyframes(
                kept,
                self.keyframes,
                self.duration,
            )
            self._edited_preview_ranges = ranges
            self._edited_preview_ranges_exact = True
        else:
            # Keep preview usable while the background ffprobe scan is still
            # running (or unavailable). As soon as the map arrives this cache
            # is rebuilt with the exact export snapping rules.
            self._edited_preview_ranges = kept
            self._edited_preview_ranges_exact = False

    def _edited_preview_enabled(self) -> bool:
        return any(seg.deleted for seg in self.segments)
'''
    new_preview_refresh = '''    def _refresh_edited_preview_ranges(self):
        """Rebuild playable source-time ranges for edited-result preview."""
        self._edited_preview_has_deletions = any(
            seg.deleted for seg in self.segments
        )
        kept = kept_ranges_from_segments(self.segments)
        if not kept:
            self._edited_preview_ranges = []
            self._edited_preview_ranges_exact = bool(self.keyframes)
            return

        if self.keyframes and self.duration > 0:
            ranges, _max_shift = snap_ranges_to_keyframes(
                kept,
                self.keyframes,
                self.duration,
            )
            self._edited_preview_ranges = ranges
            self._edited_preview_ranges_exact = True
        else:
            # Keep preview usable while the background ffprobe scan is still
            # running (or unavailable). As soon as the map arrives this cache
            # is rebuilt with the exact export snapping rules.
            self._edited_preview_ranges = kept
            self._edited_preview_ranges_exact = False

    def _edited_preview_enabled(self) -> bool:
        return self._edited_preview_has_deletions
'''
    text = replace_once(
        text,
        old_preview_refresh,
        new_preview_refresh,
        "cache edited-preview deletion state",
    )

    old_preview_range = '''    def _preview_kept_range_at(
        self,
        position: float,
    ) -> Optional[tuple[float, float]]:
        for start, end in kept_ranges_from_segments(self.segments):
            if start - 0.001 <= position <= end + 0.001:
                return start, end
        return None
'''
    new_preview_range = '''    def _preview_kept_range_at(
        self,
        position: float,
    ) -> Optional[tuple[float, float]]:
        """Return the effective range used by Edited Preview and export."""
        for start, end in self._edited_preview_ranges:
            if start - 0.001 <= position <= end + 0.001:
                return start, end
        return None
'''
    text = replace_once(
        text,
        old_preview_range,
        new_preview_range,
        "reuse effective ranges for preview fades",
    )

    old_keyframe_paint = '''        if self.keyframes:
            first = bisect.bisect_left(self.keyframes, vis_start - 1e-9)
            last = bisect.bisect_right(self.keyframes, vis_end + 1e-9)

            # Include one neighbour outside each side when available.  It makes
            # the spacing estimate stable while panning near viewport edges.
            spacing_first = max(0, first - 1)
            spacing_last = min(len(self.keyframes), last + 1)
            spacing_keyframes = self.keyframes[spacing_first:spacing_last]
            visible_keyframes = self.keyframes[first:last]

            show_keyframes = bool(visible_keyframes)
            if show_keyframes and len(spacing_keyframes) > 1:
                px_per_second = width / max(0.001, self.visible_duration)
                gaps_px = sorted(
                    max(0.0, b - a) * px_per_second
                    for a, b in zip(spacing_keyframes, spacing_keyframes[1:])
                    if b > a
                )
                if gaps_px:
                    # Median spacing is robust to an occasional unusually close
                    # scene-change keyframe while still hiding a dense GOP wall.
                    representative_spacing_px = gaps_px[len(gaps_px) // 2]
                    show_keyframes = (
                        representative_spacing_px >= self.keyframe_min_spacing_px
                    )

            if show_keyframes:
                lane_top = self.RULER_H + 1
                lane_bottom = max(lane_top, self.TRACK_Y - 2)
                painter.setPen(QPen(QColor(145, 145, 145, 205), 1))
                for keyframe in visible_keyframes:
                    x = self._x_from_time(keyframe)
                    if -1 <= x <= width + 1:
                        painter.drawLine(
                            int(x),
                            lane_top,
                            int(x),
                            lane_bottom,
                        )
'''
    new_keyframe_paint = '''        if self.keyframes:
            first = bisect.bisect_left(self.keyframes, vis_start - 1e-9)
            last = bisect.bisect_right(self.keyframes, vis_end + 1e-9)
            visible_count = max(0, last - first)

            # A dense viewport can be rejected without slicing and sorting
            # thousands of timestamps on every playhead repaint. If there are
            # more markers than the lane can physically fit at the configured
            # minimum spacing, drawing the complete truthful keyframe set would
            # necessarily overlap, so hide it immediately.
            marker_capacity = max(
                2,
                int(width / max(1.0, self.keyframe_min_spacing_px)) + 2,
            )
            show_keyframes = 0 < visible_count <= marker_capacity
            visible_keyframes = (
                self.keyframes[first:last] if show_keyframes else []
            )

            if show_keyframes:
                # Include one neighbour outside each side when available.  It
                # keeps the actual-spacing estimate stable while panning near
                # viewport edges. The hard density cap above keeps this slice
                # small even on multi-hour VODs.
                spacing_first = max(0, first - 1)
                spacing_last = min(len(self.keyframes), last + 1)
                spacing_keyframes = self.keyframes[spacing_first:spacing_last]

                if len(spacing_keyframes) > 1:
                    px_per_second = width / max(0.001, self.visible_duration)
                    gaps_px = sorted(
                        max(0.0, b - a) * px_per_second
                        for a, b in zip(
                            spacing_keyframes,
                            spacing_keyframes[1:],
                        )
                        if b > a
                    )
                    if gaps_px:
                        # Median spacing is robust to an occasional unusually
                        # close scene-change keyframe.
                        representative_spacing_px = gaps_px[len(gaps_px) // 2]
                        show_keyframes = (
                            representative_spacing_px
                            >= self.keyframe_min_spacing_px
                        )

            if show_keyframes:
                lane_top = self.RULER_H + 1
                lane_bottom = max(lane_top, self.TRACK_Y - 2)
                painter.setPen(QPen(QColor(145, 145, 145, 205), 1))
                for keyframe in visible_keyframes:
                    x = self._x_from_time(keyframe)
                    if -1 <= x <= width + 1:
                        painter.drawLine(
                            int(x),
                            lane_top,
                            int(x),
                            lane_bottom,
                        )
'''
    text = replace_once(
        text,
        old_keyframe_paint,
        new_keyframe_paint,
        "optimize dense keyframe timeline paint",
    )

    target.write_text(text, encoding="utf-8")
    print("Applied 0.5.0 stabilization pass to vfr_fastcut.py")
    print("Next: python -m py_compile .\\vfr_fastcut.py .\\vfr_keyframes.py")
    print('Then: python -m unittest discover -s tests -p "test_*.py"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
