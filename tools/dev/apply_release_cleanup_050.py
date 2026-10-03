# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Sergilol

"""Prepare v0.5.0 documentation/release cleanup without finalizing APP_VERSION.

Run this once after the stabilization passes have been committed. The helper
updates public docs, built-in help, BUILD.md and release notes. It intentionally
leaves APP_VERSION at 0.5.0-dev; final versioning happens only after the portable
RC smoke test.
"""

from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_i = text.find(start)
    if start_i < 0:
        raise RuntimeError(f"{label}: start marker not found")
    end_i = text.find(end, start_i)
    if end_i < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:start_i] + replacement + text[end_i:]


def main() -> int:
    root = Path(__file__).resolve().parents[2]

    # ---------- README.md ----------
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "- Timeline zoom, horizontal scrolling, playhead navigation and cut markers.\n",
        "- Timeline zoom, horizontal scrolling, playhead navigation and cut markers.\n"
        "- Background keyframe analysis with optional keyframe markers on the timeline.\n"
        "- Edited-result preview: normal Play skips deleted ranges using the same effective keyframe boundaries as export, while paused manual seeking can still inspect deleted source frames.\n",
        "README keyframe/edited-preview bullets",
    )
    text = replace_once(
        text,
        "- Compact export result dialog with expandable technical details.\n",
        "- Compact export result dialog with expandable technical details.\n"
        "- Modeless task-progress dialogs for keyframe analysis and export; long analysis can continue while editing remains available.\n",
        "README task dialog bullet",
    )
    text = replace_once(
        text,
        "Because the exported Main Mix contains real audio processing, \"Lossless Export\" does **not** mean that every audio stream is always bit-for-bit copied. The completion dialog can show the detailed processing report.\n",
        "Because the exported Main Mix contains real audio processing, \"Lossless Export\" does **not** mean that every audio stream is always bit-for-bit copied. The completion dialog can show the detailed processing report.\n\n"
        "> **Export performance:** unchanged audio can usually be stream-copied and therefore exports very quickly, even for long recordings. Changing Volume/Fade or creating a real multi-track Main Mix requires audio decode → filter/mix → AAC encode for the affected duration, so long recordings can take noticeably longer. The video stream still remains stream-copied.\n",
        "README audio performance note",
    )
    text = text.replace("Release environment recorded for v0.4.15:", "Release environment used for v0.5.0:")
    text = text.replace("The v0.4.15 release process also retains", "The v0.5.0 release process also retains")
    path.write_text(text, encoding="utf-8")

    # ---------- README_RU.md ----------
    path = root / "README_RU.md"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "- Zoom и горизонтальный скролл таймлайна, playhead, навигация по разрезам.\n",
        "- Zoom и горизонтальный скролл таймлайна, playhead, навигация по разрезам.\n"
        "- Фоновый анализ keyframe с отображением маркеров keyframe на таймлайне.\n"
        "- Preview смонтированного результата: обычное воспроизведение пропускает удалённые диапазоны по тем же эффективным keyframe-границам, что и экспорт, а на паузе можно вручную зайти в удалённый исходный фрагмент и посмотреть его.\n",
        "README_RU keyframe/edited-preview bullets",
    )
    text = replace_once(
        text,
        "- Компактное окно результата экспорта с раскрываемыми техническими подробностями.\n",
        "- Компактное окно результата экспорта с раскрываемыми техническими подробностями.\n"
        "- Отдельные немодальные окна прогресса для анализа keyframe и экспорта; во время длительного анализа можно продолжать монтаж.\n",
        "README_RU task dialog bullet",
    )
    text = replace_once(
        text,
        "Поэтому надпись `Lossless Export` **не означает**, что любой аудиопоток всегда копируется бит-в-бит. Подробный технический отчёт доступен в окне завершения экспорта.\n",
        "Поэтому надпись `Lossless Export` **не означает**, что любой аудиопоток всегда копируется бит-в-бит. Подробный технический отчёт доступен в окне завершения экспорта.\n\n"
        "> **Скорость экспорта:** неизменённый звук обычно можно оставить stream-copy, поэтому даже большие записи экспортируются очень быстро. Изменение Volume/Fade или настоящий Main Mix из нескольких дорожек требуют декодирования → обработки/микширования → кодирования AAC на всей затронутой длительности, поэтому экспорт длинной записи может занять заметно больше времени. Видеоряд при этом по-прежнему остаётся stream-copy.\n",
        "README_RU audio performance note",
    )
    text = text.replace("Зафиксированное окружение релиза v0.4.15:", "Окружение релиза v0.5.0:")
    text = text.replace("Для релиза v0.4.15 также сохраняются", "Для релиза v0.5.0 также сохраняются")
    path.write_text(text, encoding="utf-8")

    # ---------- Built-in F1 help ----------
    path = root / "vfr_fastcut.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '  <li><b>Lossless Export</b> — export all kept segments; video remains stream-copied while Main Mix and other processed audio are encoded only when required.</li>\n',
        '  <li><b>Lossless Export</b> — export all kept segments; video remains stream-copied while Main Mix and other processed audio are encoded only when required.</li>\n'
        '  <li><b>Performance:</b> unchanged audio is normally stream-copied and exports very quickly. Volume/Fade or a real multi-track Main Mix requires audio decoding, filtering/mixing and AAC encoding, so long recordings can take noticeably longer while video still remains stream-copied.</li>\n',
        "English F1 audio performance note",
    )
    text = replace_once(
        text,
        '  <li><b>Lossless Export</b> — экспортировать все неудалённые фрагменты; видеоряд остаётся stream-copy, а Main Mix и другой обрабатываемый звук кодируются только при необходимости.</li>\n',
        '  <li><b>Lossless Export</b> — экспортировать все неудалённые фрагменты; видеоряд остаётся stream-copy, а Main Mix и другой обрабатываемый звук кодируются только при необходимости.</li>\n'
        '  <li><b>Скорость:</b> неизменённый звук обычно остаётся stream-copy и экспортируется очень быстро. Volume/Fade или настоящий Main Mix из нескольких дорожек требуют декодирования, обработки/микширования и кодирования AAC, поэтому на длинных записях экспорт может занять заметно больше времени; видео при этом остаётся stream-copy.</li>\n',
        "Russian F1 audio performance note",
    )
    path.write_text(text, encoding="utf-8")

    # ---------- CHANGELOG.md ----------
    path = root / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    section = '''## 0.5.0\n\n### Keyframe-aware editing and preview\n\n- Added a reusable background keyframe map shared by timeline visualization, Edited Preview and lossless export.\n- Added keyframe markers that appear only when timeline density is useful, keeping long-VOD painting inexpensive.\n- Added Edited Preview: normal playback skips deleted ranges using the same effective keyframe-snapped boundaries as export.\n- Manual paused seeking remains unrestricted, so deleted source ranges can still be inspected before deciding what to keep.\n- Preview audio channels hard-sync after automatic edited-range jumps.\n\n### Export and audio performance\n\n- Added a fast single-track Main Mix path: one unchanged built-in AAC track can be kept by stream-copy instead of being decoded and re-encoded.\n- Removed redundant processed-export primary/remux passes and unnecessary large temporary-file I/O.\n- Reused the background keyframe map during export instead of rescanning the source when possible.\n- Preserved video stream-copy throughout audio processing paths.\n- Clarified performance behavior: unchanged audio is usually very fast to export, while Volume/Fade or a true multi-track Main Mix must decode/process/re-encode audio and can therefore take noticeably longer on long recordings.\n\n### Interface and stability\n\n- Replaced the permanent lower progress bar with a shared modeless Task Progress Dialog for keyframe analysis and export.\n- Keyframe analysis can run in the background while editing remains available.\n- Hardened keyframe worker generation/cancellation lifecycle so stale scans cannot replace the current source map.\n- Reduced hot-path work in Edited Preview, audio fade calculations and keyframe timeline painting.\n- Removed stale/dead state left by the 0.5.x refactors.\n\n### Build and release\n\n- CI now compiles the application/keyframe module, runs unit tests and builds/audits a portable Windows artifact on pull requests.\n- Repaired the minimal-FFmpeg CI path so runtime package splits/renames no longer break release metadata generation.\n- Portable packaging now uses the verified `tools/release/package-portable.ps1` path, validates bundled FFmpeg/FFprobe and verifies archive contents before producing the SHA-256 file.\n\n'''
    text = replace_once(text, "## 0.4.15\n", section + "## 0.4.15\n", "prepend 0.5.0 changelog")
    path.write_text(text, encoding="utf-8")

    # ---------- BUILD.md ----------
    path = root / "BUILD.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("v0.4.15", "v0.5.0").replace("0.4.15", "0.5.0")
    old_runtime = '''Recorded MSYS2 runtime packages:\n\n```text\nmingw-w64-ucrt-x86_64-libwinpthread 14.0.0.r409.g6de5d3b4d-1\nmingw-w64-ucrt-x86_64-gcc-libs     16.2.0-3\n```\n'''
    new_runtime = '''The exact MSYS2 runtime package owners and versions are recorded dynamically in `tools\\ffmpeg-minimal\\runtime\\BUILD_INFO.txt` by the FFmpeg build. Do not hard-code an old GCC runtime package name here: current MSYS2 can split/rename runtime packages while the produced DLL set remains valid.\n'''
    text = replace_once(text, old_runtime, new_runtime, "BUILD runtime package note")

    smoke_start = "Minimum release test:\n\n"
    smoke_end = "Restore:\n\n"
    smoke = '''Minimum release test:\n\n1. Open a representative long VFR/Twitch video with multiple embedded audio streams.\n2. Confirm the keyframe-analysis task dialog appears for a sufficiently large file, then closes cleanly.\n3. Zoom the timeline until keyframe markers become visible; pan/seek/play and check for regressions or excessive UI load.\n4. Create kept → deleted → kept ranges. Normal Play must skip the deleted range, while paused manual seeking can still inspect it.\n5. Check deleted-head, deleted-tail and all-deleted projects.\n6. Play / Pause and seek repeatedly; verify preview audio stays synchronized after Edited Preview jumps.\n7. Check Safe Preview with the user's normal VRR/G-SYNC configuration.\n8. Split and remove a split; Delete/Restore; Undo/Redo.\n9. Multi-range stream-copy export with a middle video segment deleted.\n10. Main Mix with one untouched built-in AAC track and stems off: verify the fast stream-copy path.\n11. Enable a second embedded track and verify real Main Mix preview/export.\n12. Change Volume and Fade on a track and verify processed AAC output. On long recordings this test is expected to take longer because audio must be decoded/processed/re-encoded; video must remain stream-copy.\n13. Add external MP3; verify live preview, offset, trim and exported timing.\n14. Duplicate an external clip, move the copy, then delete the copy.\n15. Main Mix + separate stems.\n16. Audio-only MKA export.\n17. Selected-segment export.\n18. Cancel export from the Task Progress Dialog, then immediately start a new export.\n19. Open a second source while the first source's keyframe scan is still running; stale results must never replace the new keyframe map.\n20. Reset and close the application during keyframe analysis; no hang or late UI update is allowed.\n21. RU ↔ EN switching and persistence.\n22. F1 help, including the audio-processing performance note.\n23. Compact export-complete dialog, `Details`, `Open folder`, and default focus on `OK`.\n24. Confirm the portable app still runs while `C:\\ffmpeg` is unavailable.\n\nRestore:\n\n'''
    text = replace_between(text, smoke_start, smoke_end, smoke, "BUILD smoke checklist")

    archive_start = "## 8. Create release archives\n\n"
    archive_end = "## 9. Release assets\n\n"
    archive = '''## 8. Create release archives\n\nDo not create the release ZIP manually. Use the verified packaging helper from the exact release commit:\n\n```powershell\npowershell.exe -NoProfile -ExecutionPolicy Bypass `\n  -File ".\\tools\\release\\package-portable.ps1" `\n  -DistDir ".\\dist\\VFRFastCut" `\n  -RuntimeDir ".\\tools\\ffmpeg-minimal\\runtime" `\n  -OutputDir "."\n```\n\nThe helper copies the complete verified FFmpeg runtime, runs the portable audit, starts bundled FFmpeg/FFprobe, creates the ZIP, re-opens the archive to verify required executables and writes the SHA-256 file.\n\nAlso calculate and record SHA-256 for each source archive published with the release.\n\n'''
    text = replace_between(text, archive_start, archive_end, archive, "BUILD packaging section")
    text = text.replace(
        "python -m py_compile .\\vfr_fastcut.py\ngit diff --check",
        "python -m py_compile .\\vfr_fastcut.py .\\vfr_keyframes.py\npython -m unittest discover -s tests -p \"test_*.py\"\ngit diff --check",
    )
    path.write_text(text, encoding="utf-8")

    # ---------- tools/release/README.md ----------
    path = root / "tools" / "release" / "README.md"
    path.write_text(
        '''# Release helpers\n\n## Safe portable packaging\n\nUse `package-portable.ps1` for release and RC archives instead of calling `tar.exe` manually.\n\nThe script:\n\n- reads `APP_VERSION` from `vfr_fastcut.py` unless `-Version` is supplied;\n- requires the verified runtime in `tools\\ffmpeg-minimal\\runtime`;\n- copies the complete FFmpeg runtime into `dist\\VFRFastCut\\ffmpeg\\bin`;\n- checks required application, license, `ffmpeg.exe` and `ffprobe.exe` files;\n- starts the bundled `ffmpeg.exe` and `ffprobe.exe` to verify their DLL dependencies;\n- runs `audit-portable.ps1`;\n- creates the release ZIP and SHA-256 file;\n- re-opens the ZIP and refuses the package if `ffmpeg.exe` or `ffprobe.exe` is missing.\n\nFrom the repository root after building `dist\\VFRFastCut`:\n\n```powershell\npowershell.exe -NoProfile -ExecutionPolicy Bypass `\n  -File ".\\tools\\release\\package-portable.ps1"\n```\n\nDefault output:\n\n```text\nVFRFastCut-v<APP_VERSION>-Windows-x64.zip\nVFRFastCut-v<APP_VERSION>-Windows-x64.zip.sha256\n```\n\nFor an RC you may leave `APP_VERSION` as `0.5.0-dev` and use `-Version` to give the test archive an explicit RC label if desired. For the final release, set `APP_VERSION = "0.5.0"`, commit that exact source state, rebuild the application, and package from that exact commit.\n\nDo not publish an archive produced by a manual ZIP step that bypasses these checks.\n''',
        encoding="utf-8",
    )

    # ---------- release-notes/v0.5.0.md ----------
    notes = root / "release-notes" / "v0.5.0.md"
    notes.write_text(
        '''# VFR FastCut v0.5.0\n\nv0.5.0 focuses on making lossless cutting feel closer to editing the final result while keeping the fast stream-copy workflow.\n\n## Highlights\n\n- **Edited Preview:** normal playback skips deleted ranges. Manual paused seeking can still inspect deleted source frames. Preview and export use the same effective keyframe-snapped boundaries.\n- **Background keyframe map:** keyframes are analyzed once in the background, reused by preview/export and shown on the timeline when zoomed in far enough.\n- **Task Progress Dialogs:** keyframe analysis and export now use compact separate progress windows instead of a permanent lower progress bar.\n- **Faster Main Mix/export paths:** one untouched built-in AAC track can remain stream-copy, and processed export avoids redundant large temporary-file/remux passes.\n- **Stability cleanup:** hardened keyframe worker cancellation/source switching and reduced hot-path work on long VODs.\n- **Portable build:** CI now runs tests and the verified portable packaging/audit path.\n\n## Audio export performance\n\nVFR FastCut remains a lossless **video** cutter. Unchanged audio can usually be stream-copied and therefore exports very quickly.\n\nIf you change Volume/Fade or create a real Main Mix from multiple tracks, FFmpeg must decode the affected audio, apply filters/mixing and encode the result to AAC. On long recordings this can take noticeably longer even though the video itself is still copied without re-encoding. This is expected behavior, not video transcoding.\n\n## Notes\n\n- Lossless video cuts remain keyframe-aligned rather than frame-exact.\n- Main Mix processing uses AAC stereo / 48 kHz and a limiter.\n- Windows 10/11 x64 remains the tested release platform.\n''',
        encoding="utf-8",
    )

    print("Prepared v0.5.0 release documentation and built-in help.")
    print("APP_VERSION intentionally remains 0.5.0-dev for the RC stage.")
    print("Next: remove one-shot development helpers with: git rm -r tools/dev")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
