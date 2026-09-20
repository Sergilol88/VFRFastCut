# Third-party license texts

This directory contains license texts and package-provided notices for third-party components redistributed with packaged VFR FastCut builds.

Exact third-party versions recorded for packaged releases are listed in [`../THIRD_PARTY_VERSIONS.md`](../THIRD_PARTY_VERSIONS.md).

## Files used by current / historical releases

- `LGPL-3.0.txt` — Qt/PySide6 LGPL text used by current packaged builds.
- `GPL-3.0.txt` — retained for historical v0.2.33 third-party components.
- `LGPL-2.1.txt` — FFmpeg minimal runtime used by v0.2.34.
- `MinGW-w64-libwinpthread-COPYING.txt` — package-provided license text for `libwinpthread-1.dll`.
- `GCC-COPYING.LIB.txt` — package-provided GCC runtime license text.
- `GCC-COPYING.RUNTIME.txt` — package-provided GCC Runtime Library Exception text.
- `GCC-COPYING3.txt` — package-provided GPLv3 text included with the GCC runtime package.
- `GCC-runtime-README.txt` — package-provided runtime licensing/readme file.

Before publishing a binary Release:

- record the exact versions/build identifiers in `THIRD_PARTY_VERSIONS.md`;
- keep the applicable license texts with the portable package;
- retain the build/source information required for the exact shipped third-party binaries.

Official references:
- Qt for Python licensing: https://doc.qt.io/qtforpython-6/
- FFmpeg licensing: https://ffmpeg.org/doxygen/trunk/md_LICENSE.html
