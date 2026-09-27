param(
    [Parameter(Mandatory=$false)]
    [string]$InputFile
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeDir = Join-Path $ScriptDir "runtime"
$Ffmpeg = Join-Path $RuntimeDir "ffmpeg.exe"
$Ffprobe = Join-Path $RuntimeDir "ffprobe.exe"

if (-not (Test-Path $Ffmpeg)) { throw "Missing $Ffmpeg" }
if (-not (Test-Path $Ffprobe)) { throw "Missing $Ffprobe" }

$versionText = & $Ffmpeg -version 2>&1 | Out-String
if ($versionText -notmatch '(?m)^ffmpeg version 9\.0\.2(?:\s|$)') { throw "Expected FFmpeg 9.0.2 runtime." }
$licenseText = & $Ffmpeg -hide_banner -L 2>&1 | Out-String
if ($licenseText -notmatch 'GNU\s+Lesser\s+General\s+Public\s+License') {
    throw "Expected LGPL FFmpeg license output."
}
if ($licenseText -notmatch 'version\s+2\.1\b') {
    throw "Expected FFmpeg LGPL version 2.1-or-later license output."
}
if ($versionText -match '--enable-gpl') { throw "GPL was enabled unexpectedly." }
if ($versionText -match '--enable-nonfree') { throw "Nonfree was enabled unexpectedly." }
if ($versionText -notmatch '--disable-gpl') { throw "Expected --disable-gpl in build configuration." }
if ($versionText -notmatch '--disable-nonfree') { throw "Expected --disable-nonfree in build configuration." }
if ($versionText -match '--enable-version3') { throw "Version-3 licensing was enabled unexpectedly." }
if ($versionText -notmatch '--disable-version3') { throw "Expected --disable-version3 in build configuration." }
if ($versionText -notmatch '--disable-autodetect') { throw "Expected --disable-autodetect in build configuration." }

$demuxers = & $Ffmpeg -hide_banner -demuxers 2>&1 | Out-String
foreach ($required in @('mov', 'matroska', 'mpegts', 'm4v', 'avi', 'flv', 'mpeg', 'asf', 'concat', 'mp3', 'wav', 'aac', 'flac', 'ogg')) {
    if ($demuxers -notmatch "(?m)^\s*D\s+[^\r\n]*\b$([regex]::Escape($required))\b") {
        throw "Required demuxer missing: $required"
    }
}

$decoders = & $Ffmpeg -hide_banner -decoders 2>&1 | Out-String
foreach ($required in @('aac', 'mp3', 'flac', 'vorbis', 'opus', 'alac', 'ac3', 'eac3', 'wmav1', 'wmav2', 'pcm_u8', 'pcm_s16le', 'pcm_s24le', 'pcm_s32le', 'pcm_f32le')) {
    if ($decoders -notmatch "(?m)^\s*A[^\r\n]*\b$([regex]::Escape($required))\b") {
        throw "Required audio decoder missing: $required"
    }
}

$encoders = & $Ffmpeg -hide_banner -encoders 2>&1 | Out-String
if ($encoders -notmatch "(?m)^\s*A[^\r\n]*\baac\b") {
    throw "Required audio encoder missing: aac"
}

$filters = & $Ffmpeg -hide_banner -filters 2>&1 | Out-String
foreach ($required in @('volume', 'afade', 'aformat', 'amix', 'alimiter', 'adelay')) {
    if ($filters -notmatch "(?m)^\s*\S+\s+$([regex]::Escape($required))\s+") {
        throw "Required audio filter missing: $required"
    }
}

$muxers = & $Ffmpeg -hide_banner -muxers 2>&1 | Out-String
foreach ($required in @('mp4', 'mov', 'matroska')) {
    if ($muxers -notmatch "(?m)^\s*E\s+[^\r\n]*\b$([regex]::Escape($required))\b") {
        throw "Required muxer missing: $required"
    }
}

$protocols = & $Ffmpeg -hide_banner -protocols 2>&1 | Out-String
foreach ($required in @('file', 'pipe')) {
    if ($protocols -notmatch "(?m)^\s*$([regex]::Escape($required))\s*$") {
        throw "Required protocol missing: $required"
    }
}

Write-Host "License/configuration checks: OK"
Write-Host "Required demuxers/audio processing/muxers: OK"
Write-Host "Required local protocols: OK"

if (-not $InputFile) {
    Write-Host "No input file supplied; runtime capability checks complete."
    exit 0
}

if (-not (Test-Path $InputFile)) { throw "Input file not found: $InputFile" }

$InputFile = (Resolve-Path $InputFile).Path
$TempRoot = Join-Path ([IO.Path]::GetTempPath()) ("VFRFastCutFFmpegTest_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $TempRoot | Out-Null

try {
    $probePackets = & $Ffprobe -v error -select_streams v:0 -show_entries packet=pts_time,flags -of csv=p=0 -read_intervals "0%+5" $InputFile 2>&1 | Out-String
    if (-not $probePackets.Trim()) { throw "FFprobe packet/keyframe scan produced no output." }
    Write-Host "FFprobe packet scan: OK"

    $av = Join-Path $TempRoot "av.mp4"
    & $Ffmpeg -hide_banner -loglevel error -y -ss 1 -i $InputFile -t 3 -map 0:v:0 -map '0:a?' -map_metadata 0 -c copy -f mp4 $av
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $av)) { throw "Video+audio stream copy failed." }
    Write-Host "Video + audio stream copy: OK"

    $video = Join-Path $TempRoot "video.mkv"
    & $Ffmpeg -hide_banner -loglevel error -y -ss 1 -i $InputFile -t 3 -map 0:v:0 -map_metadata 0 -c copy $video
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $video)) { throw "Video-only stream copy failed." }
    Write-Host "Video-only stream copy: OK"

    $audio = Join-Path $TempRoot "audio.mka"
    & $Ffmpeg -hide_banner -loglevel error -y -ss 1 -i $InputFile -t 3 -map '0:a?' -map_metadata 0 -c copy -f matroska $audio
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $audio)) { throw "Audio-only stream copy failed." }
    Write-Host "Audio-only stream copy: OK"

    $audioCodec = & $Ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nw=1:nk=1 $InputFile 2>&1 | Out-String
    if ($audioCodec.Trim()) {
        $processedAudio = Join-Path $TempRoot "volume-test.mka"
        & $Ffmpeg -hide_banner -loglevel error -y -ss 1 -i $InputFile -t 1 -map 0:a:0 -af 'volume=0.5,afade=t=in:st=0:d=0.1,afade=t=out:st=0.9:d=0.1' -c:a aac -b:a 192k -f matroska $processedAudio
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $processedAudio)) { throw "Audio volume/fade filter AAC encode test failed." }
        Write-Host "Audio volume/fade processing: OK ($($audioCodec.Trim()) -> AAC)"

        $mainMix = Join-Path $TempRoot "main-mix-test.mka"
        & $Ffmpeg -hide_banner -loglevel error -y -ss 1 -i $InputFile -ss 1 -i $InputFile -t 1 -filter_complex '[0:a:0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[m0];[1:a:0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,adelay=250|250[m1];[m0][m1]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,alimiter=limit=0.95:attack=5:release=50:level=false:latency=true[main]' -map '[main]' -c:a aac -b:a 256k -f matroska $mainMix
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $mainMix)) { throw "Main Mix filter/AAC encode test failed." }

        $mainMixInfo = & $Ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of csv=p=0 $mainMix 2>&1 | Out-String
        $mainMixParts = $mainMixInfo.Trim().Split(',')
        if ($mainMixParts.Count -lt 3 -or $mainMixParts[0] -ne 'aac' -or $mainMixParts[1] -ne '48000' -or $mainMixParts[2] -ne '2') {
            throw "Main Mix output format mismatch: expected AAC stereo/48 kHz, got '$($mainMixInfo.Trim())'."
        }
        Write-Host "Main Mix processing: OK (amix + alimiter -> AAC stereo/48 kHz)"
    }
    else {
        Write-Host "Audio volume/fade processing: SKIPPED (input has no audio stream)"
    }

    $part1 = Join-Path $TempRoot "part1.mkv"
    $part2 = Join-Path $TempRoot "part2.mkv"
    & $Ffmpeg -hide_banner -loglevel error -y -ss 1 -i $InputFile -t 2 -map 0:v:0 -map '0:a?' -c copy -avoid_negative_ts make_zero $part1
    if ($LASTEXITCODE -ne 0) { throw "Concat part 1 creation failed." }
    & $Ffmpeg -hide_banner -loglevel error -y -ss 5 -i $InputFile -t 2 -map 0:v:0 -map '0:a?' -c copy -avoid_negative_ts make_zero $part2
    if ($LASTEXITCODE -ne 0) { throw "Concat part 2 creation failed." }

    $concatFile = Join-Path $TempRoot "concat.txt"
    $concatLines = @(
        "file '$($part1.Replace("'", "'\''"))'",
        "file '$($part2.Replace("'", "'\''"))'"
    )
    # Windows PowerShell 5.1 writes a BOM for -Encoding UTF8. FFmpeg's concat
    # demuxer treats that BOM as part of the first keyword ("file") and fails.
    # Write explicit UTF-8 without BOM so the test behaves like the Python app.
    [IO.File]::WriteAllText(
        $concatFile,
        ($concatLines -join [Environment]::NewLine),
        (New-Object Text.UTF8Encoding($false))
    )

    $joined = Join-Path $TempRoot "joined.mkv"
    & $Ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $concatFile -map 0:v:0 -map '0:a?' -c copy $joined
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $joined)) { throw "Concat demuxer stream-copy test failed." }
    Write-Host "Multi-range concat stream copy: OK"

    Write-Host "All VFR FastCut FFmpeg smoke tests passed."
}
finally {
    Remove-Item -Recurse -Force $TempRoot -ErrorAction SilentlyContinue
}
