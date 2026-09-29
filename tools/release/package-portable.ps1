param(
    [Parameter(Mandatory=$false)]
    [string]$Version = "",

    [Parameter(Mandatory=$false)]
    [string]$DistDir = ".\dist\VFRFastCut",

    [Parameter(Mandatory=$false)]
    [string]$RuntimeDir = ".\tools\ffmpeg-minimal\runtime",

    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "."
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location $RepoRoot

try {
    if ([string]::IsNullOrWhiteSpace($Version)) {
        $SourceFile = Join-Path $RepoRoot "vfr_fastcut.py"
        if (-not (Test-Path $SourceFile -PathType Leaf)) {
            throw "Could not determine application version: $SourceFile was not found."
        }

        $SourceText = Get-Content $SourceFile -Raw
        $VersionMatch = [regex]::Match($SourceText, 'APP_VERSION\s*=\s*"([^"]+)"')
        if (-not $VersionMatch.Success) {
            throw "Could not determine application version from APP_VERSION in vfr_fastcut.py."
        }
        $Version = $VersionMatch.Groups[1].Value
    }

    if (-not (Test-Path $DistDir -PathType Container)) {
        throw "Portable directory not found: $DistDir"
    }
    if (-not (Test-Path $RuntimeDir -PathType Container)) {
        throw "FFmpeg runtime directory not found: $RuntimeDir`nBuild it first with tools\ffmpeg-minimal\build-msys2-ucrt64.sh."
    }

    $DistDir = (Resolve-Path $DistDir).Path
    $RuntimeDir = (Resolve-Path $RuntimeDir).Path

    New-Item -ItemType Directory -Force $OutputDir | Out-Null
    $OutputDir = (Resolve-Path $OutputDir).Path

    Write-Host "Preparing VFR FastCut portable package v$Version" -ForegroundColor Cyan
    Write-Host "Portable directory: $DistDir"
    Write-Host "FFmpeg runtime:    $RuntimeDir"
    Write-Host

    $requiredRuntimeFiles = @(
        "ffmpeg.exe",
        "ffprobe.exe",
        "BUILD_INFO.txt",
        "COPYING.LGPLv2.1"
    )

    $missingRuntimeFiles = @()
    foreach ($name in $requiredRuntimeFiles) {
        if (-not (Test-Path (Join-Path $RuntimeDir $name) -PathType Leaf)) {
            $missingRuntimeFiles += $name
        }
    }

    if ($missingRuntimeFiles.Count -gt 0) {
        throw "FFmpeg runtime is incomplete. Missing: $($missingRuntimeFiles -join ', ')"
    }

    $TargetFfmpegBin = Join-Path $DistDir "ffmpeg\bin"
    if (Test-Path $TargetFfmpegBin) {
        Remove-Item $TargetFfmpegBin -Recurse -Force
    }
    New-Item -ItemType Directory -Force $TargetFfmpegBin | Out-Null

    Copy-Item (Join-Path $RuntimeDir "*") $TargetFfmpegBin -Recurse -Force

    $requiredPortableFiles = @(
        "VFRFastCut.exe",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "THIRD_PARTY_VERSIONS.md",
        "LICENSES\LGPL-2.1.txt",
        "LICENSES\LGPL-3.0.txt",
        "LICENSES\Python-3.14.5-LICENSE.txt",
        "ffmpeg\bin\ffmpeg.exe",
        "ffmpeg\bin\ffprobe.exe",
        "ffmpeg\bin\BUILD_INFO.txt",
        "ffmpeg\bin\COPYING.LGPLv2.1"
    )

    $missingPortableFiles = @()
    foreach ($rel in $requiredPortableFiles) {
        if (-not (Test-Path (Join-Path $DistDir $rel) -PathType Leaf)) {
            $missingPortableFiles += $rel
        }
    }

    if ($missingPortableFiles.Count -gt 0) {
        throw "Portable package staging failed. Missing: $($missingPortableFiles -join ', ')"
    }

    Write-Host "Testing bundled FFmpeg executables..." -ForegroundColor Cyan
    & (Join-Path $TargetFfmpegBin "ffmpeg.exe") -hide_banner -version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Bundled ffmpeg.exe failed to start (exit code $LASTEXITCODE)."
    }

    & (Join-Path $TargetFfmpegBin "ffprobe.exe") -hide_banner -version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Bundled ffprobe.exe failed to start (exit code $LASTEXITCODE)."
    }

    $AuditScript = Join-Path $RepoRoot "tools\release\audit-portable.ps1"
    if (Test-Path $AuditScript -PathType Leaf) {
        Write-Host "Running portable audit..." -ForegroundColor Cyan
        & $AuditScript -DistDir $DistDir
    }

    $ArchiveName = "VFRFastCut-v$Version-Windows-x64.zip"
    $ArchivePath = Join-Path $OutputDir $ArchiveName
    $ChecksumPath = "$ArchivePath.sha256"

    Remove-Item $ArchivePath -Force -ErrorAction SilentlyContinue
    Remove-Item $ChecksumPath -Force -ErrorAction SilentlyContinue

    $DistParent = Split-Path $DistDir -Parent
    $DistLeaf = Split-Path $DistDir -Leaf

    Write-Host "Creating archive: $ArchiveName" -ForegroundColor Cyan
    & tar.exe -a -c -f $ArchivePath -C $DistParent $DistLeaf
    if ($LASTEXITCODE -ne 0) {
        throw "tar.exe failed to create the release archive (exit code $LASTEXITCODE)."
    }

    Write-Host "Verifying archive contents..." -ForegroundColor Cyan
    $archiveEntries = @(& tar.exe -tf $ArchivePath)
    if ($LASTEXITCODE -ne 0) {
        throw "tar.exe failed to read the release archive (exit code $LASTEXITCODE)."
    }

    $requiredArchiveEntries = @(
        "$DistLeaf/VFRFastCut.exe",
        "$DistLeaf/ffmpeg/bin/ffmpeg.exe",
        "$DistLeaf/ffmpeg/bin/ffprobe.exe"
    )

    $trimChars = [char[]]"./"
    $normalizedEntries = $archiveEntries | ForEach-Object {
        ($_ -replace '\\', '/').TrimStart($trimChars)
    }

    $missingArchiveEntries = @()
    foreach ($entry in $requiredArchiveEntries) {
        $normalizedRequired = ($entry -replace '\\', '/').TrimStart($trimChars)
        if ($normalizedEntries -notcontains $normalizedRequired) {
            $missingArchiveEntries += $entry
        }
    }

    if ($missingArchiveEntries.Count -gt 0) {
        Remove-Item $ArchivePath -Force -ErrorAction SilentlyContinue
        throw "Release archive verification failed. Missing from ZIP: $($missingArchiveEntries -join ', ')"
    }

    $Hash = (Get-FileHash $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    "$Hash  $ArchiveName" | Set-Content $ChecksumPath -Encoding ascii

    Write-Host
    Write-Host "Release package is ready." -ForegroundColor Green
    Write-Host "  ZIP:    $ArchivePath"
    Write-Host "  SHA256: $ChecksumPath"
    Write-Host "  Hash:   $Hash"
    Write-Host
    Write-Host "The archive was verified to contain ffmpeg.exe and ffprobe.exe." -ForegroundColor Green
}
finally {
    Pop-Location
}
