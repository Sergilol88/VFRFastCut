# Third-party component versions

This file records the third-party component versions used for packaged VFR FastCut binary releases.

It complements `THIRD_PARTY_NOTICES.md` and the license texts in `LICENSES/`. It is not a substitute for the license terms that apply to redistributed third-party binaries.

## VFR FastCut v0.2.34 / v0.2.35 / v0.2.36 — Windows x64

### Qt for Python / PySide6

- PySide6: `6.11.2`
- Qt: `6.11.2`
- Runtime model: shared Qt/PySide6 libraries in the PyInstaller `onedir` package
- License family: LGPLv3 / GPLv3, depending on the exact component

Official project information:
- https://doc.qt.io/qtforpython-6/
- https://download.qt.io/official_releases/QtForPython/

### FFmpeg / FFprobe

Starting with VFR FastCut v0.2.34, packaged Windows builds use the project-specific minimal runtime built from the official FFmpeg release source.

- FFmpeg: `9.0.2`
- Source: `https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz`
- Source SHA-256: `8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e`
- Build environment: MSYS2 UCRT64
- Compiler: `gcc.exe (Rev3, Built by MSYS2 project) 16.2.0`
- Linkage: shared FFmpeg libraries
- Recorded build license target: LGPL v2.1 or later
- `--disable-gpl`
- `--disable-nonfree`
- `--disable-version3`
- external library autodetection disabled

The complete configure flags and build metadata are generated into `ffmpeg\bin\BUILD_INFO.txt` in the portable package.

The exact source archive used for the build is retained as:
`ffmpeg-9.0.2-source.tar.xz`

It should be published with the corresponding Release assets or otherwise kept available from a project-controlled location.

### MinGW runtime DLLs bundled with the FFmpeg runtime

`libwinpthread-1.dll`

- MSYS2 package: `mingw-w64-ucrt-x86_64-libwinpthread`
- Package version: `14.0.0.r409.g6de5d3b4d-1`
- Package-provided license text: `LICENSES/MinGW-w64-libwinpthread-COPYING.txt`

`libgcc_s_seh-1.dll`

- MSYS2 package: `mingw-w64-ucrt-x86_64-gcc-libs`
- Package version: `16.2.0-3`
- Package-provided license files:
  - `LICENSES/GCC-COPYING.LIB.txt`
  - `LICENSES/GCC-COPYING.RUNTIME.txt`
  - `LICENSES/GCC-COPYING3.txt`
  - `LICENSES/GCC-runtime-README.txt`

## VFR FastCut v0.2.33 — Windows x64

### Qt for Python / PySide6

- PySide6: `6.11.2`
- Qt: `6.11.2`
- Runtime model: shared Qt/PySide6 libraries in the PyInstaller `onedir` package
- License family: LGPLv3 / GPLv3, depending on the exact component

### FFmpeg / FFprobe

- Version string: `2026-09-17-git-7070fe638e-full_build-www.gyan.dev`
- FFmpeg commit: `7070fe638e`
- Distribution: Gyan.dev Windows full static build
- Compiler: `gcc 16.2.0 (Rev3, Built by MSYS2 project)`
- Recorded license for that redistributed Gyan.dev build: GPLv3

The v0.2.33 entry is retained as historical release metadata and is not a description of the v0.2.34+ runtime.

## Release process

For each future packaged release:

1. Pin the exact PySide6 version used for the build.
2. Record the exact Qt runtime version.
3. Record the exact FFmpeg/FFprobe source and build configuration.
4. Record any additional runtime DLL package versions.
5. Include the applicable third-party license texts in the portable package.
6. Retain the build metadata and source reference for the exact shipped FFmpeg runtime.
7. Update this file whenever a shipped third-party version changes.
