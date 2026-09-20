# Minimal FFmpeg runtime for VFR FastCut

This directory contains a reproducible build recipe for the FFmpeg/FFprobe runtime bundled with future VFR FastCut Windows releases.

The goal is not to build a general-purpose FFmpeg distribution. VFR FastCut 0.2.x only needs local-file stream-copy operations, packet/keyframe inspection and concat-based joining. The custom runtime therefore intentionally excludes codecs, network features and external GPL/nonfree libraries that VFR FastCut does not use.

## Target

- FFmpeg: **9.0.2**
- Source: official `ffmpeg.org` release tarball
- Windows toolchain: **MSYS2 UCRT64 / MinGW-w64 GCC**
- Linkage: **shared** FFmpeg libraries (`av*.dll`) rather than static libraries
- FFmpeg license target: **LGPL v2.1 or later**
- `--disable-gpl`
- `--disable-nonfree`
- `--disable-version3`
- no external library autodetection

The source archive is downloaded from:

```text
https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz
```

The build script records the downloaded source SHA-256 and complete configure flags in `runtime/BUILD_INFO.txt`.

## Why shared libraries?

The FastCut application invokes `ffmpeg.exe` and `ffprobe.exe` as independent command-line programs. The custom FFmpeg executables themselves use shared FFmpeg DLLs. This makes the runtime boundary explicit and avoids introducing static-library relinking issues into the FastCut application package.

VFR FastCut's own MIT license is unchanged. The FFmpeg runtime remains governed by FFmpeg's license.

## Supported FastCut operations

The recipe intentionally enables only the container/protocol functionality needed by the 0.2.x branch:

### Input

- MP4 / MOV (`mov` demuxer)
- MKV / WebM (`matroska` demuxer)
- MPEG-TS (`mpegts` demuxer)
- raw M4V (`m4v` demuxer)
- concat lists (`concat` demuxer)

### Output

- MP4 / MOV-family (`mov` muxer)
- MKV / MKA (`matroska` muxer)

### Protocols

- local files (`file`)
- pipes (`pipe`)

Parsers and bitstream filters remain available because some stream-copy container conversions may require them automatically. Encoders, decoders, hardware acceleration, devices and networking are disabled.

## 1. Install MSYS2

Install MSYS2, then open the **MSYS2 UCRT64** shell.

Install the build tools:

```bash
pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain mingw-w64-ucrt-x86_64-nasm mingw-w64-ucrt-x86_64-pkgconf curl tar xz
```

Do not run the script from the plain MSYS, MINGW64 or CLANG shells. It checks for `MSYSTEM=UCRT64`.

## 2. Build

From the repository root in the UCRT64 shell:

```bash
./tools/ffmpeg-minimal/build-msys2-ucrt64.sh
```

The script creates:

```text
tools/ffmpeg-minimal/runtime/
    ffmpeg.exe
    ffprobe.exe
    av*.dll
    COPYING.LGPLv2.1
    BUILD_INFO.txt

tools/ffmpeg-minimal/ffmpeg-9.0.2-source.tar.xz
```

`runtime/` is what will eventually replace the current Gyan.dev `ffmpeg\bin\` payload in the portable FastCut package.

The source tarball is retained so the exact corresponding FFmpeg source can be attached to the GitHub Release or stored in another project-controlled location.

## 3. Verify

From PowerShell, use a real Twitch/VFR H.264+AAC sample when possible:

```powershell
.\tools\ffmpeg-minimal\verify.ps1 -InputFile "D:\video\sample-vod.mp4"
```

Without an input file the script still checks the build configuration and required local protocols:

```powershell
.\tools\ffmpeg-minimal\verify.ps1
```

The full smoke test covers:

- FFprobe packet/keyframe scan;
- video + audio stream copy;
- video-only stream copy;
- audio-only MKA stream copy;
- multi-range concat stream copy.

## 4. Do not switch releases yet

The current v0.2.33 binary release was built with the recorded Gyan.dev full build. Its historical entry in `THIRD_PARTY_VERSIONS.md` must remain unchanged.

Only after this custom build passes the real VOD smoke tests should a later VFR FastCut release be packaged with it. At that point:

1. copy the files from `runtime/` into the portable `ffmpeg\bin\` directory;
2. update `THIRD_PARTY_VERSIONS.md` for the new release;
3. update `THIRD_PARTY_NOTICES.md` from the old Gyan/GPL description to the custom FFmpeg LGPL build for the new release;
4. add the applicable LGPL 2.1 license text to the release package;
5. publish the exact `ffmpeg-9.0.2-source.tar.xz` used by the build as a Release asset or other project-controlled corresponding-source location;
6. retain `BUILD_INFO.txt` in the portable distribution.

## Scope warning

This recipe is intentionally narrow. If VFR FastCut 0.3.x later adds encoding, filters, text overlays or hardware codecs, do not silently reuse this configuration. Re-evaluate the required FFmpeg components and licenses first.
