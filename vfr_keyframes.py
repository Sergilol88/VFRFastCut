# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Sergilol

"""Reusable keyframe analysis and lossless range snapping for VFR FastCut.

The module deliberately has no Qt dependency.  Both the GUI preview layer and
LosslessExporter can use the same keyframe map and the same snapping rules.
"""

from __future__ import annotations

import bisect
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional


class KeyframeScanCancelled(RuntimeError):
    """Raised when a background/export keyframe scan is cancelled."""


class KeyframeScanError(RuntimeError):
    """Raised when ffprobe cannot produce a usable keyframe map."""


ProgressCallback = Callable[[int], None]


def _terminate_and_reap(proc: subprocess.Popen, timeout: float = 1.0) -> None:
    """Best-effort child-process cleanup without leaking ffprobe processes."""
    if proc.poll() is not None:
        return

    try:
        proc.terminate()
        proc.wait(timeout=timeout)
        return
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass

    try:
        proc.kill()
    except Exception:
        pass

    try:
        proc.wait(timeout=timeout)
    except Exception:
        pass


def scan_video_keyframes(
    ffprobe: str,
    input_path: str,
    *,
    duration: float = 0.0,
    interval: Optional[tuple[float, float]] = None,
    cancel_event: Optional[threading.Event] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> list[float]:
    """Return sorted keyframe timestamps from the first video stream.

    The scan reads packet timestamps/flags instead of decoding video.  This is
    the same information stream-copy export needs to resolve safe cut points.

    ``progress_callback`` receives best-effort integer percentages.  Full-file
    scans use ``duration`` when known; interval scans use the interval length.
    The callback is intentionally optional so the function remains useful in
    command-line/export code without any UI dependency.
    """
    if not ffprobe:
        raise KeyframeScanError("ffprobe executable is not available")

    source = Path(input_path)
    if not source.is_file():
        raise KeyframeScanError(f"Input file not found: {input_path}")

    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_packets",
        "-show_entries", "packet=pts_time,flags",
        "-of", "csv=p=0",
    ]

    progress_start = 0.0
    progress_span = max(0.0, float(duration))
    if interval is not None:
        start, end = interval
        start = max(0.0, float(start))
        end = max(start, float(end))
        if duration > 0:
            end = min(float(duration), end)
        cmd += ["-read_intervals", f"{start:.6f}%{end:.6f}"]
        progress_start = start
        progress_span = max(0.0, end - start)

    cmd.append(str(source))

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
        bufsize=1,
    )

    keyframes: list[float] = []
    diagnostic_lines: list[str] = []
    last_progress = -1

    def report_progress(pts: float) -> None:
        nonlocal last_progress
        if progress_callback is None or progress_span <= 0.001:
            return
        pct = int(
            max(
                0.0,
                min(100.0, ((pts - progress_start) / progress_span) * 100.0),
            )
        )
        if pct == last_progress:
            return
        last_progress = pct
        progress_callback(pct)

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if cancel_event is not None and cancel_event.is_set():
                _terminate_and_reap(proc)
                raise KeyframeScanCancelled()

            stripped = line.strip()
            parts = stripped.split(",")
            if len(parts) < 2:
                if stripped:
                    diagnostic_lines.append(stripped)
                    diagnostic_lines = diagnostic_lines[-20:]
                continue

            try:
                pts = float(parts[0])
            except ValueError:
                if stripped:
                    diagnostic_lines.append(stripped)
                    diagnostic_lines = diagnostic_lines[-20:]
                continue

            report_progress(pts)
            if "K" in parts[-1]:
                keyframes.append(pts)

        rc = proc.wait()
    except KeyframeScanCancelled:
        raise
    except BaseException:
        _terminate_and_reap(proc)
        raise

    if cancel_event is not None and cancel_event.is_set():
        raise KeyframeScanCancelled()

    if rc != 0:
        details = "\n".join(diagnostic_lines[-20:]).strip()
        raise KeyframeScanError(details or "ffprobe could not scan keyframes")

    keyframes = sorted(set(value for value in keyframes if value >= 0.0))
    if not keyframes:
        raise KeyframeScanError("No keyframes were found in the video stream")

    # Preserve the existing VFR FastCut export convention: a full-file map has
    # an explicit project-zero boundary even when the first packet timestamp is
    # slightly above zero.  Interval scans intentionally do not invent it.
    if interval is None and keyframes[0] > 0.01:
        keyframes.insert(0, 0.0)

    if progress_callback is not None:
        progress_callback(100)
    return keyframes


