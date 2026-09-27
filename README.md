# VFR FastCut

[Русская версия](README_RU.md)

**Windows 10/11 • Portable • No installation required**

**VFR FastCut** is a lightweight Windows utility for fast VFR video cutting with lossless video stream-copy and a practical audio timeline.

The main workflow is simple: add cuts, mark unwanted video segments, add or arrange audio when needed, preview the mix, and export through FFmpeg. Video remains stream-copied whenever possible; only audio that actually requires processing is re-encoded.

## Installation

VFR FastCut does **not** require installation.

1. Open the repository's **Releases** page.
2. Download the latest `VFRFastCut-vX.X.X-Windows-x64.zip`.
3. Extract the archive to any folder.
4. Run `VFRFastCut.exe`.

Python, PySide6/Qt and the project FFmpeg runtime are included in the portable build.

> **Windows SmartScreen:** unsigned builds may show a warning on first launch. If you trust the release downloaded from this repository, choose **More info → Run anyway**.

## Features

### Video

- Fast cutting without full video re-encoding.
- Designed for VFR recordings and stream VODs.
- Timeline zoom, horizontal scrolling, playhead navigation and cut markers.
- Delete / restore unwanted segments.
- Undo / Redo.
- Export all kept segments or only the selected segment.
- Video-only export is supported.
- Safe preview path based on `QVideoSink → QImage → QWidget`, avoiding the native video surface that caused black-screen / VRR issues in earlier builds.

### Audio

- Embedded source audio tracks are shown directly under the video timeline.
- External audio files can be added and positioned by dragging them on the timeline.
- External clips can be trimmed from either edge.
- External clips can be duplicated for repeated SFX and deleted independently.
- The 10 most recently added external audio files are kept between sessions for quick reuse.
- Per-track volume, Fade In and Fade Out.
- Right-click any audio track for its audio settings.
- Play flags on the timeline control which visible tracks participate in the live preview mix and exported Main Mix.
- On video open, only the first embedded audio track is enabled in the mix by default.
- Newly added external audio is enabled in the mix by default.
- **Main Mix is enabled by default.**
- Separate audio stems are optional and disabled by default.
- Live preview mixes all currently enabled tracks so balance can be checked before export.

### Interface

- Top menus hold less-frequent commands; common editing controls remain in the main window.
- Context-sensitive Split / Remove Cut button.
- Context-sensitive Delete / Restore button.
- Drag & Drop.
- English and Russian UI.
- Built-in help (`F1`).
- Compact export result dialog with expandable technical details.

## Supported formats

### Video input containers

MP4, MOV, M4V, MKV, WebM, TS, MTS, M2TS, AVI, FLV, MPG/MPEG, WMV.

### Video output containers

MP4, MOV, MKV.

If the source is MP4, MOV or MKV, FastCut normally suggests the same container. Other supported video inputs default to MKV.

### External audio / media

The file picker accepts WAV, MP3, M4A, AAC, FLAC, OGG, Opus, MKA, MP4, MOV, MKV and WebM when they contain an audio stream. Actual decoding support depends on the codec subset enabled in the bundled FFmpeg runtime.

Audio-only output uses MKA.

Container support does not guarantee that every possible source codec can be stream-copied into every output container. MKV is the safest fallback when MP4/MOV rejects a stream.

## Main Mix, stems and "lossless" behavior

VFR FastCut is primarily a **lossless video cutter**.

- Video is copied without re-encoding during normal lossless export.
- Unchanged audio stems can also remain stream-copied.
- Main Mix is newly generated audio and is encoded to AAC stereo / 48 kHz.
- A track with changed Volume or Fade is processed and encoded to AAC.
- External audio timing, trim and offset are applied to the mix and stems.
- Main Mix uses a limiter to protect against digital clipping when several loud tracks overlap.

Because the exported Main Mix contains real audio processing, "Lossless Export" does **not** mean that every audio stream is always bit-for-bit copied. The completion dialog can show the detailed processing report.

## How lossless video cutting works

VFR FastCut does not decode and re-encode the video during normal export. FFmpeg copies already encoded video packets into the output file.

Inter-frame codecs depend on keyframes, so requested video cut boundaries are snapped to suitable keyframes. The actual exported boundary can therefore differ slightly from the requested position. This is an expected limitation of stream-copy video editing.

Audio-only and processed audio operations use audio packet / filter timing and are not limited by video keyframes in the same way.

## Audio timeline basics

- Click `▶ / ▷` beside an audio row to include or exclude that track from the preview/Main Mix.
- Drag an external audio block to change its project position.
- Drag the left or right edge of an external block to trim it.
- Right-click an audio block for Volume / Fade controls.
- Right-click an external block to create a copy.
- Right-click a copied external block to delete that copy.

Tracks disabled in the available-audio selection are hidden from the timeline.

## Shortcuts

| Action | Shortcut |
| --- | --- |
| Open video | `Ctrl+O` |
| Reset project | `Ctrl+N` |
| Play / Pause | `Space` |
| Mute preview | `M` |
| Split | `S` |
| Remove cut | `Shift+S` |
| Delete / restore selected segment | `Delete` |
| Undo / Redo | `Ctrl+Z` / `Ctrl+Y` |
| Previous / next cut | `Q` / `E` |
| Seek ±1 second | `←` / `→` |
| Help | `F1` |
| Timeline zoom | `Ctrl + mouse wheel` |
| Timeline scroll | Mouse wheel |

## Interface language

On first launch, VFR FastCut uses Russian when Windows reports a Russian locale; otherwise English is used.

The language can be changed from **View → Language** and is saved between launches.

## Running from source

This section is for developers and contributors. Regular users should use the portable ZIP from **Releases**.

Release environment recorded for v0.4.15:

- Windows 10/11 x64
- Python `3.14.5`
- PySide6 `6.11.2`
- Qt `6.11.2`
- PyInstaller `6.21.0`
- FFmpeg / FFprobe `9.0.2` project-specific minimal runtime

Install the pinned Python dependency:

```powershell
python -m pip install -r requirements.txt
```

Run:

```powershell
python vfr_fastcut.py
```

FFmpeg / FFprobe are searched in this order:

1. application directory / packaged `ffmpeg\bin`,
2. `tools\ffmpeg-minimal\runtime` when running from the repository,
3. `C:\ffmpeg\bin`,
4. `PATH`.

## Building for Windows

See [BUILD.md](BUILD.md).

## Current limitations

- Lossless video cuts are keyframe-aligned, not frame-exact.
- Video overlays, transitions, compositing and other video filters are outside the current lossless-cut workflow.
- Audio waveforms are not generated; audio is represented as timeline clips.
- Live preview uses multiple Qt audio players. Normal mixes should closely match export, but heavily overloaded peaks may differ slightly because exported Main Mix passes through FFmpeg's limiter.
- Windows is the currently tested release platform.

## Bugs and feature requests

Please use GitHub Issues. Include:

- VFR FastCut version,
- Windows version,
- source container / codecs if known,
- exact reproduction steps,
- whether the problem affects preview, editing or export.

## License

VFR FastCut source code is licensed under the [MIT License](LICENSE).

Portable builds redistribute third-party software under their own licenses, including Python, Qt for Python / PySide6, Qt and FFmpeg. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [THIRD_PARTY_VERSIONS.md](THIRD_PARTY_VERSIONS.md) and the `LICENSES` directory.

The v0.4.15 release process also retains the corresponding FFmpeg source and the LGPL source archives required for the shipped Qt/PySide6 components.