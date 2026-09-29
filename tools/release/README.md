# Release helpers

## Safe portable packaging

Use `package-portable.ps1` to create the Windows release ZIP instead of calling `tar.exe` manually.

The script:

- reads `APP_VERSION` from `vfr_fastcut.py` unless `-Version` is supplied;
- requires the verified runtime in `tools\ffmpeg-minimal\runtime`;
- copies the complete FFmpeg runtime into `dist\VFRFastCut\ffmpeg\bin`;
- checks the required application, license, `ffmpeg.exe` and `ffprobe.exe` files;
- starts the bundled `ffmpeg.exe` and `ffprobe.exe` to verify their DLL dependencies;
- runs `audit-portable.ps1`;
- creates the release ZIP and SHA-256 file;
- re-opens the ZIP and refuses the release if `ffmpeg.exe` or `ffprobe.exe` is missing from the archive.

From the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".\tools\release\package-portable.ps1"
```

The default output is:

```text
VFRFastCut-v<APP_VERSION>-Windows-x64.zip
VFRFastCut-v<APP_VERSION>-Windows-x64.zip.sha256
```

## Repairing the v0.4.15 release package

If the existing `dist\VFRFastCut` directory is still available, rebuild only the release package; the application executable does not need to be rebuilt for this packaging-only repair.

First confirm that the minimal FFmpeg runtime exists in:

```text
tools\ffmpeg-minimal\runtime\
```

Then run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".\tools\release\package-portable.ps1" `
  -Version "0.4.15"
```

Replace the broken GitHub Release ZIP and its `.sha256` file only after this script completes successfully.

Do not publish an archive produced by a manual `tar.exe`/ZIP step that bypasses these checks.
