# SPDX-License-Identifier: MIT
"""Integrate 0.5.x edited-preview playback into vfr_fastcut.py.

The helper is idempotent and intentionally patches the locally integrated GUI
source so the large monolithic file remains easy to review during 0.5.0 work.
"""

from __future__ import annotations

from pathlib import Path


MARKER = "def _refresh_edited_preview_ranges("


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
    if MARKER in text:
        print("Edited preview is already integrated; nothing to do.")
        return 0

    text = replace_once(
        text,
        "    scan_video_keyframes,\n"
        "    snap_range_to_keyframes,\n",
        "    scan_video_keyframes,\n"
        "    resolve_preview_playback_position,\n"
        "    snap_range_to_keyframes,\n",
        "edited-preview helper import",
    )

    text = replace_once(
        text,
        '        "restored": "Segment restored.",\n',
        '        "restored": "Segment restored.",\n'
        '        "preview_nothing_to_play": "All video segments are deleted; there is nothing to play.",\n',
        "English edited-preview text",
    )
    text = replace_once(
        text,
        '        "restored": "Фрагмент восстановлен.",\n',
        '        "restored": "Фрагмент восстановлен.",\n'
        '        "preview_nothing_to_play": "Все видеофрагменты удалены — воспроизводить нечего.",\n',
        "Russian edited-preview text",
    )

    text = replace_once(
        text,
        "  <li><b>Play / Pause [Space]</b> — playback control.</li>\n",
        "  <li><b>Play / Pause [Space]</b> — plays the edited result: deleted gaps are skipped using the same effective keyframe boundaries as lossless export. Manual seeking can still inspect deleted source frames while paused.</li>\n",
        "English help edited preview",
    )
    text = replace_once(
        text,
        "  <li><b>Play / Pause [Space]</b> — воспроизведение и пауза.</li>\n",
        "  <li><b>Play / Pause [Space]</b> — воспроизводит будущий результат монтажа: удалённые участки пропускаются по тем же эффективным keyframe-границам, что и lossless export. На паузе ручной seek по удалённым кадрам остаётся доступен.</li>\n",
        "Russian help edited preview",
    )

    text = replace_once(
        text,
        "        self.keyframes: list[float] = []\n"
        "        self._keyframe_scan_generation = 0\n",
        "        self.keyframes: list[float] = []\n"
        "        self._edited_preview_ranges: list[tuple[float, float]] = []\n"
        "        self._edited_preview_ranges_exact = False\n"
        "        self._edited_preview_jump_active = False\n"
        "        self._keyframe_scan_generation = 0\n",
        "edited-preview state",
    )

    text = replace_once(
        text,
        "        self._resume_after_seek = False\n"
        "        self._seek_session_active = False\n",
        "        self._resume_after_seek = False\n"
        "        self._seek_was_playing = False\n"
        "        self._seek_session_active = False\n",
        "smooth-seek playback intent state",
    )

    text = replace_once(
        text,
        "        self._seek_timer.timeout.connect(self._finish_smooth_seek)\n"
        "        self._resume_after_seek = False\n",
        "        self._seek_timer.timeout.connect(self._finish_smooth_seek)\n\n"
        "        # Automatic edited-preview jumps use direct seeks so cuts do not\n"
        "        # inherit the user-seek debounce delay. A short guard suppresses\n"
        "        # stale positionChanged events from retriggering the same jump.\n"
        "        self._edited_preview_jump_guard_timer = QTimer(self)\n"
        "        self._edited_preview_jump_guard_timer.setSingleShot(True)\n"
        "        self._edited_preview_jump_guard_timer.setInterval(250)\n"
        "        self._edited_preview_jump_guard_timer.timeout.connect(\n"
        "            self._clear_edited_preview_jump_guard\n"
        "        )\n\n"
        "        self._resume_after_seek = False\n",
        "edited-preview jump guard timer",
    )

    text = replace_once(
        text,
        "        self._seek_timer.stop()\n"
        "        self._cancel_preview_prime()\n"
        "        self._seek_session_active = False\n"
        "        self._resume_after_seek = False\n",
        "        self._seek_timer.stop()\n"
        "        self._edited_preview_jump_guard_timer.stop()\n"
        "        self._cancel_preview_prime()\n"
        "        self._seek_session_active = False\n"
        "        self._resume_after_seek = False\n"
        "        self._seek_was_playing = False\n"
        "        self._edited_preview_jump_active = False\n",
        "clear edited-preview transport state",
    )

    text = replace_once(
        text,
        "        self.keyframes.clear()\n"
        "        self.timeline.set_keyframes([])\n"
        "        self.selected_index = -1\n",
        "        self.keyframes.clear()\n"
        "        self.timeline.set_keyframes([])\n"
        "        self._edited_preview_ranges.clear()\n"
        "        self._edited_preview_ranges_exact = False\n"
        "        self.selected_index = -1\n",
        "clear edited-preview ranges",
    )

    text = replace_once(
        text,
        "        self.timeline.set_keyframes(self.keyframes)\n"
        "        if not self._export_busy:\n",
        "        self.timeline.set_keyframes(self.keyframes)\n"
        "        self._refresh_edited_preview_ranges()\n"
        "        if not self._export_busy:\n",
        "refresh preview after keyframe scan",
    )

    text = replace_once(
        text,
        "        self.keyframes.clear()\n"
        "        self.timeline.set_keyframes([])\n"
        "        if not self._export_busy:\n",
        "        self.keyframes.clear()\n"
        "        self.timeline.set_keyframes([])\n"
        "        self._refresh_edited_preview_ranges()\n"
        "        if not self._export_busy:\n",
        "refresh preview after keyframe scan failure",
    )

    position_marker = "    def on_position_changed(self, ms: int):\n"
    helper_block = '''    def _refresh_edited_preview_ranges(self):
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

    def _is_edited_preview_playable(self, position: float) -> bool:
        if not self._edited_preview_enabled():
            return True
        index, _jump_target = resolve_preview_playback_position(
            self._edited_preview_ranges,
            position,
        )
        return index >= 0

    def _clear_edited_preview_jump_guard(self):
        self._edited_preview_jump_active = False

    def _jump_edited_preview_to(self, seconds: float):
        if self.duration <= 0:
            return
        seconds = max(0.0, min(self.duration, float(seconds)))
        target_ms = int(round(seconds * 1000.0))

        self._edited_preview_jump_active = True
        self._edited_preview_jump_guard_timer.start()
        self.player.setPosition(target_ms)
        self.timeline.ensure_time_visible(seconds)
        self._sync_preview_mix_transport(
            force_seek=True,
            project_position_ms=target_ms,
        )
        self._apply_preview_mix_gains(project_position=seconds)

    def _maybe_route_edited_preview_playback(self, position: float) -> bool:
        """Skip removed source-time gaps while normal playback is running."""
        if (
            not self._edited_preview_enabled()
            or self._edited_preview_jump_active
            or self._preview_priming
            or self._seek_session_active
            or self.player.playbackState()
            != QMediaPlayer.PlaybackState.PlayingState
        ):
            return False

        range_index, jump_target = resolve_preview_playback_position(
            self._edited_preview_ranges,
            position,
        )
        if range_index >= 0:
            return False

        if jump_target is not None:
            self._jump_edited_preview_to(jump_target)
            return True

        # No future kept range. If the edit ends before source EOF, stop on the
        # last kept frame instead of continuing into the trailing deleted area.
        if self._edited_preview_ranges:
            last_start, last_end = self._edited_preview_ranges[-1]
            if last_end < self.duration - 0.001:
                self.player.pause()
                stop_at = max(last_start, last_end - 0.001)
                self._jump_edited_preview_to(stop_at)
                self._sync_play_button(QMediaPlayer.PlaybackState.PausedState)
                return True
        else:
            self.player.pause()
            self._sync_play_button(QMediaPlayer.PlaybackState.PausedState)
            self.statusBar().showMessage(
                self._t("preview_nothing_to_play"),
                2500,
            )
            return True

        return False

'''
    if text.count(position_marker) != 1:
        raise RuntimeError("edited-preview helper insertion: expected one on_position_changed")
    text = text.replace(position_marker, helper_block + position_marker, 1)

    text = replace_once(
        text,
        "    def on_position_changed(self, ms: int):\n"
        "        pos = ms / 1000.0\n"
        "        self.timeline.set_position(pos)\n",
        "    def on_position_changed(self, ms: int):\n"
        "        pos = ms / 1000.0\n"
        "        if self._maybe_route_edited_preview_playback(pos):\n"
        "            return\n"
        "        self.timeline.set_position(pos)\n",
        "edited-preview position routing",
    )

    old_seek = '''        if not self._seek_session_active:
            self._seek_session_active = True
            self._resume_after_seek = (
                self.player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState
            )

            # Keep the button representing the user's logical playback mode,
            # not the temporary internal pause used to suppress audio crackle.
            self._set_play_button_playing(self._resume_after_seek)

            if self._resume_after_seek:
                self.player.pause()

            self._seek_temp_muted = True
            self._apply_audio_mute_state()

        target_ms = int(seconds * 1000)
'''
    new_seek = '''        if not self._seek_session_active:
            self._seek_session_active = True
            self._seek_was_playing = (
                self.player.playbackState()
                == QMediaPlayer.PlaybackState.PlayingState
            )

            if self._seek_was_playing:
                self.player.pause()

            self._seek_temp_muted = True
            self._apply_audio_mute_state()

        # Manual seek is allowed everywhere, including removed source ranges.
        # If a seek that started during playback lands in a removed/effectively
        # snapped-out region, remain paused so the user can inspect that frame.
        self._resume_after_seek = (
            self._seek_was_playing
            and self._is_edited_preview_playable(seconds)
        )
        self._set_play_button_playing(self._resume_after_seek)

        target_ms = int(seconds * 1000)
'''
    text = replace_once(text, old_seek, new_seek, "manual seek into deleted ranges")

    text = replace_once(
        text,
        "    def _finish_smooth_seek(self):\n"
        "        resume_playback = self._resume_after_seek\n"
        "        self._resume_after_seek = False\n",
        "    def _finish_smooth_seek(self):\n"
        "        resume_playback = self._resume_after_seek\n"
        "        self._resume_after_seek = False\n"
        "        self._seek_was_playing = False\n",
        "finish manual seek state",
    )

    old_toggle = '''    def toggle_play(self):
        if not self.input_path:
            return
        if self._seek_timer.isActive():
            self._seek_timer.stop()
            self._seek_session_active = False
            self._seek_temp_muted = False
            self._apply_audio_mute_state()
            self._resume_after_seek = False

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()
'''
    new_toggle = '''    def toggle_play(self):
        if not self.input_path:
            return
        if self._seek_timer.isActive():
            self._seek_timer.stop()
            self._seek_session_active = False
            self._seek_temp_muted = False
            self._apply_audio_mute_state()
            self._resume_after_seek = False
            self._seek_was_playing = False

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return

        if self._edited_preview_enabled():
            range_index, jump_target = resolve_preview_playback_position(
                self._edited_preview_ranges,
                self.current_seconds(),
            )
            if range_index < 0:
                if jump_target is None:
                    self.statusBar().showMessage(
                        self._t("preview_nothing_to_play"),
                        2500,
                    )
                    return
                self._jump_edited_preview_to(jump_target)

        self.player.play()
'''
    text = replace_once(text, old_toggle, new_toggle, "Space edited-preview routing")

    text = replace_once(
        text,
        "    def _update_timeline(self):\n"
        "        self.timeline.set_state(\n",
        "    def _update_timeline(self):\n"
        "        self._refresh_edited_preview_ranges()\n"
        "        self.timeline.set_state(\n",
        "refresh edited-preview ranges after edits",
    )

    target.write_text(text, encoding="utf-8")
    print("Integrated 0.5.x edited preview into vfr_fastcut.py")
    print('Next: python -m unittest discover -s tests -p "test_keyframes.py"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
