# Third-party component versions

This file records third-party component versions used for packaged VFR FastCut binary releases.

It complements `THIRD_PARTY_NOTICES.md` and the license texts in `LICENSES/`. It is not a substitute for the license terms that apply to redistributed third-party binaries.

## VFR FastCut v0.4.15 — Windows x64

### Build environment

- Python: `3.14.5`
- PyInstaller: `6.21.0`
- PySide6: `6.11.2`
- Qt: `6.11.2`

### Python runtime

- CPython `3.14.5`
- License: Python Software Foundation License / Python license stack
- The exact `LICENSE.txt` from the build interpreter must be copied into the portable package.

### Qt for Python / PySide6

- PySide6: `6.11.2`
- Qt: `6.11.2`
- Runtime model: dynamically loaded/shared Qt/PySide6 libraries in a PyInstaller `onedir` package
- Primary open-source license family used by the relevant Qt/PySide6 components: LGPLv3 / GPLv3 as provided by upstream

Expected baseline source archives retained for the release:

- `qtbase-everywhere-src-6.11.2.tar.xz`
- `qtmultimedia-everywhere-src-6.11.2.tar.xz`
- `pyside-setup-everywhere-src-6.11.2.tar.xz`

Known upstream SHA-256 values recorded during release preparation:

- `qtbase-everywhere-src-6.11.2.tar.xz`: `5b2e00eccaf5a4d8c14134ffa0ea8dfd0a35ae1ffc7f8d87fa4305a1ed23cf22`
- `pyside-setup-everywhere-src-6.11.2.tar.xz`: `cba47efbaad1bedd529725cbc14e21f156c7a19366f07b3edfbb076ffd7afdf8`

Record the downloaded `qtmultimedia` SHA-256 together with the final release asset before publication.

If the built portable directory contains a Qt module outside the baseline set, retain the corresponding source archive and update this file before publishing.

### Project FFmpeg / FFprobe runtime

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
- `--disable-autodetect`

The complete configure flags and build metadata are generated into `ffmpeg\bin\BUILD_INFO.txt`.

The exact source archive retained for release is:

```text
ffmpeg-9.0.2-source.tar.xz
```

### MinGW runtime DLLs bundled with the project FFmpeg runtime

`libwinpthread-1.dll`

- MSYS2 package: `mingw-w64-ucrt-x86_64-libwinpthread`
- Package version: `14.0.0.r409.g6de5d3b4d-1`
- License text: `LICENSES/MinGW-w64-libwinpthread-COPYING.txt`

`libgcc_s_seh-1.dll`

- MSYS2 package: `mingw-w64-ucrt-x86_64-gcc-libs`
- Package version: `16.2.0-3`
- License files:
  - `LICENSES/GCC-COPYING.LIB.txt`
  - `LICENSES/GCC-COPYING.RUNTIME.txt`
  - `LICENSES/GCC-COPYING3.txt`
  - `LICENSES/GCC-runtime-README.txt`

## VFR FastCut v0.2.34 / v0.2.35 / v0.2.36 — Windows x64

### Qt for Python / PySide6

- PySide6: `6.11.2`
- Qt: `6.11.2`
- Runtime model: shared Qt/PySide6 libraries in the PyInstaller `onedir` package
- License family: LGPLv3 / GPLv3, depending on the exact component

### FFmpeg / FFprobe

- FFmpeg: `9.0.2`
- Source SHA-256: `8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e`
- Build environment: MSYS2 UCRT64
- Compiler: `gcc.exe (Rev3, Built by MSYS2 project) 16.2.0`
- Linkage: shared FFmpeg libraries
- Recorded build license target: LGPL v2.1 or later

The 0.2.x runtime was stream-copy focused and enabled fewer audio-processing components than v0.4.15.

## VFR FastCut v0.2.33 — Windows x64

### Qt for Python / PySide6

- PySide6: `6.11.2`
- Qt: `6.11.2`

### FFmpeg / FFprobe

- Version string: `2026-09-17-git-7070fe638e-full_build-www.gyan.dev`
- FFmpeg commit: `7070fe638e`
- Distribution: Gyan.dev Windows full static build
- Compiler: `gcc 16.2.0 (Rev3, Built by MSYS2 project)`
- Recorded license: GPLv3

## Release process

For every packaged release:

1. Record exact Python, PyInstaller, PySide6 and Qt versions.
2. Record exact FFmpeg source/build configuration.
3. Record runtime DLL package versions.
4. Include applicable license texts.
5. Audit the actual portable directory.
6. Retain corresponding source required by redistributed copyleft components.
7. Update this file whenever a shipped component/version changes.
## OpenSSL

- OpenSSL 3.0.20 (7 Apr 2026)
- Bundled with the Python Windows runtime as libssl-3.dll and libcrypto-3.dll.
## Qt Multimedia FFmpeg runtime

- FFmpeg 7.1.3
- Bundled with Qt Multimedia 6.11.2 for media preview/playback.
- This runtime is separate from the project's minimal FFmpeg 9.0.2 export runtime.
## Release source archives for Qt / PySide6 6.11.2

- `qtbase-everywhere-src-6.11.2.tar.xz`
  - SHA-256: `5b2e00eccaf5a4d8c14134ffa0ea8dfd0a35ae1ffc7f8d87fa4305a1ed23cf22`
- `qtmultimedia-everywhere-src-6.11.2.tar.xz`
  - SHA-256: `967b5e02ec6b793cdb360622cd6e703132836af983208d678dae4b50f109cd9f`
- `pyside-setup-everywhere-src-6.11.2.tar.xz`
  - SHA-256: `cba47efbaad1bedd529725cbc14e21f156c7a19366f07b3edfbb076ffd7afdf8`
