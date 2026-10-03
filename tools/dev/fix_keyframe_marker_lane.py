# SPDX-License-Identifier: MIT
"""Refine 0.5.x keyframe marker rendering in an already integrated vfr_fastcut.py.

Moves keyframe ticks out of the time-ruler tick area into the dedicated gap
between ruler and video track, and makes marker visibility depend on actual
keyframe spacing instead of visible-count averaging.
"""

from __future__ import annotations

from pathlib import Path


OLD = '''        # ---- keyframe map ----
        # Keyframes are useful only when they are visually separable.
        # At wide zoom levels hiding them is clearer than rendering a
        # solid barcode across the ruler.
        if self.keyframes:
            first = bisect.bisect_left(self.keyframes, vis_start - 1e-9)
            last = bisect.bisect_right(self.keyframes, vis_end + 1e-9)
            visible_keyframes = self.keyframes[first:last]
            if visible_keyframes:
                spacing_px = (
                    width / max(1, len(visible_keyframes) - 1)
                    if len(visible_keyframes) > 1
                    else float(width)
                )
                if spacing_px >= self.keyframe_min_spacing_px:
                    painter.setPen(QPen(QColor(135, 135, 135, 190), 1))
                    for keyframe in visible_keyframes:
                        x = self._x_from_time(keyframe)
                        if -1 <= x <= width + 1:
                            painter.drawLine(
                                int(x),
                                self.RULER_H - 8,
                                int(x),
                                self.RULER_H - 2,
                            )

'''

NEW = '''        # ---- keyframe map ----
        # Keep keyframe markers in their own narrow lane between the time ruler
        # and the video track.  This avoids visual collisions with ruler ticks.
        # Visibility is based on the representative *actual* keyframe spacing
        # on screen, so zooming does not make the whole marker set flicker merely
        # because one keyframe entered or left the viewport.
        if self.keyframes:
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


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "vfr_fastcut.py"
    text = target.read_text(encoding="utf-8")

    if NEW in text:
        print("Keyframe marker lane fix is already applied; nothing to do.")
        return 0

    count = text.count(OLD)
    if count != 1:
        raise RuntimeError(
            f"Expected one integrated keyframe drawing block, found {count}. "
            "Run apply_keyframe_architecture.py first or inspect local changes."
        )

    target.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("Applied keyframe marker lane/density fix to vfr_fastcut.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
