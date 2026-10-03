# Release helpers

## Safe portable packaging

Use `package-portable.ps1` for release and RC archives instead of calling `tar.exe` manually.

The script:

- reads `APP_VERSION` from `vfr_fastcut.py` unless `-Version` is supplied;
- requires the verified runtime in `tools\ffmpeg-minimal\runtime`;
- copies the complete FFmpeg runtime into `dist\VFRFastCut\ffmpeg\bin`;
- checks required application, license, `ffmpeg.exe` and `ffprobe.exe` files;
- starts the bundled `ffmpeg.exe` and `ffprobe.exe` to verify their DLL dependencies;
- runs `audit-portable.ps1`;
- creates the release ZIP and SHA-256 file;
- re-opens the ZIP and refuses the package if `ffmpeg.exe` or `ffprobe.exe` is missing.

From the repository root after building `dist\VFRFastCut`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File ".\tools\release\package-portable.ps1"
```

Default output:

```text
VFRFastCut-v<APP_VERSION>-Windows-x64.zip
VFRFastCut-v<APP_VERSION>-Windows-x64.zip.sha256
```

For an RC you may leave `APP_VERSION` as `0.5.0-dev` and use `-Version` to give the test archive an explicit RC label if desired. For the final release, set `APP_VERSION = "0.5.0"`, commit that exact source state, rebuild the application, and package from that exact commit.

Do not publish an archive produced by a manual ZIP step that bypasses these checks.
