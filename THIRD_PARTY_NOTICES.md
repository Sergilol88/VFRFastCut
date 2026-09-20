# Third-party software notices

VFR FastCut's own source code is licensed under the MIT License. The project also uses or may redistribute third-party components under their own licenses.

This file is a practical redistribution checklist, not legal advice. Always verify the exact versions and binaries included in a Release.

## Qt for Python / PySide6

VFR FastCut uses PySide6 / Qt for Python and Qt modules including QtCore, QtGui, QtWidgets and QtMultimedia.

Qt for Python Community Edition is offered under LGPLv3/GPLv3 (and Qt also offers commercial licensing). Binary distributions must comply with the license terms that apply to the exact Qt/PySide6 components shipped.

Official licensing information:
- https://doc.qt.io/qtforpython-6/
- https://doc.qt.io/qt-6/licensing.html

When publishing a binary package, include the applicable LGPL/GPL license texts and source notices. Keeping the Qt/PySide6 DLLs as separate files in the `onedir` distribution also makes the dependency boundary explicit.

## FFmpeg / FFprobe

VFR FastCut invokes `ffmpeg.exe` and `ffprobe.exe` as external command-line tools.

Upstream FFmpeg is primarily LGPLv2.1+, but a build becomes GPL when GPL components are enabled. Therefore the license of a redistributed FFmpeg binary depends on how that binary was built.

Official FFmpeg license information:
- https://ffmpeg.org/legal.html
- https://ffmpeg.org/doxygen/trunk/md_LICENSE.html

### Gyan.dev Windows builds

If the Windows Release bundles the commonly used Gyan.dev static FFmpeg builds, note that the current Gyan build page states that its static build variants are licensed as GPLv3.

Build/source information:
- https://www.gyan.dev/ffmpeg/builds/
- https://github.com/FFmpeg/FFmpeg

For a Release that bundles such a build, include the applicable GPLv3 license text and provide clear source/build information for the exact FFmpeg version shipped. The `LICENSES/README.md` file lists official license-text locations to use when preparing a binary Release.

## PyInstaller

PyInstaller is a build tool, not a runtime Python dependency of VFR FastCut source. PyInstaller is GPL-licensed with an exception that permits distributing applications created with it under the application's own license, subject to the licenses of bundled dependencies.

Official information:
- https://pyinstaller.org/en/stable/license.html
