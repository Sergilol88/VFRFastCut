# Third-party component versions

This file records the third-party component versions used for packaged VFR FastCut binary releases.

It complements `THIRD_PARTY_NOTICES.md` and the license texts in `LICENSES/`. It is not a substitute for the license terms or any corresponding-source obligations that apply to redistributed third-party binaries.

## VFR FastCut v0.2.33 — Windows x64

### Qt for Python / PySide6

- PySide6: `6.11.2`
- Qt: `6.11.2`
- Runtime model: shared Qt/PySide6 libraries in the PyInstaller `onedir` package
- License family: LGPLv3 / GPLv3, depending on the exact component

Official project information:
- https://doc.qt.io/qtforpython-6/
- https://download.qt.io/official_releases/QtForPython/

### FFmpeg / FFprobe

- Version string: `2026-09-17-git-7070fe638e-full_build-www.gyan.dev`
- FFmpeg commit: `7070fe638e`
- Distribution: Gyan.dev Windows full static build
- Compiler: `gcc 16.2.0 (Rev3, Built by MSYS2 project)`
- License for this redistributed Gyan.dev build: GPLv3

Project/build information:
- https://www.gyan.dev/ffmpeg/builds/
- https://github.com/FFmpeg/FFmpeg/commit/7070fe638e

## Release process

For each future packaged release:

1. Pin the exact PySide6 version used for the build.
2. Record the exact Qt runtime version.
3. Record the full `ffmpeg -version` identifier and build source.
4. Include the applicable license texts in the portable package.
5. Make the corresponding source material required by the applicable third-party licenses available through release assets or another project-controlled location.
6. Update this file when the shipped third-party versions change.
