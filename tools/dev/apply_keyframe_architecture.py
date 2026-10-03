# SPDX-License-Identifier: MIT
"""Integrate the 0.5.x keyframe architecture into vfr_fastcut.py.

This is an idempotent development helper for the feature/0.5.0 branch.  It
keeps the large legacy single-file GUI source reviewable while the keyframe
core lives in vfr_keyframes.py.
"""

from __future__ import annotations

import sys
from pathlib import Path


MARKER = "from vfr_keyframes import ("


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_between(
    text: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
    label: str,
) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: start marker not found")
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:start] + replacement + text[end:]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "vfr_fastcut.py"
    if not target.is_file():
        raise RuntimeError(f"vfr_fastcut.py not found at {target}")

    text = target.read_text(encoding="utf-8")
    if MARKER in text:
        print("Keyframe architecture is already integrated; nothing to do.")
        return 0

    text = replace_once(
        text,
        "from typing import Optional\n\n# Qt Multimedia hardware texture conversion",
        "from typing import Optional\n\n"
        "from vfr_keyframes import (\n"
        "    KeyframeScanCancelled,\n"
        "    KeyframeScanError,\n"
        "    scan_video_keyframes,\n"
        "    snap_range_to_keyframes,\n"
        "    snap_ranges_to_keyframes,\n"
        ")\n\n"
        "# Qt Multimedia hardware texture conversion",
        "keyframe imports",
    )

    text = replace_once(
        text,
        '        "scan_keyframes": "Scanning keyframes…",\n',
        '        "scan_keyframes": "Scanning keyframes…",\n'
        '        "keyframe_scan_started": "Analyzing keyframes…",\n'
        '        "keyframe_scan_progress": "Analyzing keyframes… {percent}%",\n'
        '        "keyframe_scan_finished": "Keyframes ready: {count}",\n'
        '        "keyframe_scan_failed_status": "Keyframe analysis unavailable.",\n',
        "English keyframe UI text",
    )
    text = replace_once(
        text,
        '        "scan_keyframes": "Сканирую keyframes…",\n',
        '        "scan_keyframes": "Сканирую keyframes…",\n'
        '        "keyframe_scan_started": "Анализирую keyframes…",\n'
        '        "keyframe_scan_progress": "Анализирую keyframes… {percent}%",\n'
        '        "keyframe_scan_finished": "Keyframes готовы: {count}",\n'
        '        "keyframe_scan_failed_status": "Анализ keyframes недоступен.",\n',
        "Russian keyframe UI text",
    )

    text = replace_once(
        text,
        "class ExportCancelledError(RuntimeError):\n    pass\n\n\nclass ExportSignals(QObject):",
        "class KeyframeScanSignals(QObject):\n"
        "    progress = Signal(int, int)\n"
        "    finished = Signal(int, object)\n"
        "    failed = Signal(int, str)\n\n\n"
        "class ExportCancelledError(RuntimeError):\n"
        "    pass\n\n\n"
        "class ExportSignals(QObject):",
        "keyframe scan signals",
    )

    text = replace_once(
        text,
        "        self.selected_index = -1\n\n        self.zoom = 1.0",
        "        self.selected_index = -1\n"
        "        self.keyframes: list[float] = []\n"
        "        self.keyframe_min_spacing_px = 6.0\n\n"
        "        self.zoom = 1.0",
        "timeline keyframe state",
    )

    text = replace_once(
        text,
        "    def set_position(self, position: float):\n"
        "        self.position = max(0.0, min(self.duration, position))\n"
        "        self.update()\n",
        "    def set_keyframes(self, keyframes: list[float]):\n"
        "        normalized = sorted(set(float(value) for value in keyframes if value >= 0.0))\n"
        "        if normalized == self.keyframes:\n"
        "            return\n"
        "        self.keyframes = normalized\n"
        "        self.update()\n\n"
        "    def set_position(self, position: float):\n"
        "        self.position = max(0.0, min(self.duration, position))\n"
        "        self.update()\n",
        "timeline set_keyframes",
    )

    text = replace_once(
        text,
        "        # ---- video track ----\n",
        "        # ---- keyframe map ----\n"
        "        # Keyframes are useful only when they are visually separable.\n"
        "        # At wide zoom levels hiding them is clearer than rendering a\n"
        "        # solid barcode across the ruler.\n"
        "        if self.keyframes:\n"
        "            first = bisect.bisect_left(self.keyframes, vis_start - 1e-9)\n"
        "            last = bisect.bisect_right(self.keyframes, vis_end + 1e-9)\n"
        "            visible_keyframes = self.keyframes[first:last]\n"
        "            if visible_keyframes:\n"
        "                spacing_px = (\n"
        "                    width / max(1, len(visible_keyframes) - 1)\n"
        "                    if len(visible_keyframes) > 1\n"
        "                    else float(width)\n"
        "                )\n"
        "                if spacing_px >= self.keyframe_min_spacing_px:\n"
        "                    painter.setPen(QPen(QColor(135, 135, 135, 190), 1))\n"
        "                    for keyframe in visible_keyframes:\n"
        "                        x = self._x_from_time(keyframe)\n"
        "                        if -1 <= x <= width + 1:\n"
        "                            painter.drawLine(\n"
        "                                int(x),\n"
        "                                self.RULER_H - 8,\n"
        "                                int(x),\n"
        "                                self.RULER_H - 2,\n"
        "                            )\n\n"
        "        # ---- video track ----\n",
        "timeline keyframe drawing",
    )

    text = replace_once(
        text,
        "        ranges_override: Optional[list[tuple[float, float]]] = None,\n"
        "        language: str = \"en\",\n",
        "        ranges_override: Optional[list[tuple[float, float]]] = None,\n"
        "        keyframes: Optional[list[float]] = None,\n"
        "        language: str = \"en\",\n",
        "exporter keyframe parameter",
    )

    text = replace_once(
        text,
        "        self.ranges_override = (\n"
        "            list(ranges_override)\n"
        "            if ranges_override is not None\n"
        "            else None\n"
        "        )\n\n"
        "        self._cancel_event = threading.Event()",
        "        self.ranges_override = (\n"
        "            list(ranges_override)\n"
        "            if ranges_override is not None\n"
        "            else None\n"
        "        )\n"
        "        self.keyframes = sorted(\n"
        "            set(float(value) for value in (keyframes or []) if value >= 0.0)\n"
        "        )\n\n"
        "        self._cancel_event = threading.Event()",
        "exporter cached keyframes",
    )

    text = replace_between(
        text,
        "    def _scan_keyframes(self, interval: Optional[tuple[float, float]] = None) -> list[float]:\n",
        "    def _make_staging_output(self, final_output: Path) -> Path:\n",
        "    def _scan_keyframes(self, interval: Optional[tuple[float, float]] = None) -> list[float]:\n"
        "        self._check_cancelled()\n"
        "        self.signals.progress.emit(3, self._t(\"scan_keyframes\"))\n"
        "        try:\n"
        "            return scan_video_keyframes(\n"
        "                self.ffprobe,\n"
        "                self.input_path,\n"
        "                duration=self.duration,\n"
        "                interval=interval,\n"
        "                cancel_event=self._cancel_event,\n"
        "            )\n"
        "        except KeyframeScanCancelled as exc:\n"
        "            raise ExportCancelledError() from exc\n"
        "        except KeyframeScanError as exc:\n"
        "            message = str(exc)\n"
        "            if \"No keyframes\" in message:\n"
        "                raise RuntimeError(self._t(\"no_keyframes\")) from exc\n"
        "            raise RuntimeError(message or self._t(\"ffprobe_scan_failed\")) from exc\n\n"
        "    def _keyframes_for_export(\n"
        "        self,\n"
        "        interval: Optional[tuple[float, float]] = None,\n"
        "    ) -> list[float]:\n"
        "        if self.keyframes:\n"
        "            return self.keyframes\n"
        "        return self._scan_keyframes(interval)\n\n"
        "    def _snap_range(\n"
        "        self, start: float, end: float, keyframes: list[float]\n"
        "    ) -> Optional[tuple[float, float]]:\n"
        "        return snap_range_to_keyframes(\n"
        "            start, end, keyframes, self.duration\n"
        "        )\n\n",
        "exporter shared keyframe methods",
    )

    old_processing = """        scan_interval = (
            keep[0]
            if self.ranges_override is not None and len(keep) == 1
            else None
        )
        keyframes = self._scan_keyframes(scan_interval)
        export_ranges: list[tuple[float, float]] = []
        max_shift = 0.0

        for range_start, range_end in keep:
            self._check_cancelled()
            item = self._snap_range(range_start, range_end, keyframes)
            if item is None:
                continue

            snapped_start, snapped_end = item
            max_shift = max(
                max_shift,
                abs(snapped_start - range_start),
                abs(snapped_end - range_end),
            )
            if (
                export_ranges
                and abs(export_ranges[-1][1] - snapped_start) < 0.002
            ):
                export_ranges[-1] = (
                    export_ranges[-1][0],
                    snapped_end,
                )
            else:
                export_ranges.append((snapped_start, snapped_end))

"""
    new_processing = """        scan_interval = (
            keep[0]
            if self.ranges_override is not None and len(keep) == 1
            else None
        )
        keyframes = self._keyframes_for_export(scan_interval)
        self._check_cancelled()
        export_ranges, max_shift = snap_ranges_to_keyframes(
            keep,
            keyframes,
            self.duration,
        )

"""
    text = replace_once(
        text,
        old_processing,
        new_processing,
        "processed-export shared snapping",
    )

    old_run = """            max_shift = 0.0

            if self.export_video:
                scan_interval = (
                    keep[0]
                    if self.ranges_override is not None and len(keep) == 1
                    else None
                )
                keyframes = self._scan_keyframes(scan_interval)
                export_ranges: list[tuple[float, float]] = []

                for range_start, range_end in keep:
                    self._check_cancelled()
                    item = self._snap_range(range_start, range_end, keyframes)
                    if item is None:
                        continue

                    snapped_start, snapped_end = item
                    max_shift = max(
                        max_shift,
                        abs(snapped_start - range_start),
                        abs(snapped_end - range_end),
                    )

                    if (
                        export_ranges
                        and abs(export_ranges[-1][1] - snapped_start) < 0.002
                    ):
                        export_ranges[-1] = (
                            export_ranges[-1][0],
                            snapped_end,
                        )
                    else:
                        export_ranges.append((snapped_start, snapped_end))

                if not export_ranges:
                    raise RuntimeError(self._t("no_ranges_after_snap"))
            else:
                # Audio-only stream copy does not depend on video keyframes.
                export_ranges = list(keep)
"""
    new_run = """            max_shift = 0.0

            if self.export_video:
                scan_interval = (
                    keep[0]
                    if self.ranges_override is not None and len(keep) == 1
                    else None
                )
                keyframes = self._keyframes_for_export(scan_interval)
                self._check_cancelled()
                export_ranges, max_shift = snap_ranges_to_keyframes(
                    keep,
                    keyframes,
                    self.duration,
                )
                if not export_ranges:
                    raise RuntimeError(self._t("no_ranges_after_snap"))
            else:
                # Audio-only stream copy does not depend on video keyframes.
                export_ranges = list(keep)
"""
    text = replace_once(text, old_run, new_run, "main-export shared snapping")

    text = replace_once(
        text,
        "        self.audio_probe_ok = False\n"
        "        self.preview_mix_channels: dict[\n",
        "        self.audio_probe_ok = False\n"
        "        self.keyframes: list[float] = []\n"
        "        self._keyframe_scan_generation = 0\n"
        "        self._keyframe_scan_cancel_event: Optional[threading.Event] = None\n"
        "        self.keyframe_scan_thread: Optional[threading.Thread] = None\n"
        "        self.preview_mix_channels: dict[\n",
        "main-window keyframe state",
    )

    text = replace_once(
        text,
        "        self.export_signals.cancelled.connect(self.on_export_cancelled)\n\n"
        "        self.player = QMediaPlayer(self)",
        "        self.export_signals.cancelled.connect(self.on_export_cancelled)\n\n"
        "        self.keyframe_scan_signals = KeyframeScanSignals(self)\n"
        "        self.keyframe_scan_signals.progress.connect(\n"
        "            self.on_keyframe_scan_progress\n"
        "        )\n"
        "        self.keyframe_scan_signals.finished.connect(\n"
        "            self.on_keyframe_scan_finished\n"
        "        )\n"
        "        self.keyframe_scan_signals.failed.connect(\n"
        "            self.on_keyframe_scan_failed\n"
        "        )\n\n"
        "        self.player = QMediaPlayer(self)",
        "keyframe scan signal wiring",
    )

    text = replace_once(
        text,
        "        self.player.stop()\n"
        "        self.player.setSource(QUrl())\n"
        "        self._clear_preview_mix()",
        "        self._cancel_keyframe_scan()\n"
        "        self.player.stop()\n"
        "        self.player.setSource(QUrl())\n"
        "        self._clear_preview_mix()",
        "cancel scan on project clear",
    )

    text = replace_once(
        text,
        "        self.audio_tracks.clear()\n"
        "        self.audio_probe_ok = False\n"
        "        self.selected_index = -1",
        "        self.audio_tracks.clear()\n"
        "        self.audio_probe_ok = False\n"
        "        self.keyframes.clear()\n"
        "        self.timeline.set_keyframes([])\n"
        "        self.selected_index = -1",
        "clear cached keyframes",
    )

    # First-load path does not go through _clear_project_state(), so explicitly
    # reset any keyframe UI/model state here too.
    load_anchor = """        self.audio_tracks.clear()
        self.audio_probe_ok = False
        self._clear_preview_mix()
        self.selected_index = -1
"""
    load_replacement = """        self.audio_tracks.clear()
        self.audio_probe_ok = False
        self.keyframes.clear()
        self.timeline.set_keyframes([])
        self._clear_preview_mix()
        self.selected_index = -1
"""
    text = replace_once(text, load_anchor, load_replacement, "load-video keyframe reset")

    text = replace_once(
        text,
        "        self._update_timeline()\n"
        "        self._update_ui_state()\n\n"
        "    def on_position_changed(self, ms: int):",
        "        self._update_timeline()\n"
        "        self._update_ui_state()\n"
        "        self._start_keyframe_scan()\n\n"
        "    def on_position_changed(self, ms: int):",
        "start scan after media duration",
    )

    scan_methods = r'''    def _cancel_keyframe_scan(self):
        cancel_event = self._keyframe_scan_cancel_event
        if cancel_event is not None:
            cancel_event.set()

        # Any late signals from the old worker become stale immediately.
        self._keyframe_scan_generation += 1
        self._keyframe_scan_cancel_event = None
        self.keyframe_scan_thread = None

    def _start_keyframe_scan(self):
        if not self.input_path or self.duration <= 0 or self.keyframes:
            return
        if self.keyframe_scan_thread and self.keyframe_scan_thread.is_alive():
            return

        ffprobe = find_tool("ffprobe.exe")
        if not ffprobe:
            return

        self._keyframe_scan_generation += 1
        generation = self._keyframe_scan_generation
        cancel_event = threading.Event()
        self._keyframe_scan_cancel_event = cancel_event
        source_path = self.input_path
        duration = self.duration
        signals = self.keyframe_scan_signals

        self.statusBar().showMessage(self._t("keyframe_scan_started"))

        def worker():
            try:
                keyframes = scan_video_keyframes(
                    ffprobe,
                    source_path,
                    duration=duration,
                    cancel_event=cancel_event,
                    progress_callback=lambda pct: signals.progress.emit(
                        generation, pct
                    ),
                )
            except KeyframeScanCancelled:
                return
            except Exception as exc:
                signals.failed.emit(generation, str(exc))
                return
            signals.finished.emit(generation, keyframes)

        thread = threading.Thread(
            target=worker,
            daemon=True,
            name="VFRFastCutKeyframeScan",
        )
        self.keyframe_scan_thread = thread
        thread.start()

    def on_keyframe_scan_progress(self, generation: int, percent: int):
        if generation != self._keyframe_scan_generation:
            return
        if not self._export_busy:
            self.statusBar().showMessage(
                self._t("keyframe_scan_progress", percent=percent)
            )

    def on_keyframe_scan_finished(self, generation: int, keyframes):
        if generation != self._keyframe_scan_generation:
            return

        self.keyframe_scan_thread = None
        self._keyframe_scan_cancel_event = None
        self.keyframes = sorted(
            set(float(value) for value in keyframes if value >= 0.0)
        )
        self.timeline.set_keyframes(self.keyframes)
        if not self._export_busy:
            self.statusBar().showMessage(
                self._t("keyframe_scan_finished", count=len(self.keyframes)),
                3500,
            )

    def on_keyframe_scan_failed(self, generation: int, error: str):
        if generation != self._keyframe_scan_generation:
            return

        self.keyframe_scan_thread = None
        self._keyframe_scan_cancel_event = None
        self.keyframes.clear()
        self.timeline.set_keyframes([])
        if not self._export_busy:
            self.statusBar().showMessage(
                self._t("keyframe_scan_failed_status"),
                5000,
            )

'''
    text = replace_once(
        text,
        "    def _activate_after_drop(self):\n",
        scan_methods + "    def _activate_after_drop(self):\n",
        "background scan methods",
    )

    text = replace_once(
        text,
        "            source_audio_probe_ok=self.audio_probe_ok,\n"
        "            ranges_override=ranges_override,\n"
        "            language=self.language,\n",
        "            source_audio_probe_ok=self.audio_probe_ok,\n"
        "            ranges_override=ranges_override,\n"
        "            keyframes=list(self.keyframes),\n"
        "            language=self.language,\n",
        "pass cached keyframes to exporter",
    )

    text = replace_once(
        text,
        "    def closeEvent(self, event):\n"
        "        self._seek_timer.stop()\n"
        "        self._cancel_preview_prime()",
        "    def closeEvent(self, event):\n"
        "        keyframe_thread = self.keyframe_scan_thread\n"
        "        self._cancel_keyframe_scan()\n"
        "        if keyframe_thread and keyframe_thread.is_alive():\n"
        "            keyframe_thread.join(timeout=0.75)\n\n"
        "        self._seek_timer.stop()\n"
        "        self._cancel_preview_prime()",
        "close keyframe worker",
    )

    # Validate Python syntax before touching the working tree.
    compile(text, str(target), "exec")
    target.write_text(text, encoding="utf-8")

    print("Integrated 0.5.x keyframe architecture into vfr_fastcut.py")
    print("Next: python -m unittest discover -s tests -p \"test_keyframes.py\"")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
