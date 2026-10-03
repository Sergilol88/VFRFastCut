# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Sergilol

"""Apply the v0.5.0 export/mixer stabilization pass.

This pass removes two redundant full-file/range I/O passes from the processed
export pipeline without changing the audio-processing semantics:

1. Embedded-only processing with no Main Mix / external audio now writes the
   requested range directly to the final part instead of processing to a temp
   primary file and immediately remuxing that temp file again.
2. When embedded source streams themselves need no processing, non-zero edited
   ranges can feed the final assembly directly from the original source using a
   keyframe-safe input seek. This avoids writing/reading a large primary temp
   file merely to combine/mix audio.

Cases that actually modify embedded audio keep the existing prepared-primary
path. External audio preparation, Main Mix filters, stems and concat semantics
are otherwise unchanged.
"""

from __future__ import annotations

from pathlib import Path


MARKER = "# Direct-source processed-export fast path (0.5.0 stabilization)."


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
        print("0.5.0 stabilization pass 3 is already applied; nothing to do.")
        return 0

    old_primary = '''        external_tracks = self._required_external_tracks()\n\n        primary_path: Optional[Path] = None\n        primary_is_original = False\n        if self._has_primary_streams():\n            if start <= 0.001 and not self._has_embedded_audio_processing():\n                # A range that begins at project zero can use the source file\n                # directly when its embedded streams need no processing.\n                primary_path = Path(self.input_path)\n                primary_is_original = True\n            else:\n                primary_path = temp_dir / (\n                    f"primary_{tag}{'.mkv' if self.export_video else '.mka'}"\n                )\n                self._build_primary_range_part(primary_path, start, end)\n\n        prepared: list[tuple[Path, float]] = []\n'''
    new_primary = '''        external_tracks = self._required_external_tracks()\n\n        # If the only requested processing is on embedded tracks and there is\n        # no Main Mix/external stream to assemble afterward, the prepared\n        # primary file already *is* the finished range. Write it directly and\n        # skip an otherwise redundant second full remux pass.\n        if (\n            not self._has_main_mix()\n            and not external_tracks\n            and self._has_primary_streams()\n        ):\n            self._build_primary_range_part(output, start, end)\n            return\n\n        primary_path: Optional[Path] = None\n        primary_is_original = False\n        if self._has_primary_streams():\n            if not self._has_embedded_audio_processing():\n                # Direct-source processed-export fast path (0.5.0 stabilization).\n                # The edited range boundaries are already keyframe-snapped when\n                # video is present, so the original source can feed the final\n                # assembly directly even for non-zero ranges.\n                primary_path = Path(self.input_path)\n                primary_is_original = True\n            else:\n                primary_path = temp_dir / (\n                    f"primary_{tag}{'.mkv' if self.export_video else '.mka'}"\n                )\n                self._build_primary_range_part(primary_path, start, end)\n\n        prepared: list[tuple[Path, float]] = []\n'''
    text = replace_once(
        text,
        old_primary,
        new_primary,
        "optimize processed primary preparation",
    )

    old_input = '''        if primary_path is not None:\n            primary_input_index = input_index\n            cmd += ["-i", str(primary_path)]\n            input_index += 1\n'''
    new_input = '''        if primary_path is not None:\n            primary_input_index = input_index\n            if primary_is_original and start > 0.001:\n                cmd += ["-ss", f"{start:.6f}"]\n            cmd += ["-i", str(primary_path)]\n            input_index += 1\n'''
    text = replace_once(
        text,
        old_input,
        new_input,
        "seek direct original primary input",
    )

    old_no_mix_finish = '''            cmd += ["-t", f"{duration:.6f}", "-c", "copy"]\n            if primary_input_index is not None:\n                cmd += ["-map_metadata", str(primary_input_index)]\n            cmd += [str(output)]\n            self._run(cmd)\n            return\n'''
    new_no_mix_finish = '''            cmd += ["-t", f"{duration:.6f}", "-c", "copy"]\n            if primary_input_index is not None:\n                cmd += ["-map_metadata", str(primary_input_index)]\n            if primary_is_original and start > 0.001:\n                cmd += ["-avoid_negative_ts", "make_zero"]\n            cmd += [str(output)]\n            self._run(cmd)\n            return\n'''
    text = replace_once(
        text,
        old_no_mix_finish,
        new_no_mix_finish,
        "normalize direct-source no-mix timestamps",
    )

    # The Main Mix assembly has the same direct-source input possibility. Add
    # timestamp normalization just before its final output path as well.
    old_mix_finish = '''        cmd += ["-t", f"{duration:.6f}"]\n        if primary_input_index is not None:\n            cmd += ["-map_metadata", str(primary_input_index)]\n        cmd += self._main_mix_metadata_args()\n        cmd += [str(output)]\n        self._run(cmd)\n'''
    new_mix_finish = '''        cmd += ["-t", f"{duration:.6f}"]\n        if primary_input_index is not None:\n            cmd += ["-map_metadata", str(primary_input_index)]\n        cmd += self._main_mix_metadata_args()\n        if primary_is_original and start > 0.001:\n            cmd += ["-avoid_negative_ts", "make_zero"]\n        cmd += [str(output)]\n        self._run(cmd)\n'''
    text = replace_once(
        text,
        old_mix_finish,
        new_mix_finish,
        "normalize direct-source Main Mix timestamps",
    )

    target.write_text(text, encoding="utf-8")
    print("Applied 0.5.0 stabilization pass 3 to vfr_fastcut.py")
    print("Optimized processed export to avoid redundant primary temp/remux passes.")
    print("Next: python -m py_compile .\\vfr_fastcut.py .\\vfr_keyframes.py")
    print('Then: python -m unittest discover -s tests -p "test_*.py"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
