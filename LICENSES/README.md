# Third-party license texts

This directory contains license texts and package-provided notices for third-party components redistributed with packaged VFR FastCut builds.

Exact component versions are recorded in [`../THIRD_PARTY_VERSIONS.md`](../THIRD_PARTY_VERSIONS.md).

## Current v0.5.0 release

Expected files in the portable package include:

- `LGPL-3.0.txt` — Qt/PySide6 LGPL text.
- `LGPL-2.1.txt` — project FFmpeg runtime.
- `Python-3.14.5-LICENSE.txt` — copied from the exact Python installation used for the release build; this license stack also carries applicable notices for components bundled with that Python runtime.
- `MinGW-w64-libwinpthread-COPYING.txt` — package-provided text for `libwinpthread-1.dll`.
- `GCC-COPYING.LIB.txt` — GCC runtime library license.
- `GCC-COPYING.RUNTIME.txt` — GCC Runtime Library Exception.
- `GCC-COPYING3.txt` — GPLv3 text distributed with the GCC runtime package.
- `GCC-runtime-README.txt` — package-provided GCC runtime licensing/readme.

`GPL-3.0.txt` remains in the repository for historical release records and for third-party components that may be dual-licensed upstream. Its presence does not by itself mean that VFR FastCut is GPL-licensed.

## Source availability

License texts and source availability are separate obligations.

For the v0.5.0 portable release, retain the corresponding source archives for the Qt/PySide6 components actually shipped, both FFmpeg runtimes that are redistributed, and the exact project FFmpeg source archive. The package helper removes optional QtPdf/QML/Quick/VirtualKeyboard families before the final audit so they are not part of the shipped dependency surface.

Release source assets are expected to include:

- project FFmpeg `9.0.2` source;
- Qt Multimedia FFmpeg `7.1.3` source;
- Qt `qtbase`, `qtmultimedia` and `qtsvg` `6.11.2` source;
- PySide6 `pyside-setup` `6.11.2` source.

These source archives may be published as separate GitHub Release assets rather than placed inside the application ZIP. FFmpeg's IJG attribution is recorded in `../THIRD_PARTY_NOTICES.md`.

Always audit the final `dist\VFRFastCut` directory before publication. If the binary inventory includes another copyleft dependency, add its notice/license/source information before releasing.

Official references:

- Qt for Python licensing: https://doc.qt.io/qtforpython-6/
- Qt LGPL obligations: https://www.qt.io/development/open-source-lgpl-obligations
- FFmpeg licensing: https://ffmpeg.org/doxygen/trunk/md_LICENSE.html
- Python licensing: https://docs.python.org/3/license.html
