# VFR FastCut

[Русская версия](README_RU.md)

**Windows 10/11 • Portable • No installation required**

**VFR FastCut** is a lightweight Windows utility for fast lossless cutting of VFR video, especially stream recordings and VODs.

The core idea is simple: add cuts, mark unwanted segments, and export the result through FFmpeg **stream copy (`-c copy`)** without re-encoding the whole video.

## Installation

VFR FastCut does **not** require installation.

1. Open the repository's **Releases** page.
2. Download the latest `VFRFastCut-vX.X.X-Windows-x64.zip` archive.
3. Extract the archive to any folder.
4. Run `VFRFastCut.exe`.

Python, FFmpeg, and other runtime components do not need to be installed separately — everything required for the portable build is included in the archive.

> **Windows SmartScreen:** unsigned builds may show a warning on first launch. If you trust the release downloaded from this repository, choose **More info → Run anyway**.

### Updating

Download the newer Release and extract it to a new folder or replace the previous portable folder. Application settings such as the selected interface language are stored separately and should remain available after replacing the program files.

## Features

- Lossless video cutting without full re-encoding.
- Designed to work well with VFR recordings and stream VODs.
- Timeline with zoom, horizontal scrolling, cuts, segment selection, and playhead navigation.
- Export all kept segments or only the currently selected segment.
- Export video + audio, video only, or audio only.
- Audio-only export to `.mka` while preserving the source audio codec and stream parameters.
- Preserves all source audio tracks when audio export is enabled.
- Drag & Drop.
- Undo / Redo and restore for deleted segments.
- Preview volume control and Mute.
- English and Russian interface with automatic first-run language selection and persistent manual choice.
- Built-in help (`F1`) covering features, shortcuts, and lossless-mode limitations.
- No account, cloud service, or API token required.

## How lossless cutting works

VFR FastCut does not decode and re-encode the video during normal lossless export. FFmpeg copies already encoded packets into a new file.

Because inter-frame video codecs depend on keyframes, video cut boundaries are snapped to suitable keyframes. The actual exported boundary can therefore differ slightly from the requested position. This is an expected limitation of stream-copy editing without re-encoding.

Audio-only export does not depend on video keyframes, so its boundaries are packet-based.

## Shortcuts

| Action | Shortcut |
| --- | --- |
| Open video | `Ctrl+O` |
| Reset project | `Ctrl+N` |
| Play / Pause | `Space` |
| Mute preview | `M` |
| Split | `S` |
| Delete selected segment | `Delete` |
| Undo / Redo | `Ctrl+Z` / `Ctrl+Y` |
| Previous / next cut | `Q` / `E` |
| Seek ±1 second | `←` / `→` |
| Help | `F1` |
| Timeline zoom | `Ctrl + mouse wheel` |
| Timeline scroll | Mouse wheel |

## Interface language

On first launch, VFR FastCut uses Russian when Windows reports a Russian locale; otherwise it defaults to English.

The language can be changed at any time from the selector in the upper-right area of the window. The selected language is saved between launches.

## Running from source

This section is for developers and contributors. Regular users should use the portable ZIP from **Releases** instead.

- Primary target: Windows 10/11
- Python 3.10+
- PySide6 6.7+
- FFmpeg and FFprobe

Install the Python dependency:

```powershell
python -m pip install -r requirements.txt
```

Run:

```powershell
python vfr_fastcut.py
```

FFmpeg/FFprobe are searched in this order:

1. `ffmpeg\bin\` next to the application,
2. `C:\ffmpeg\bin\`,
3. `PATH`.

## Building for Windows

See [BUILD.md](BUILD.md) for the portable PyInstaller build instructions.

## Current limitations

- Lossless video cuts are keyframe-aligned.
- Text overlays, transitions, filters, and frame-exact video editing require re-encoding and are intentionally deferred to the 0.3.x line.
- Preview uses Qt Multimedia / `QVideoWidget`; some VRR/G-SYNC configurations may flicker. On affected systems, using Fixed Refresh for `VFRFastCut.exe` in the NVIDIA application profile can help.
- Windows is the currently tested release platform. Other operating systems are not yet treated as supported targets.

## Bugs and feature requests

Please use GitHub Issues. For bug reports, include:

- VFR FastCut version,
- Windows version,
- source container/codec if known,
- exact reproduction steps,
- whether the problem affects preview, editing, or export.

## License

VFR FastCut source code is licensed under the [MIT License](LICENSE).

The project uses third-party components with their own licenses, including Qt for Python / PySide6 and FFmpeg. Before redistributing compiled binaries, see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
