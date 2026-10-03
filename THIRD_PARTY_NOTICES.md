# Third-party software notices

VFR FastCut's own source code is licensed under the MIT License. Packaged Windows builds also redistribute third-party components under their own licenses.

This file is a practical redistribution record, not legal advice. Exact versions used for packaged releases are recorded in `THIRD_PARTY_VERSIONS.md`.

## Python runtime — v0.5.0

The PyInstaller portable build contains the CPython runtime used to build the application.

Recorded v0.5.0 version:

- Python `3.14.5`

The final portable package includes the exact `LICENSE.txt` from that Python installation under `LICENSES/`. The Windows Python runtime also contributes OpenSSL runtime DLLs; applicable bundled-component notices are retained through that exact Python license stack.

Official licensing information:
- https://docs.python.org/3/license.html
- https://www.python.org/psf/about/legal-and-policies/

## Qt for Python / PySide6 and Qt — v0.5.0

VFR FastCut uses PySide6 / Qt for Python and Qt modules required by QtCore, QtGui, QtWidgets and QtMultimedia-based preview/playback.

Recorded versions:

- PySide6 `6.11.2`
- Qt `6.11.2`

The application is distributed as a PyInstaller `onedir` package. Qt/PySide6 libraries remain separate dynamically loaded files instead of being statically linked into VFR FastCut.

The portable package includes applicable LGPL/GPL license texts and a prominent third-party notice. Corresponding source for the Qt/PySide6 libraries actually shipped with the application is retained under project control for the matching release.

The v0.5.0 packaging step intentionally removes optional QtPdf, QML, Quick and VirtualKeyboard artifacts collected by generic PyInstaller hooks because VFR FastCut does not use those families. The release audit fails if those optional artifacts reappear. The remaining expected Qt/PySide6 families are covered by retained source archives for `qtbase`, `qtmultimedia`, `qtsvg` and `pyside-setup`.

Official licensing information:
- https://doc.qt.io/qtforpython-6/
- https://www.qt.io/development/open-source-lgpl-obligations
- https://www.qt.io/faq/qt-open-source-licensing

## Qt Multimedia FFmpeg runtime — v0.5.0

Qt Multimedia 6.11.2 includes a separate FFmpeg runtime used by VFR FastCut for media preview/playback. The audited portable package contains FFmpeg-family DLLs under `PySide6\` with library major versions corresponding to the FFmpeg 7.1 branch; the current PySide6 runtime has been recorded as FFmpeg `7.1.3`.

This Qt Multimedia FFmpeg runtime is distinct from the project FFmpeg 9.0.2 runtime used for export. The matching FFmpeg 7.1.3 source archive is retained/published with the release source assets.

Official FFmpeg licensing information:
- https://ffmpeg.org/legal.html
- https://ffmpeg.org/doxygen/trunk/md_LICENSE.html

## Project FFmpeg / FFprobe — v0.5.0

VFR FastCut invokes its project FFmpeg / FFprobe runtime as external command-line programs for export and media probing.

The v0.5.0 Windows portable package uses a project-specific minimal runtime built from the official FFmpeg `9.0.2` release source.

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

Compared with the older stream-copy-only runtime, v0.5.0 intentionally enables a limited audio-processing subset required for Volume, Fade and Main Mix. It does **not** enable GPL or nonfree components.

The build recipe is stored in `tools/ffmpeg-minimal/`. Complete configure flags, source SHA-256, compiler information and exact MSYS2 runtime package owners/versions are generated into `BUILD_INFO.txt`.

The portable package includes:

- `ffmpeg\bin\COPYING.LGPLv2.1`
- `LICENSES\LGPL-2.1.txt`

The exact `ffmpeg-9.0.2-source.tar.xz` used by the build is retained and published with the corresponding release assets.

FFmpeg's upstream license documentation notes that portions of libavcodec are derived from Independent JPEG Group (IJG) code and require IJG credit when distributing executables. Accordingly:

> Portions of FFmpeg are based in part on the work of the Independent JPEG Group.

## MinGW runtime DLLs used by project FFmpeg — v0.5.0

The custom FFmpeg runtime bundles `libwinpthread-1.dll` and `libgcc_s_seh-1.dll`. Exact package owners/versions are recorded dynamically in the shipped `ffmpeg\bin\BUILD_INFO.txt` and summarized in `THIRD_PARTY_VERSIONS.md`.

Applicable package-provided license files are included in `LICENSES/`:

- `MinGW-w64-libwinpthread-COPYING.txt`
- `GCC-COPYING.LIB.txt`
- `GCC-COPYING.RUNTIME.txt`
- `GCC-COPYING3.txt`
- `GCC-runtime-README.txt`

## PyInstaller

Recorded v0.5.0 build tool:

- PyInstaller `6.21.0`

PyInstaller is used only to create the portable executable bundle. Its bootloader exception permits generated application bundles to be distributed under the application's license, subject to the licenses of bundled dependencies. PyInstaller's own documentation states that the generated application does not need to include PyInstaller's license file or acknowledgement.

Official information:
- https://pyinstaller.org/en/stable/license.html

## Final portable-binary inventory

Third-party compliance follows the **actual files shipped**, not only Python imports.

Before publication, `tools/release/package-portable.ps1` prunes known-unused optional Qt components, runs `tools/release/audit-portable.ps1`, launches the portable executable as a short dependency smoke test, verifies the bundled project FFmpeg/FFprobe and then creates/re-opens the release ZIP.

The audit explicitly records Qt DLLs/plugins, project and Qt Multimedia FFmpeg-family DLLs, Python/OpenSSL candidates and the project FFmpeg build metadata.

## Historical FFmpeg runtime — v0.2.33

The v0.2.33 Windows x64 package used:

- `ffmpeg version 2026-09-17-git-7070fe638e-full_build-www.gyan.dev`
- FFmpeg commit `7070fe638e`
- Gyan.dev full static build
- GCC `16.2.0 (Rev3, Built by MSYS2 project)`
- recorded GPLv3 licensing for that redistributed build

This historical record is retained because published binaries do not change when newer releases use another runtime.
