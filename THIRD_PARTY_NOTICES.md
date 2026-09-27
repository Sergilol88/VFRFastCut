# Third-party software notices

VFR FastCut's own source code is licensed under the MIT License. Packaged Windows builds also redistribute third-party components under their own licenses.

This file is a practical redistribution record, not legal advice. Exact versions used for packaged releases are recorded in `THIRD_PARTY_VERSIONS.md`.

## Python runtime — v0.4.15

The PyInstaller portable build contains the CPython runtime used to build the application.

Recorded v0.4.15 version:

- Python `3.14.5`

The final portable package must include the exact `LICENSE.txt` from that Python installation, stored under `LICENSES/`.

Official licensing information:
- https://docs.python.org/3/license.html
- https://www.python.org/psf/about/legal-and-policies/

## Qt for Python / PySide6 and Qt — v0.4.15

VFR FastCut uses PySide6 / Qt for Python and Qt modules including QtCore, QtGui, QtWidgets and QtMultimedia.

Recorded versions:

- PySide6 `6.11.2`
- Qt `6.11.2`

The application is distributed as a PyInstaller `onedir` package. Qt/PySide6 libraries remain separate dynamically loaded files instead of being statically linked into VFR FastCut.

The portable package must include the applicable LGPL/GPL license texts and a prominent third-party notice.

For LGPL compliance, corresponding source for the Qt/PySide6 libraries actually shipped with the application must remain available under project control for the corresponding release. The release checklist therefore retains the expected baseline official source archives for `qtbase`, `qtmultimedia` and `pyside-setup`, and requires a final binary inventory check for any additional Qt modules.

Official licensing information:
- https://doc.qt.io/qtforpython-6/
- https://www.qt.io/development/open-source-lgpl-obligations
- https://www.qt.io/faq/qt-open-source-licensing

## FFmpeg / FFprobe — v0.4.15

VFR FastCut invokes its project FFmpeg / FFprobe runtime as external command-line programs.

The v0.4.15 Windows portable package uses a project-specific minimal runtime built from the official FFmpeg `9.0.2` release source.

Recorded build properties:

- official FFmpeg 9.0.2 source tarball;
- shared FFmpeg DLLs;
- `--disable-gpl`;
- `--disable-nonfree`;
- `--disable-version3`;
- external library autodetection disabled;
- only required local protocols, muxers/demuxers, audio decoders, native AAC encoder and audio filters enabled;
- video processing in VFR FastCut remains stream-copy;
- recorded build license target: LGPL v2.1 or later.

Compared with the older 0.2.x runtime, v0.4.15 intentionally enables a limited audio-processing subset required for Volume, Fade and Main Mix. It does **not** enable GPL or nonfree components.

The build recipe is stored in `tools/ffmpeg-minimal/`. Complete configure flags, source SHA-256, compiler information and the exact MSYS2 runtime package versions are generated into `BUILD_INFO.txt`.

The portable package includes:

- `ffmpeg\bin\COPYING.LGPLv2.1`
- `LICENSES\LGPL-2.1.txt`

The exact `ffmpeg-9.0.2-source.tar.xz` used by the build must be retained and published with the corresponding release assets or otherwise kept available from a project-controlled location.

FFmpeg's upstream license documentation notes that portions of libavcodec are derived from Independent JPEG Group (IJG) code and require IJG credit when distributing executables. Accordingly:

> Portions of FFmpeg are based in part on the work of the Independent JPEG Group.

Official FFmpeg licensing information:
- https://ffmpeg.org/legal.html
- https://ffmpeg.org/doxygen/trunk/md_LICENSE.html

## MinGW runtime DLLs used by project FFmpeg — v0.4.15

The custom FFmpeg runtime bundles:

### libwinpthread-1.dll

Recorded source package:

- `mingw-w64-ucrt-x86_64-libwinpthread`
- version `14.0.0.r409.g6de5d3b4d-1`

Package-provided license text:

- `LICENSES/MinGW-w64-libwinpthread-COPYING.txt`

### libgcc_s_seh-1.dll

Recorded source package:

- `mingw-w64-ucrt-x86_64-gcc-libs`
- version `16.2.0-3`

Package-provided license files:

- `LICENSES/GCC-COPYING.LIB.txt`
- `LICENSES/GCC-COPYING.RUNTIME.txt`
- `LICENSES/GCC-COPYING3.txt`
- `LICENSES/GCC-runtime-README.txt`

## PyInstaller

Recorded v0.4.15 build tool:

- PyInstaller `6.21.0`

PyInstaller is used only to create the portable executable bundle. Its bootloader exception permits generated application bundles to be distributed under the application's license, subject to the licenses of bundled dependencies. PyInstaller's own documentation states that the generated application does not need to include PyInstaller's license file or acknowledgement.

Official information:
- https://pyinstaller.org/en/stable/license.html

## Final portable-binary inventory

Third-party compliance must follow the **actual files shipped**, not only Python imports.

Before publishing a release, run `tools/release/audit-portable.ps1` against `dist\VFRFastCut` and review all unexpected DLLs/plugins.

Qt Multimedia can introduce multimedia backend dependencies. If FFmpeg-family libraries are present outside VFR FastCut's own `ffmpeg\bin`, treat that runtime as a separate redistributed dependency and retain the corresponding license/source information.

## Historical FFmpeg runtime — v0.2.33

The v0.2.33 Windows x64 package used:

- `ffmpeg version 2026-09-17-git-7070fe638e-full_build-www.gyan.dev`
- FFmpeg commit `7070fe638e`
- Gyan.dev full static build
- GCC `16.2.0 (Rev3, Built by MSYS2 project)`
- recorded GPLv3 licensing for that redistributed build

This historical record is retained because published binaries do not change when newer releases use another runtime.