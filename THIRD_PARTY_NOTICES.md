# Third-party software notices

VFR FastCut's own source code is licensed under the MIT License. The project also uses and, in packaged Windows releases, may redistribute third-party components under their own licenses.

This file is a practical redistribution checklist, not legal advice. Always verify the exact versions and binaries included in each Release. Exact versions used for packaged releases are recorded in `THIRD_PARTY_VERSIONS.md`.

## Qt for Python / PySide6

VFR FastCut uses PySide6 / Qt for Python and Qt modules including QtCore, QtGui, QtWidgets and QtMultimedia.

Qt for Python Community Edition is offered under LGPLv3/GPLv3 (and Qt also offers commercial licensing). Binary distributions must comply with the license terms that apply to the exact Qt/PySide6 components shipped.

For the VFR FastCut v0.2.33 Windows x64 package, the recorded versions are:

- PySide6 `6.11.2`
- Qt `6.11.2`

Official licensing information:
- https://doc.qt.io/qtforpython-6/
- https://doc.qt.io/qt-6/licensing.html

When publishing a binary package:

- include the applicable LGPL/GPL license texts;
- keep the Qt/PySide6 shared libraries separable from the application where applicable;
- make the corresponding source material required by the applicable license available through release assets or another project-controlled location;
- record the exact PySide6 and Qt versions in `THIRD_PARTY_VERSIONS.md`.

The project intentionally uses a PyInstaller `onedir` distribution, which keeps Qt/PySide6 runtime files visible as separate files instead of hiding everything inside a single executable.

## FFmpeg / FFprobe

VFR FastCut invokes `ffmpeg.exe` and `ffprobe.exe` as external command-line tools.

Upstream FFmpeg is primarily LGPLv2.1+, but a build becomes GPL when GPL components are enabled. Therefore the license of a redistributed FFmpeg binary depends on how that binary was built.

Official FFmpeg license information:
- https://ffmpeg.org/legal.html
- https://ffmpeg.org/doxygen/trunk/md_LICENSE.html

### Gyan.dev Windows build used by v0.2.33

The VFR FastCut v0.2.33 Windows x64 package was built with:

- `ffmpeg version 2026-09-17-git-7070fe638e-full_build-www.gyan.dev`
- FFmpeg commit `7070fe638e`
- Gyan.dev full static build
- GCC `16.2.0 (Rev3, Built by MSYS2 project)`
- GPLv3 licensing for the redistributed Gyan.dev build

Build/source information:
- https://www.gyan.dev/ffmpeg/builds/
- https://github.com/FFmpeg/FFmpeg/commit/7070fe638e

When redistributing a packaged build containing this FFmpeg/FFprobe binary set:

- include the GPLv3 license text;
- record the exact build identifier in `THIRD_PARTY_VERSIONS.md`;
- make the corresponding source material required by the GPL available through release assets or another project-controlled location.

Because Gyan.dev `full_build` includes many optional libraries that VFR FastCut 0.2.x does not need for stream-copy editing, future releases may switch to a smaller purpose-built FFmpeg package with a simpler dependency and licensing footprint.

## PyInstaller

PyInstaller is a build tool, not a runtime Python dependency of VFR FastCut source. PyInstaller is GPL-licensed with an exception that permits distributing applications created with it under the application's own license, subject to the licenses of bundled dependencies.

Official information:
- https://pyinstaller.org/en/stable/license.html
