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
if ($versionText -match '--enable-gpl') { throw "GPL was enabled unexpectedly." }
if ($versionText -match '--enable-nonfree') { throw "Nonfree was enabled unexpectedly." }
if ($versionText -notmatch '--disable-gpl') { throw "Expected --disable-gpl in build configuration." }
if ($versionText -notmatch '--disable-nonfree') { throw "Expected --disable-nonfree in build configuration." }

$formats = & $Ffmpeg -hide_banner -formats 2>&1 | Out-String
foreach ($required in @('mov,mp4,m4a,3gp,3g2,mj2', 'matroska,webm', 'mpegts', 'm4v', 'concat')) {
    if ($formats -notmatch [regex]::Escape($required)) {
        Write-Warning "Could not confirm format token: $required"
    }
}

$protocols = & $Ffmpeg -hide_banner -protocols 2>&1 | Out-String
foreach ($required in @('file', 'pipe')) {
    if ($protocols -notmatch "(?m)^\s*$([regex]::Escape($required))\s*$") {
        throw "Required protocol missing: $required"
    }
}

Write-Host "License/configuration checks: OK"
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

    $av = Join-Path $TempRoot "av.mkv"
    & $Ffmpeg -hide_banner -loglevel error -y -ss 1 -i $InputFile -t 3 -map 0:v:0 -map '0:a?' -map_metadata 0 -c copy $av
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
