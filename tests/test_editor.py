# SPDX-License-Identifier: MIT
"""GUI regressions; skipped in the dependency-free source-check job."""
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from vfr_fastcut import MainWindow, AudioTrack, Segment
except ImportError:
    MainWindow = None


@unittest.skipIf(MainWindow is None, "PySide6 is not installed")
class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.window.language = "en"

    def tearDown(self):
        self.window.close()
        self.app.processEvents()

    def test_import_returns_while_audio_probe_is_blocked(self):
        entered, release = threading.Event(), threading.Event()

        def slow_probe(*args):
            entered.set()
            release.wait(5)
            return []

        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "test.mp4"
            source.touch()
            with patch("vfr_fastcut.find_tool", return_value="ffprobe"), \
                 patch("vfr_fastcut.probe_audio_tracks", side_effect=slow_probe), \
                 patch.object(self.window, "_start_keyframe_scan") as scan, \
                 patch.object(self.window.player, "setSource"):
                try:
                    self.window.load_video(str(source))
                    self.assertTrue(entered.wait(1))
                    scan.assert_called_once()
                    self.assertTrue(self.window._audio_probe_pending)
                    self.window.on_duration_changed(10000)
                    self.assertFalse(self.window.export_btn.isEnabled())
                    # A queued event still runs while ffprobe has not returned.
                    from PySide6.QtCore import QTimer
                    responsive = []
                    QTimer.singleShot(0, lambda: responsive.append(True))
                    self.app.processEvents()
                    self.assertTrue(responsive)
                finally:
                    release.set()
                deadline = time.monotonic() + 2
                while self.window._audio_probe_pending and time.monotonic() < deadline:
                    self.app.processEvents()
                    time.sleep(0.005)
                self.assertFalse(self.window._audio_probe_pending)
                self.assertTrue(self.window.audio_probe_ok)
                self.assertTrue(self.window.export_btn.isEnabled())

    def test_stale_audio_results_after_reset_are_ignored(self):
        generation = self.window._audio_probe_generation
        self.window._clear_project_state()
        self.window.on_audio_probe_finished(generation, [])
        self.assertFalse(self.window.audio_probe_ok)
        self.assertEqual(self.window.audio_tracks, [])

    def test_split_waits_for_map_then_stores_export_safe_cut(self):
        self.window.input_path = "example.mp4"
        self.window.duration = 10
        self.window.segments = [Segment(0, 10, False)]
        self.window.selected_index = 0
        with patch.object(self.window, "current_seconds", return_value=3.1), \
             patch.object(self.window, "seek_seconds_smooth") as seek:
            self.window.split_at_playhead()
            self.assertEqual(len(self.window.segments), 1)
            self.window.keyframes = [0, 2, 4, 6, 8]
            self.window.split_at_playhead()
            self.assertEqual([(s.start, s.end) for s in self.window.segments], [(0, 4), (4, 10)])
            seek.assert_called_once_with(4)
            self.window.delete_selected()
            self.assertEqual(self.window._edited_preview_ranges, [(0, 4)])
            self.window.undo()
            self.window.undo()
            self.assertEqual(len(self.window.segments), 1)
            self.window.redo()
            self.assertEqual(self.window.segments[1].start, 4)

    def test_audio_probe_failure_keeps_fallback_available(self):
        self.window.on_audio_probe_finished(self.window._audio_probe_generation, None)
        self.assertFalse(self.window.audio_probe_ok)
        self.assertFalse(self.window._audio_probe_pending)

    def test_audio_results_preserve_external_tracks_and_initialize_mix(self):
        embedded = [AudioTrack(i, i, "source.mp4") for i in range(2)]
        external = AudioTrack(0, 0, "music.wav", source_type="external")
        self.window.audio_tracks = [external]
        with patch.object(self.window, "_rebuild_preview_mix"):
            self.window.on_audio_probe_finished(self.window._audio_probe_generation, embedded)
        self.assertEqual(self.window.audio_tracks, embedded + [external])
        self.assertEqual([track.mix_enabled for track in embedded], [True, False])


if __name__ == "__main__":
    unittest.main()
