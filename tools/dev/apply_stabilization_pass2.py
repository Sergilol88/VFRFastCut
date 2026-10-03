# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Sergilol

"""Apply low-risk dead-code and worker-lifecycle cleanup for v0.5.0.

This helper is intentionally narrow and idempotent. It removes state and
wrappers made obsolete by the 0.5.x refactors, then centralizes keyframe-scan
completion cleanup so finished/failed/cancel/close paths have one clear owner.
"""

from __future__ import annotations

from pathlib import Path


MARKER = "def _finish_keyframe_scan_lifecycle(self, generation: int) -> bool:"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def remove_lines_containing(
    text: str,
    needle: str,
    *,
    expected: int,
    label: str,
) -> str:
    lines = text.splitlines(keepends=True)
    found = sum(1 for line in lines if needle in line)
    if found != expected:
        raise RuntimeError(f"{label}: expected {expected} lines, found {found}")
    return "".join(line for line in lines if needle not in line)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "vfr_fastcut.py"
    if not target.is_file():
        raise RuntimeError(f"vfr_fastcut.py not found at {target}")

    text = target.read_text(encoding="utf-8")
    if MARKER in text:
        print("0.5.0 stabilization pass 2 is already applied; nothing to do.")
        return 0

    # The exporter now calls the shared multi-range snapper directly. The old
    # one-range wrapper and its import have no callers.
    text = replace_once(
        text,
        "    snap_range_to_keyframes,\n",
        "",
        "remove unused snap_range_to_keyframes import",
    )
    text = replace_once(
        text,
        '''    def _snap_range(\n        self, start: float, end: float, keyframes: list[float]\n    ) -> Optional[tuple[float, float]]:\n        return snap_range_to_keyframes(\n            start, end, keyframes, self.duration\n        )\n\n''',
        "",
        "remove unused exporter snap wrapper",
    )

    # These aliases were useful during the audio-export refactor but all active
    # paths now go through _selected_audio_tracks/_required_* helpers.
    text = replace_once(
        text,
        '''    def _selected_external_tracks(self) -> list[AudioTrack]:\n        return self._selected_audio_tracks("external")\n\n    def _selected_embedded_tracks(self) -> list[AudioTrack]:\n        return self._selected_audio_tracks("embedded")\n\n''',
        "",
        "remove unused selected-track aliases",
    )

    # This flag was introduced while Edited Preview could have two range modes.
    # No code reads it anymore; the effective range cache itself is authoritative.
    text = remove_lines_containing(
        text,
        "self._edited_preview_ranges_exact",
        expected=5,
        label="remove dead edited-preview exact flag",
    )

    # TaskProgressDialog used to remember whether the user hid a task window.
    # No later decision reads that state; visibility is already represented by Qt.
    text = remove_lines_containing(
        text,
        "self._user_hidden",
        expected=4,
        label="remove dead task-dialog hidden flag",
    )

    # Make cancellation return the exact worker reference that was invalidated.
    # closeEvent can then cancel + join one coherent lifecycle operation instead
    # of reading the attribute separately before cancellation clears it.
    text = replace_once(
        text,
        '''    def _cancel_keyframe_scan(self):\n        self._keyframe_progress_show_timer.stop()\n        self._hide_task_progress("keyframes")\n        cancel_event = self._keyframe_scan_cancel_event\n        if cancel_event is not None:\n            cancel_event.set()\n\n        # Any late signals from the old worker become stale immediately.\n        self._keyframe_scan_generation += 1\n        self._keyframe_scan_cancel_event = None\n        self.keyframe_scan_thread = None\n''',
        '''    def _cancel_keyframe_scan(self) -> Optional[threading.Thread]:\n        thread = self.keyframe_scan_thread\n        self._keyframe_progress_show_timer.stop()\n        self._hide_task_progress("keyframes")\n        cancel_event = self._keyframe_scan_cancel_event\n        if cancel_event is not None:\n            cancel_event.set()\n\n        # Any late signals from the old worker become stale immediately.\n        self._keyframe_scan_generation += 1\n        self._keyframe_scan_cancel_event = None\n        self.keyframe_scan_thread = None\n        return thread\n''',
        "make keyframe cancellation return invalidated worker",
    )

    # Finished and failed used to duplicate timer/dialog/thread cleanup. Keep the
    # generation gate and all ownership cleanup in one helper so future changes
    # cannot accidentally update only one completion path.
    text = replace_once(
        text,
        '''    def on_keyframe_scan_finished(self, generation: int, keyframes):\n        if generation != self._keyframe_scan_generation:\n            return\n\n        self._keyframe_progress_show_timer.stop()\n        self._hide_task_progress("keyframes")\n        self.keyframe_scan_thread = None\n        self._keyframe_scan_cancel_event = None\n        self.keyframes = sorted(\n''',
        '''    def _finish_keyframe_scan_lifecycle(self, generation: int) -> bool:\n        if generation != self._keyframe_scan_generation:\n            return False\n        self._keyframe_progress_show_timer.stop()\n        self._hide_task_progress("keyframes")\n        self.keyframe_scan_thread = None\n        self._keyframe_scan_cancel_event = None\n        return True\n\n    def on_keyframe_scan_finished(self, generation: int, keyframes):\n        if not self._finish_keyframe_scan_lifecycle(generation):\n            return\n\n        self.keyframes = sorted(\n''',
        "centralize successful keyframe lifecycle cleanup",
    )
    text = replace_once(
        text,
        '''    def on_keyframe_scan_failed(self, generation: int, error: str):\n        if generation != self._keyframe_scan_generation:\n            return\n\n        self._keyframe_progress_show_timer.stop()\n        self._hide_task_progress("keyframes")\n        self.keyframe_scan_thread = None\n        self._keyframe_scan_cancel_event = None\n        self.keyframes.clear()\n''',
        '''    def on_keyframe_scan_failed(self, generation: int, _error: str):\n        if not self._finish_keyframe_scan_lifecycle(generation):\n            return\n\n        self.keyframes.clear()\n''',
        "centralize failed keyframe lifecycle cleanup",
    )

    text = replace_once(
        text,
        '''    def closeEvent(self, event):\n        keyframe_thread = self.keyframe_scan_thread\n        self._cancel_keyframe_scan()\n        if keyframe_thread and keyframe_thread.is_alive():\n''',
        '''    def closeEvent(self, event):\n        keyframe_thread = self._cancel_keyframe_scan()\n        if keyframe_thread and keyframe_thread.is_alive():\n''',
        "join the worker returned by keyframe cancellation",
    )

    # Final dead-code sanity checks for this pass.
    forbidden = (
        "snap_range_to_keyframes",
        "_edited_preview_ranges_exact",
        "_user_hidden",
        "def _selected_external_tracks",
        "def _selected_embedded_tracks",
        "def _snap_range(",
    )
    leftovers = [item for item in forbidden if item in text]
    if leftovers:
        raise RuntimeError(f"pass 2 left stale symbols: {', '.join(leftovers)}")

    target.write_text(text, encoding="utf-8")
    print("Applied 0.5.0 stabilization pass 2 to vfr_fastcut.py")
    print("Removed dead exporter/preview/dialog state and unified keyframe lifecycle cleanup.")
    print("Next: python -m py_compile .\\vfr_fastcut.py .\\vfr_keyframes.py")
    print('Then: python -m unittest discover -s tests -p "test_*.py"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
