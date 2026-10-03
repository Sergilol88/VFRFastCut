# SPDX-License-Identifier: MIT
"""Add the 0.5.x single-track Main Mix stream-copy fast path.

Run this helper on a locally integrated feature/0.5.0 working tree. It is
idempotent and only touches vfr_fastcut.py.
"""

from __future__ import annotations

from pathlib import Path


MARKER = "def _single_track_main_mix_copy_track("


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
        print("Single-track Main Mix fast path is already applied; nothing to do.")
        return 0

    text = replace_once(
        text,
        '        "main_mix_note": "Main Mix was created from Play-enabled tracks as AAC stereo/48 kHz and set as the first/default audio stream.",\n',
        '        "main_mix_note": "Main Mix was created from Play-enabled tracks as AAC stereo/48 kHz and set as the first/default audio stream.",\n'
        '        "main_mix_stream_copy_note": "Main Mix uses direct stream copy of the single unchanged AAC track; source codec and parameters are preserved.",\n',
        "English fast Main Mix note",
    )
    text = replace_once(
        text,
        '        "main_mix_note": "Main Mix создан из дорожек с активным флагом Play как AAC stereo/48 kHz и установлен первым аудиопотоком/дорожкой по умолчанию.",\n',
        '        "main_mix_note": "Main Mix создан из дорожек с активным флагом Play как AAC stereo/48 kHz и установлен первым аудиопотоком/дорожкой по умолчанию.",\n'
        '        "main_mix_stream_copy_note": "Main Mix использует прямой stream copy единственной неизменённой AAC-дорожки; исходный кодек и параметры сохранены.",\n',
        "Russian fast Main Mix note",
    )

    text = replace_once(
        text,
        "        self._cancel_event = threading.Event()\n"
        "        self._process_lock = threading.Lock()\n",
        "        self._cancel_event = threading.Event()\n"
        "        self._used_single_track_main_mix_copy = False\n"
        "        self._process_lock = threading.Lock()\n",
        "exporter fast-path state",
    )

    insertion_marker = "    def _build_processed_range_part(\n"
    helper_block = '''    def _single_track_main_mix_copy_track(self) -> Optional[AudioTrack]:
        """Return the one embedded AAC track eligible for direct Main Mix copy.

        The default Main Mix path decodes and mixes audio, which is necessary
        for real mixes, external audio, fades, volume changes and stems. When
        Main Mix is just one untouched embedded AAC stream, doing that work is
        redundant and forces an expensive extra pass over long VOD ranges.
        """
        if not self._has_main_mix() or self.export_separate_audio_tracks:
            return None
        if not self.source_audio_probe_ok or self._required_external_tracks():
            return None

        tracks = self._selected_mix_tracks("embedded")
        if len(tracks) != 1:
            return None

        track = tracks[0]
        if _track_requires_processing(track):
            return None

        # AAC is safe for every video/audio output container currently offered
        # by VFR FastCut. Other codecs keep the proven transcoding path instead
        # of risking a container/codec incompatibility regression.
        if track.codec_name.strip().lower() != "aac":
            return None
        return track

    def _build_single_track_main_mix_copy_part(
        self,
        track: AudioTrack,
        output: Path,
        start: float,
        end: float,
    ) -> None:
        """Write one edited range in a single FFmpeg stream-copy pass."""
        duration = max(0.0, end - start)
        cmd = [
            self.ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
        ]
        if start > 0.001:
            cmd += ["-ss", f"{start:.6f}"]
        cmd += ["-i", self.input_path]
        cmd += ["-t", f"{duration:.6f}"]

        if self.export_video:
            cmd += ["-map", "0:v:0", "-c:v", "copy"]

        cmd += [
            "-map", f"0:{track.stream_index}",
            "-c:a:0", "copy",
            "-map_metadata", "0",
        ]
        cmd += self._main_mix_metadata_args()

        if start > 0.001:
            cmd += ["-avoid_negative_ts", "make_zero"]
        cmd += [str(output)]

        self._used_single_track_main_mix_copy = True
        self._run(cmd)

'''
    if text.count(insertion_marker) != 1:
        raise RuntimeError(
            "Main Mix helper insertion point: expected exactly one match"
        )
    text = text.replace(insertion_marker, helper_block + insertion_marker, 1)

    text = replace_once(
        text,
        "        duration = max(0.0, end - start)\n"
        "        external_tracks = self._required_external_tracks()\n",
        "        duration = max(0.0, end - start)\n"
        "        fast_main_mix_track = self._single_track_main_mix_copy_track()\n"
        "        if fast_main_mix_track is not None:\n"
        "            self._build_single_track_main_mix_copy_part(\n"
        "                fast_main_mix_track,\n"
        "                output,\n"
        "                start,\n"
        "                end,\n"
        "            )\n"
        "            return\n\n"
        "        external_tracks = self._required_external_tracks()\n",
        "processed range fast-path dispatch",
    )

    text = replace_once(
        text,
        "        if self._has_main_mix():\n"
        "            note += \"\\n\" + self._t(\"main_mix_note\")\n",
        "        if self._has_main_mix():\n"
        "            note += \"\\n\" + self._t(\n"
        "                \"main_mix_stream_copy_note\"\n"
        "                if self._used_single_track_main_mix_copy\n"
        "                else \"main_mix_note\"\n"
        "            )\n",
        "Main Mix result note",
    )

    target.write_text(text, encoding="utf-8")
    print("Applied single-track Main Mix stream-copy fast path to vfr_fastcut.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