def snap_range_to_keyframes(
    start: float,
    end: float,
    keyframes: list[float],
    duration: float,
) -> Optional[tuple[float, float]]:
    """Snap one kept project range to stream-copy-safe keyframe boundaries.

    This intentionally preserves the 0.4.15 semantics:
    - start moves *forward* to the first keyframe at/after the requested start;
    - end moves *backward* to the last keyframe at/before the requested end;
    - exact project start/end remain exact start/end boundaries.
    """
    if not keyframes or end <= start:
        return None

    duration = max(0.0, float(duration))
    start = max(0.0, float(start))
    end = min(duration, max(start, float(end))) if duration > 0 else max(start, float(end))

    if start <= 0.001:
        snapped_start = 0.0
    else:
        index = bisect.bisect_left(keyframes, start - 1e-6)
        if index >= len(keyframes):
            return None
        snapped_start = keyframes[index]

    if duration > 0 and end >= duration - 0.001:
        snapped_end = duration
    else:
        index = bisect.bisect_right(keyframes, end + 1e-6) - 1
        if index < 0:
            return None
        snapped_end = keyframes[index]

    if snapped_end - snapped_start <= 0.005:
        return None
    return snapped_start, snapped_end


def snap_ranges_to_keyframes(
    ranges: list[tuple[float, float]],
    keyframes: list[float],
    duration: float,
) -> tuple[list[tuple[float, float]], float]:
    """Snap/merge multiple kept ranges and return ``(ranges, max_shift)``."""
    snapped_ranges: list[tuple[float, float]] = []
    max_shift = 0.0

    for range_start, range_end in ranges:
        item = snap_range_to_keyframes(
            range_start,
            range_end,
            keyframes,
            duration,
        )
        if item is None:
            continue

        snapped_start, snapped_end = item
        max_shift = max(
            max_shift,
            abs(snapped_start - range_start),
            abs(snapped_end - range_end),
        )

        if (
            snapped_ranges
            and abs(snapped_ranges[-1][1] - snapped_start) < 0.002
        ):
            snapped_ranges[-1] = (snapped_ranges[-1][0], snapped_end)
        else:
            snapped_ranges.append((snapped_start, snapped_end))

    return snapped_ranges, max_shift


def resolve_preview_playback_position(
    ranges: list[tuple[float, float]],
    position: float,
    *,
    tolerance: float = 0.003,
) -> tuple[int, Optional[float]]:
    """Resolve an edited-preview position against effective kept ranges.

    Returns ``(range_index, jump_target)``:
    - ``range_index >= 0`` and ``jump_target is None`` means the position is
      already inside a playable range;
    - ``range_index == -1`` with a numeric ``jump_target`` means playback is in
      a removed gap and should jump to the next kept range;
    - ``(-1, None)`` means there is no playable range at or after the position.

    The end boundary is treated as exclusive (with a tiny tolerance) so the
    preview skips immediately once it reaches the same snapped end boundary
    used by lossless export.
    """
    if not ranges:
        return -1, None

    position = float(position)
    tolerance = max(0.0, float(tolerance))
    probe = position + tolerance

    # ``ranges`` is already sorted by start time. Bisect the tuple list itself
    # instead of allocating a parallel list of starts on every player position
    # update; this function is on the Edited Preview hot path.
    index = bisect.bisect_right(ranges, (probe, float("inf"))) - 1
    if index >= 0:
        start, end = ranges[index]
        if start - tolerance <= position < end - tolerance:
            return index, None

    next_index = index + 1
    if next_index < len(ranges):
        return -1, ranges[next_index][0]

    return -1, None
