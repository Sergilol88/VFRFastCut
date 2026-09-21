# Changelog

All notable changes to VFR FastCut are documented here.

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
