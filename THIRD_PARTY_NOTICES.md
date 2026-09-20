# Third-party software notices

VFR FastCut's own source code is licensed under the MIT License. Packaged Windows builds also redistribute third-party components under their own licenses.

This file is a practical redistribution record, not legal advice. Exact versions used for packaged releases are recorded in `THIRD_PARTY_VERSIONS.md`.

## Qt for Python / PySide6

VFR FastCut uses PySide6 / Qt for Python and Qt modules including QtCore, QtGui, QtWidgets and QtMultimedia.

For v0.2.34 the recorded versions are:

- PySide6 `6.11.2`
- Qt `6.11.2`

The portable application is intentionally distributed as a PyInstaller `onedir` package so Qt/PySide6 runtime files remain separate files in the application directory.

Official licensing information:
- https://doc.qt.io/qtforpython-6/
- https://doc.qt.io/qt-6/licensing.html

The applicable Qt/PySide6 license texts and notices must remain with redistributed binary builds.

## FFmpeg / FFprobe — v0.2.34

VFR FastCut invokes `ffmpeg.exe` and `ffprobe.exe` as external command-line programs.

Starting with v0.2.34, the Windows portable package uses a project-specific minimal FFmpeg runtime built from the official FFmpeg `9.0.2` release source.

Recorded build properties:

- official FFmpeg 9.0.2 source tarball
- shared FFmpeg DLLs
- `--disable-gpl`
- `--disable-nonfree`
- `--disable-version3`
- external library autodetection disabled
- encoders and decoders disabled for the 0.2.x stream-copy use case
- recorded build license target: LGPL v2.1 or later

The build recipe is stored in `tools/ffmpeg-minimal/`, and the complete build flags and source SHA-256 are recorded in the generated `BUILD_INFO.txt`.

The portable package includes:
- `ffmpeg\bin\COPYING.LGPLv2.1`
- `LICENSES\LGPL-2.1.txt`

The exact source archive used to build the runtime is retained as `ffmpeg-9.0.2-source.tar.xz` and should be published with the corresponding Release assets or otherwise kept available from a project-controlled location.

Official FFmpeg licensing information:
- https://ffmpeg.org/legal.html
- https://ffmpeg.org/doxygen/trunk/md_LICENSE.html

## MinGW runtime DLLs — v0.2.34

The custom FFmpeg runtime also bundles two runtime DLLs from the MSYS2 UCRT64 toolchain:

### libwinpthread-1.dll

Recorded source package:
- `mingw-w64-ucrt-x86_64-libwinpthread`
- version `14.0.0.r409.g6de5d3b4d-1`

Package-provided license text included in the project:
- `LICENSES/MinGW-w64-libwinpthread-COPYING.txt`

### libgcc_s_seh-1.dll

Recorded source package:
- `mingw-w64-ucrt-x86_64-gcc-libs`
- version `16.2.0-3`

Package-provided license files included in the project:
- `LICENSES/GCC-COPYING.LIB.txt`
- `LICENSES/GCC-COPYING.RUNTIME.txt`
- `LICENSES/GCC-COPYING3.txt`
- `LICENSES/GCC-runtime-README.txt`

These files are copied from the installed MSYS2 packages used for the release build.

## Historical FFmpeg runtime — v0.2.33

The v0.2.33 Windows x64 package used:

- `ffmpeg version 2026-09-17-git-7070fe638e-full_build-www.gyan.dev`
- FFmpeg commit `7070fe638e`
- Gyan.dev full static build
- GCC `16.2.0 (Rev3, Built by MSYS2 project)`
- recorded GPLv3 licensing for that redistributed build

This historical record is retained because published v0.2.33 binaries do not change when later releases switch runtimes.

## PyInstaller

PyInstaller is used as the Windows build tool. Its bootloader exception permits distribution of applications created with it subject to the licenses of the application and bundled dependencies.

Official information:
- https://pyinstaller.org/en/stable/license.html
