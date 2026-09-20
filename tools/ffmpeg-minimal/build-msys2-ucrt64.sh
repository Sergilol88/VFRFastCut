#!/usr/bin/env bash
set -euo pipefail

FFMPEG_VERSION="9.0.2"
SOURCE_URL="https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.xz"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="${SCRIPT_DIR}/work"
SRC_ARCHIVE="${WORK_DIR}/ffmpeg-${FFMPEG_VERSION}.tar.xz"
SRC_DIR="${WORK_DIR}/ffmpeg-${FFMPEG_VERSION}"
INSTALL_DIR="${SCRIPT_DIR}/out"
RUNTIME_DIR="${SCRIPT_DIR}/runtime"
MINGW_RUNTIME_BIN="${MINGW_PREFIX:-/ucrt64}/bin"

if [[ "${MSYSTEM:-}" != "UCRT64" ]]; then
  echo "ERROR: run this script from the MSYS2 UCRT64 shell." >&2
  exit 1
fi

for tool in curl tar make gcc pkg-config nasm sha256sum; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "ERROR: missing required tool: $tool" >&2
    exit 1
  fi
done

rm -rf "$WORK_DIR" "$INSTALL_DIR" "$RUNTIME_DIR"
mkdir -p "$WORK_DIR" "$INSTALL_DIR" "$RUNTIME_DIR"

printf 'Downloading FFmpeg %s from official upstream...\n' "$FFMPEG_VERSION"
curl -L --fail --retry 3 -o "$SRC_ARCHIVE" "$SOURCE_URL"
SOURCE_SHA256="$(sha256sum "$SRC_ARCHIVE" | awk '{print $1}')"

tar -xf "$SRC_ARCHIVE" -C "$WORK_DIR"
cd "$SRC_DIR"

CONFIGURE_FLAGS=(
  "--prefix=${INSTALL_DIR}"
  "--disable-static"
  "--enable-shared"
  "--disable-debug"
  "--disable-doc"
  "--disable-network"
  "--disable-autodetect"
  "--disable-gpl"
  "--disable-nonfree"
  "--disable-version3"
  "--disable-ffplay"
  "--disable-encoders"
  "--disable-decoders"
  "--disable-hwaccels"
  "--disable-devices"
  "--disable-avdevice"
  "--disable-demuxers"
  "--enable-demuxer=mov"
  "--enable-demuxer=avi"
  "--enable-demuxer=flv"
  "--enable-demuxer=mpeg"
  "--enable-demuxer=asf"
  "--enable-demuxer=matroska"
  "--enable-demuxer=mpegts"
  "--enable-demuxer=m4v"
  "--enable-demuxer=concat"
  "--disable-muxers"
  "--enable-muxer=mov"
  "--enable-muxer=mp4"
  "--enable-muxer=matroska"
  "--disable-protocols"
  "--enable-protocol=file"
  "--enable-protocol=pipe"
)

./configure "${CONFIGURE_FLAGS[@]}"
make -j"$(nproc)"
make install

cp "$INSTALL_DIR/bin/ffmpeg.exe" "$RUNTIME_DIR/"
cp "$INSTALL_DIR/bin/ffprobe.exe" "$RUNTIME_DIR/"
find "$INSTALL_DIR/bin" -maxdepth 1 -type f -name '*.dll' -exec cp '{}' "$RUNTIME_DIR/" ';'

# FFmpeg built with the MSYS2 UCRT64 GCC runtime depends on these two
# MinGW runtime DLLs when launched outside the MSYS2 shell. Bundle them
# explicitly so the resulting FFmpeg runtime is portable on Windows.
RUNTIME_DLLS=(
  "libwinpthread-1.dll"
  "libgcc_s_seh-1.dll"
)

for dll in "${RUNTIME_DLLS[@]}"; do
  source_dll="${MINGW_RUNTIME_BIN}/${dll}"
  if [[ ! -f "$source_dll" ]]; then
    echo "ERROR: required MinGW runtime DLL not found: $source_dll" >&2
    exit 1
  fi
  cp "$source_dll" "$RUNTIME_DIR/"
done

cp COPYING.LGPLv2.1 "$RUNTIME_DIR/"

{
  echo "VFR FastCut minimal FFmpeg runtime"
  echo
  echo "FFmpeg version: ${FFMPEG_VERSION}"
  echo "Source URL: ${SOURCE_URL}"
  echo "Source SHA256: ${SOURCE_SHA256}"
  echo "Build environment: MSYS2 UCRT64"
  echo "License target: LGPL v2.1 or later"
  echo
  echo "Bundled MinGW runtime DLLs:"
  printf '  %s\n' "${RUNTIME_DLLS[@]}"
  echo
  echo "Configure flags:"
  printf '  %s\n' "${CONFIGURE_FLAGS[@]}"
  echo
  echo "Compiler:"
  gcc --version | head -n 1
} > "$RUNTIME_DIR/BUILD_INFO.txt"

cp "$SRC_ARCHIVE" "$SCRIPT_DIR/ffmpeg-${FFMPEG_VERSION}-source.tar.xz"

printf '\nBuild complete.\nRuntime: %s\nSource archive for redistribution: %s\n' \
  "$RUNTIME_DIR" \
  "$SCRIPT_DIR/ffmpeg-${FFMPEG_VERSION}-source.tar.xz"

"$RUNTIME_DIR/ffmpeg.exe" -version
"$RUNTIME_DIR/ffprobe.exe" -version
