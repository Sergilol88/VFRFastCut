# Minimal FFmpeg runtime for VFR FastCut

This directory contains the reproducible FFmpeg/FFprobe build recipe used by the VFR FastCut Windows portable package starting with v0.2.34.

The goal is not to build a general-purpose FFmpeg distribution. VFR FastCut 0.2.x needs local-file stream-copy operations, packet/keyframe inspection and concat-based joining.

## Target

- FFmpeg: **9.0.2**
- Source: official `ffmpeg.org` release tarball
- Source SHA-256 for the v0.2.34 build: `8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e`
- Windows toolchain: **MSYS2 UCRT64 / MinGW-w64 GCC**
- Linkage: **shared** FFmpeg libraries (`av*.dll`)
- Recorded FFmpeg build license target: **LGPL v2.1 or later**
- `--disable-gpl`
- `--disable-nonfree`
- `--disable-version3`
- no external library autodetection

The build script records the downloaded source SHA-256 and complete configure flags in `runtime/BUILD_INFO.txt`.

## Supported FastCut operations

### Input containers

- MP4 / MOV (`mov` demuxer)
- raw M4V (`m4v` demuxer)
- MKV / WebM (`matroska` demuxer)
- TS / MTS / M2TS (`mpegts` demuxer)
- AVI (`avi` demuxer)
- FLV (`flv` demuxer)
- MPG / MPEG program streams (`mpeg` demuxer)
- WMV / ASF (`asf` demuxer)
- concat lists (`concat` demuxer)

### Output containers

- MP4 (`mp4` muxer)
- MOV (`mov` muxer)
- MKV / MKA (`matroska` muxer)

FastCut preserves MP4, MOV and MKV as the suggested video output container. Other supported input containers default to MKV.

Container support does not guarantee that every possible encoded stream can be copied into every output container. MKV is the general fallback when a source stream is not compatible with MP4/MOV stream-copy remuxing.

### Protocols

- local files (`file`)
- pipes (`pipe`)

Parsers and bitstream filters remain available because some stream-copy operations may require them automatically. Encoders, decoders, hardware acceleration, devices and networking are disabled.

## Build

Install MSYS2, open the **MSYS2 UCRT64** shell, and install the required build tools:

```bash
pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain mingw-w64-ucrt-x86_64-nasm mingw-w64-ucrt-x86_64-pkgconf curl tar xz
```

From the repository root:

```bash
./tools/ffmpeg-minimal/build-msys2-ucrt64.sh
```

The script creates:

```text
tools/ffmpeg-minimal/runtime/
    ffmpeg.exe
    ffprobe.exe
    av*.dll
    libwinpthread-1.dll
    libgcc_s_seh-1.dll
    COPYING.LGPLv2.1
    BUILD_INFO.txt

tools/ffmpeg-minimal/ffmpeg-9.0.2-source.tar.xz
```

The two MinGW runtime DLLs are copied from the installed MSYS2 UCRT64 packages so the FFmpeg runtime can launch outside the MSYS2 shell.

## Verify

From PowerShell:

```powershell
.\tools\ffmpeg-minimal\verify.ps1 -InputFile "D:\video\sample-vod.mp4"
```

The smoke test checks:

- build configuration;
- required demuxers and muxers;
- local protocols;
- FFprobe packet/keyframe scanning;
- video + audio MP4 stream copy;
- video-only stream copy;
- audio-only MKA stream copy;
- multi-range concat stream copy.

## Release use

For v0.2.34 and later compatible 0.2.x releases:

1. build this runtime from the documented source;
2. run the smoke tests;
3. copy the complete `runtime/` contents into `dist\VFRFastCut\ffmpeg\bin\`;
4. retain `BUILD_INFO.txt`;
5. include the applicable third-party license files;
6. publish the exact generated `ffmpeg-9.0.2-source.tar.xz` with the corresponding Release or otherwise keep it available from a project-controlled location.

If future VFR FastCut versions add encoding, filters, text overlays or hardware codecs, re-evaluate the required FFmpeg components and third-party licenses before changing this configuration.
