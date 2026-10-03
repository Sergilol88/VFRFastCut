# Third-party component versions

This file records third-party component versions used for packaged VFR FastCut binary releases.

It complements `THIRD_PARTY_NOTICES.md` and the license texts in `LICENSES/`. It is not a substitute for the license terms that apply to redistributed third-party binaries.

## VFR FastCut v0.5.0 — Windows x64

### Build environment

- Python: `3.14.5`
- PyInstaller: `6.21.0`
- PyInstaller hooks contrib: `2026.8`
- PySide6: `6.11.2`
- Qt: `6.11.2`
- Project FFmpeg / FFprobe: `9.0.2`

### Python runtime

- CPython `3.14.5`
- License: Python Software Foundation License / Python license stack
- The exact `LICENSE.txt` from the build interpreter is copied into the portable package as `LICENSES/Python-3.14.5-LICENSE.txt`.
- The Windows Python runtime also contributes OpenSSL runtime DLLs; the Python license stack retained from the exact build interpreter contains the applicable bundled-component notices.

### Qt for Python / PySide6

- PySide6: `6.11.2`
- Qt: `6.11.2`
- Runtime model: dynamically loaded/shared Qt/PySide6 libraries in a PyInstaller `onedir` package
- Primary open-source license family used by the relevant Qt/PySide6 components: LGPLv3 / GPLv3 as provided by upstream

The final v0.5.0 package is intentionally pruned after PyInstaller collection. Optional QtPdf, QML, Quick and VirtualKeyboard artifacts are removed because VFR FastCut does not import or use those families. The release audit fails if they reappear.

Qt module families expected to remain after pruning are covered by these source archives:

- `qtbase-everywhere-src-6.11.2.tar.xz`
- `qtmultimedia-everywhere-src-6.11.2.tar.xz`
- `qtsvg-everywhere-src-6.11.2.tar.xz`
- `pyside-setup-everywhere-src-6.11.2.tar.xz`

Recorded SHA-256 values:

- `qtbase-everywhere-src-6.11.2.tar.xz`: `5b2e00eccaf5a4d8c14134ffa0ea8dfd0a35ae1ffc7f8d87fa4305a1ed23cf22`
- `qtmultimedia-everywhere-src-6.11.2.tar.xz`: `967b5e02ec6b793cdb360622cd6e703132836af983208d678dae4b50f109cd9f`
- `qtsvg-everywhere-src-6.11.2.tar.xz`: `d594337feca84c26fb67fe87b85e6a5c12fda404b611d905f9d138210c311876`
- `pyside-setup-everywhere-src-6.11.2.tar.xz`: `cba47efbaad1bedd529725cbc14e21f156c7a19366f07b3edfbb076ffd7afdf8`

### Qt Multimedia FFmpeg runtime

Qt Multimedia 6.11.2 ships a separate FFmpeg runtime used for preview/playback. The audited portable package contains:

- `PySide6/avcodec-61.dll`
- `PySide6/avformat-61.dll`
- `PySide6/avutil-59.dll`
- `PySide6/swresample-5.dll`
- `PySide6/swscale-8.dll`

These library major versions correspond to the FFmpeg 7.1 branch. The current PySide6 6.11.2 runtime has been recorded as FFmpeg `7.1.3`. This runtime is separate from VFR FastCut's project FFmpeg 9.0.2 export runtime.

For source availability, retain and publish `ffmpeg-7.1.3.tar.xz` with the v0.5.0 release assets and record its SHA-256 together with the final uploaded asset.

### Project FFmpeg / FFprobe runtime

- FFmpeg: `9.0.2`
- Source: `https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz`
- Source SHA-256: `8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e`
- Build environment: MSYS2 UCRT64
- Compiler: `gcc.exe (Rev4, Built by MSYS2 project) 16.2.0`
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
- Package version recorded by the final v0.5.0 CI runtime: `14.0.0.r426.g4564ee4b5-1`
- License text: `LICENSES/MinGW-w64-libwinpthread-COPYING.txt`

`libgcc_s_seh-1.dll`

- MSYS2 package: `mingw-w64-ucrt-x86_64-libgcc`
- Package version recorded by the final v0.5.0 CI runtime: `16.2.0-4`
- License files:
  - `LICENSES/GCC-COPYING.LIB.txt`
  - `LICENSES/GCC-COPYING.RUNTIME.txt`
  - `LICENSES/GCC-COPYING3.txt`
  - `LICENSES/GCC-runtime-README.txt`

### OpenSSL runtime from CPython

The Windows Python runtime used for packaging contributes OpenSSL 3 runtime DLLs (`libssl-3*.dll`, `libcrypto-3*.dll`). The release audit records these binaries; their applicable notices are carried by the exact Python license stack copied from the build interpreter.

## VFR FastCut v0.4.15 — Windows x64

### Build environment

- Python: `3.14.5`
- PyInstaller: `6.21.0`
- PySide6: `6.11.2`
- Qt: `6.11.2`
- Project FFmpeg / FFprobe: `9.0.2`

### Historical project FFmpeg / MinGW metadata

The v0.4.15 project FFmpeg runtime used the same FFmpeg `9.0.2` source SHA-256 `8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e` and recorded:

- compiler: `gcc.exe (Rev3, Built by MSYS2 project) 16.2.0`;
- `mingw-w64-ucrt-x86_64-libwinpthread` `14.0.0.r409.g6de5d3b4d-1`;
- `mingw-w64-ucrt-x86_64-gcc-libs` `16.2.0-3`.

Historical published source assets for v0.4.15 include Qt/PySide6 6.11.2 source archives and the project FFmpeg 9.0.2 source archive.

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

The 0.2.x runtime was stream-copy focused and enabled fewer audio-processing components than v0.4.15/v0.5.0.

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
2. Record exact FFmpeg source/build configuration for both the project runtime and any Qt Multimedia FFmpeg runtime that is redistributed.
3. Record runtime DLL package versions.
4. Include applicable license texts/notices.
5. Audit the actual portable directory after any pruning step.
6. Retain corresponding source required by redistributed copyleft components.
7. Update this file whenever a shipped component/version changes.
