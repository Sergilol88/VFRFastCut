# Building VFR FastCut on Windows

## 1. Install Python dependencies

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

## 2. Prepare FFmpeg

The portable build can bundle `ffmpeg.exe` and `ffprobe.exe` from:

```text
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

Before redistributing third-party binaries, read `THIRD_PARTY_NOTICES.md` and include the license/source information required by the exact FFmpeg build you ship.

## 3. Build the portable onedir package

Run from the repository root:

```powershell
python -m PyInstaller --noconfirm --clean --onedir --windowed --contents-directory "." --name "VFRFastCut" --icon "VFRFastCut.ico" --add-data "VFRFastCut.ico;." --add-data "LICENSE;." --add-data "THIRD_PARTY_NOTICES.md;." --add-data "README.md;." --add-data "README_RU.md;." --add-data "LICENSES;LICENSES" --add-binary "C:\ffmpeg\bin\ffmpeg.exe;ffmpeg\bin" --add-binary "C:\ffmpeg\bin\ffprobe.exe;ffmpeg\bin" vfr_fastcut.py
```

Result:

```text
dist\VFRFastCut\
```

Distribute the **whole folder**, normally as a ZIP archive.

## 4. Portable smoke test

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
