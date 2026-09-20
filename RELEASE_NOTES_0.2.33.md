# VFR FastCut 0.2.33

This is the first **public-ready** VFR FastCut build.

## What's new

- English + Russian interface.
- Automatic first-run language selection based on Windows locale.
- Persistent language selector in the main window.
- Fully localized built-in F1 help, dialogs, tooltips, status messages and export progress.
- Faster selected-segment export: FFprobe scans keyframes only around the requested segment instead of the entire source video.
- Cleaner export cancellation logic using a dedicated cancellation signal.
- Public GitHub documentation, changelog, issue templates, MIT license and third-party notices.

## Existing 0.2.x features

- VFR-friendly lossless stream-copy cutting.
- Multi-range export without full re-encoding.
- Selected-segment export.
- Video + audio, video-only and audio-only (`.mka`) export.
- Multiple audio tracks preserved.
- Timeline zoom / scroll / cuts / selection.
- Drag & Drop, Undo/Redo, restore, preview volume/mute and cut navigation.

## Important

Video cuts in Lossless mode are keyframe-aligned and can differ slightly from the requested position. This is expected when using `-c copy` without re-encoding.
