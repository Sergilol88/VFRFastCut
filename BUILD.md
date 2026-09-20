# Building VFR FastCut on Windows

## 1. Install pinned Python dependencies

Release builds should use the exact dependency versions committed in `requirements.txt` so that the Qt/PySide6 runtime is reproducible.

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

For the v0.2.33 Windows x64 release:

```text
PySide6 6.11.2
Qt 6.11.2
```

Verify before building:

```powershell
python -c "import PySide6; print(PySide6.__version__)"
python -c "from PySide6.QtCore import qVersion; print(qVersion())"
```

## 2. Prepare FFmpeg

The current v0.2.33 binary release used the recorded Gyan.dev build. Its exact historical details remain in `THIRD_PARTY_VERSIONS.md`.

For future releases, the preferred target is the reproducible minimal LGPL FFmpeg runtime documented in:

```text
tools/ffmpeg-minimal/README.md
```

Build that runtime first and verify it against a real VFR/Twitch sample before packaging a release.

Until the switch is validated, the portable build can still bundle:

```text
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

For v0.2.33 the packaged binaries were:

```text
ffmpeg version 2026-09-17-git-7070fe638e-full_build-www.gyan.dev
FFmpeg commit: 7070fe638e
Gyan.dev full static build
GCC 16.2.0 (Rev3, Built by MSYS2 project)
License: GPLv3
```

Verify the exact FFmpeg build before every release:

```powershell
C:\ffmpeg\bin\ffmpeg.exe -version
C:\ffmpeg\bin\ffprobe.exe -version
```

Before redistributing third-party binaries, read `THIRD_PARTY_NOTICES.md`, update `THIRD_PARTY_VERSIONS.md`, and make the corresponding source material required by the applicable licenses available through release assets or another project-controlled location.

## 3. Build the portable onedir package

Run from the repository root:

```powershell
python -m PyInstaller --noconfirm --clean --onedir --windowed --contents-directory "." --name "VFRFastCut" --icon "VFRFastCut.ico" --add-data "VFRFastCut.ico;." --add-data "LICENSE;." --add-data "THIRD_PARTY_NOTICES.md;." --add-data "THIRD_PARTY_VERSIONS.md;." --add-data "README.md;." --add-data "README_RU.md;." --add-data "LICENSES;LICENSES" --add-binary "C:\ffmpeg\bin\ffmpeg.exe;ffmpeg\bin" --add-binary "C:\ffmpeg\bin\ffprobe.exe;ffmpeg\bin" vfr_fastcut.py
```

When the custom runtime is adopted, package the entire contents of `tools\ffmpeg-minimal\runtime\` into `ffmpeg\bin\` rather than only the two executables, because the custom LGPL build uses shared FFmpeg DLLs.

Result:

```text
dist\VFRFastCut\
```

Distribute the **whole folder**, normally as a ZIP archive.

## 4. Third-party compliance checklist

Before publishing a binary Release:

1. Confirm the exact PySide6 and Qt versions.
2. Confirm the exact FFmpeg/FFprobe build identifier.
3. Update `THIRD_PARTY_VERSIONS.md` when any shipped version changes.
4. Confirm the portable ZIP contains:
   - `LICENSE`
   - `THIRD_PARTY_NOTICES.md`
   - `THIRD_PARTY_VERSIONS.md`
   - `LICENSES/`
5. Make corresponding source material required by the licenses of the redistributed Qt/PySide6 and FFmpeg binaries available through Release assets or another project-controlled location.
6. Keep the source/build reference for the exact shipped FFmpeg binary set.

## 5. Portable smoke test

Before publishing a Release:

1. Temporarily rename `C:\ffmpeg` so the app cannot use the system copy.
2. Start `dist\VFRFastCut\VFRFastCut.exe`.
3. Open a sample VFR/Twitch VOD.
4. Test video + audio export.
5. Test video-only export.
6. Test audio-only `.mka` export.
7. Test selected-segment export.
8. Test Cancel Export.
9. Switch RU ↔ EN and restart the app to confirm language persistence.
10. Check that `F1` help follows the selected language.

## Notes

- `--onedir` is intentional: it starts faster, is easier to diagnose, and keeps Qt/FFmpeg files visible for license compliance and troubleshooting.
- Do not commit `build/` or `dist/` to the source repository. Publish compiled ZIPs through GitHub Releases instead.
- VFR FastCut source code remains MIT-licensed; redistributed third-party components remain subject to their own licenses.
