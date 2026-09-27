# Changelog

All notable changes to VFR FastCut are documented here.

## 0.4.15

### Audio timeline and mixing

- Added a visual audio timeline aligned with the video timeline.
- Added embedded and external audio track visualization.
- Added live preview mixing for all tracks enabled with the timeline Play flag.
- Main Mix is enabled by default and is exported as the first/default audio stream.
- Separate stems remain available as an advanced option and are disabled by default.
- Added per-track Volume, Fade In and Fade Out.
- Added external audio positioning by dragging directly on the timeline.
- Added non-destructive Trim In / Trim Out for external clips.
- Added external clip duplication and copy deletion.
- Added a persistent list of the 10 most recently used external audio files.
- Added right-click audio settings for both embedded and external tracks.
- Fixed external-audio project offsets in the exported Main Mix by applying real audio delay before `amix`.
- Fixed preview channels re-enabled after seeking so they resume from the current playhead instead of project start.

### Interface

- Reorganized less-frequent commands into top menus.
- Kept essential edit controls in the main window.
- Added a context-sensitive Split / Remove Cut button.
- Added a context-sensitive Delete / Restore button.
- Added scrollable audio-track area without resizing the preview when tracks are added.
- Added distinct colors for video, embedded audio and external audio.
- Removed dark label overlays from audio clips and replaced them with outlined text.
- Added compact export-complete dialog with expandable technical details.
- `OK` is the default focused action in the export-complete dialog.

### Preview and performance

- Preserved the `QVideoSink → QImage → QWidget` Safe Preview architecture introduced in 0.2.36.
- Removed obsolete preview diagnostic paths and the forced software video decoder override.
- Hardware video decoding is available again while the compatible texture-conversion setting remains the default.
- Reduced redundant `QAudioOutput.setVolume()` calls in the live preview mixer.

### Export / FFmpeg

- Added external audio demuxing for MP3, WAV, AAC, FLAC and OGG.
- Added the limited audio decoder set needed for track processing.
- Added the native AAC encoder for processed tracks and Main Mix.
- Added `volume`, `afade`, `aformat`, `amix`, `alimiter` and `adelay` filters.
- Video remains stream-copy during the normal lossless workflow.
- Unmodified separate audio streams can remain stream-copy.
- Main Mix is AAC stereo / 48 kHz and uses a limiter.
- Strengthened `verify.ps1` license/configuration and audio-processing smoke tests.
- FFmpeg `BUILD_INFO.txt` now records the exact MSYS2 runtime package versions used by the build.

### Release / documentation

- Updated README and built-in workflow documentation for the 0.4.x audio editor.
- Updated the Windows release process and smoke-test checklist.
- Updated third-party version records for Python 3.14.5, PyInstaller 6.21.0, PySide6/Qt 6.11.2 and FFmpeg 9.0.2.
- Expanded the release checklist for Python, Qt/PySide6 and FFmpeg redistribution compliance.

## 0.2.36

- Reworked video preview rendering to avoid the native `QVideoWidget` presentation path on Windows.
- Preview frames are now received through `QVideoSink`, converted to `QImage`, and painted in a regular `QWidget`.
- The new preview path avoids the native presentation surface associated with the reproduced VRR / Adaptive Sync / NVIDIA G-SYNC failures, including black preview frames, flicker, and temporary full-monitor black screens.
- Qt hardware video decoding and hardware texture conversion remain at their default behavior; no NVIDIA G-SYNC application exclusion is required for the new preview path in testing.
- Lossless FFmpeg stream-copy export is unchanged.

## 0.2.35

- On Windows, VFR FastCut requests foreground activation after a successful Drag & Drop so playback shortcuts work immediately.
- Disabled Qt Multimedia hardware texture conversion at the earliest packaged-app startup stage to prevent green/corrupted preview frames on some Windows GPU/driver combinations.
- Hardware video decoding remains available; the compatibility change only affects the preview rendering path.
- Lossless FFmpeg stream-copy export is unchanged.

## 0.2.34

- Expanded supported input containers to MP4, MOV, M4V, MKV, WebM, TS/MTS/M2TS, AVI, FLV, MPG/MPEG and WMV.
- Added safe output defaults: MP4/MOV/MKV sources keep their container; other supported inputs default to MKV.
- Video export is limited to MP4, MOV and MKV; audio-only export remains MKA.
- Added explicit output muxer selection for the minimal FFmpeg runtime.
- Added dedicated MP4 muxer support plus AVI, FLV, MPEG program stream and ASF/WMV demuxers to the custom FFmpeg build.
- Updated built-in help and public documentation with supported input/output formats and stream-copy compatibility notes.

## 0.2.33

### Public-ready
- Added English and Russian interface localization.
- First launch selects Russian for a Russian Windows locale and English otherwise.
- Added a persistent language selector in the main window.
- Localized buttons, tooltips, status messages, dialogs, exporter progress and built-in F1 help.
- Added public repository documentation, MIT license, third-party notices and issue templates.

### Performance / cleanup
- Selected-segment video export limits FFprobe keyframe scanning to the requested interval instead of scanning the complete source file.
- Export cancellation now uses a dedicated `ExportCancelledError` / `cancelled` signal instead of matching a localized error string.
- Language switching is disabled while export is running so one export keeps one consistent language.

## 0.2.32
- Added independent `Export video` and `Export audio` options.
- Export buttons are disabled when both streams are deselected.
- Added audio-only `.mka` stream-copy export without video keyframe scanning.
- Preserved all source audio tracks when audio export is enabled.

## 0.2.31
- Moved export stream options under the export controls without increasing window height.

## 0.2.30
- Removed the redundant inline help paragraph after introducing built-in F1 help.

## 0.2.29
- Added selected-segment export.
- Added audio export toggle.
- Added built-in help (`F1`).

## 0.2.28
- Cleaned preview-prime timer lifecycle.
- Prevented Play/Pause button flicker during technical seek pauses.

## Earlier 0.2.x milestones
- Lossless multi-range stream-copy export with keyframe snapping.
- Timeline zoom, scrolling, segment selection, delete/restore, Undo/Redo.
- Drag & Drop, preview controls, cut navigation (`Q`/`E`).
- Stable fixed-layout Export/Cancel/progress controls.
- Windows taskbar export progress and robust FFmpeg process cancellation.