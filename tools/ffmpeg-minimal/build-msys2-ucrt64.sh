#!/usr/bin/env bash
set -euo pipefail

FFMPEG_VERSION="9.0.2"
SOURCE_URL="https://ffmpeg.org/releases/ffmpeg-${FFMPEG_VERSION}.tar.xz"
EXPECTED_SOURCE_SHA256="8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e"

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

for tool in curl tar make gcc pkg-config nasm sha256sum pacman; do
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
if [[ "$SOURCE_SHA256" != "$EXPECTED_SOURCE_SHA256" ]]; then
  echo "ERROR: FFmpeg source SHA256 mismatch." >&2
  echo "Expected: $EXPECTED_SOURCE_SHA256" >&2
  echo "Actual:   $SOURCE_SHA256" >&2
  exit 1
fi

# MSYS2 occasionally splits or renames GCC runtime packages. Record the package
# that actually owns each runtime DLL instead of assuming historical package
# names such as mingw-w64-ucrt-x86_64-gcc-libs.
runtime_package_info() {
  local runtime_file="$1"
  local owner=""

  owner="$(pacman -Qqo "$runtime_file" 2>/dev/null || true)"
  if [[ -z "$owner" ]]; then
    printf 'unowned (%s)\n' "$runtime_file"
    return 0
  fi

  pacman -Q "$owner" | head -n 1
}

LIBWINPTHREAD_PACKAGE_INFO="$(runtime_package_info "${MINGW_RUNTIME_BIN}/libwinpthread-1.dll")"
LIBGCC_PACKAGE_INFO="$(runtime_package_info "${MINGW_RUNTIME_BIN}/libgcc_s_seh-1.dll")"

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
  "--enable-encoder=aac"
  "--enable-decoder=aac"
  "--enable-decoder=mp3"
  "--enable-decoder=flac"
  "--enable-decoder=vorbis"
  "--enable-decoder=opus"
  "--enable-decoder=alac"
  "--enable-decoder=ac3"
  "--enable-decoder=eac3"
  "--enable-decoder=wmav1"
  "--enable-decoder=wmav2"
  "--enable-decoder=pcm_u8"
  "--enable-decoder=pcm_s16le"
  "--enable-decoder=pcm_s24le"
  "--enable-decoder=pcm_s32le"
  "--enable-decoder=pcm_f32le"
  "--enable-filter=volume"
  "--enable-filter=afade"
  "--enable-filter=aformat"
  "--enable-filter=amix"
  "--enable-filter=alimiter"
  "--enable-filter=adelay"
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
  "--enable-demuxer=mp3"
  "--enable-demuxer=wav"
  "--enable-demuxer=aac"
  "--enable-demuxer=flac"
  "--enable-demuxer=ogg"
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
  echo "MSYS2 runtime packages owning bundled DLLs:"
  echo "  ${LIBWINPTHREAD_PACKAGE_INFO}"
  echo "  ${LIBGCC_PACKAGE_INFO}"
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
