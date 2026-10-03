param(
    [Parameter(Mandatory=$false)]
    [string]$DistDir = ".\dist\VFRFastCut"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $DistDir)) {
    throw "Portable directory not found: $DistDir"
}

$DistDir = (Resolve-Path $DistDir).Path
Write-Host "Auditing portable directory:"
Write-Host "  $DistDir"
Write-Host

$required = @(
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "THIRD_PARTY_VERSIONS.md",
    "LICENSES\LGPL-2.1.txt",
    "LICENSES\LGPL-3.0.txt",
    "ffmpeg\bin\ffmpeg.exe",
    "ffmpeg\bin\ffprobe.exe",
    "ffmpeg\bin\BUILD_INFO.txt",
    "ffmpeg\bin\COPYING.LGPLv2.1"
)

$missing = @()
foreach ($rel in $required) {
    $path = Join-Path $DistDir $rel
    if (-not (Test-Path $path)) {
        $missing += $rel
    }
}

$licenseDir = Join-Path $DistDir "LICENSES"
$pythonLicenses = @()
if (Test-Path $licenseDir -PathType Container) {
    $pythonLicenses = @(
        Get-ChildItem $licenseDir -File -Filter "Python-*-LICENSE.txt"
    )
}
if ($pythonLicenses.Count -eq 0) {
    $missing += "LICENSES\Python-<build-version>-LICENSE.txt"
}

if ($missing.Count -gt 0) {
    Write-Host "Missing expected release files:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host
    throw "Portable audit failed because required release files are missing."
} else {
    Write-Host "Expected license/runtime files: OK" -ForegroundColor Green
    $pythonLicenses | ForEach-Object {
        Write-Host "  Python license: $($_.Name)"
    }
    if ($pythonLicenses.Count -gt 1) {
        Write-Host "  WARNING: more than one Python build license is present; verify the package contains the license matching the bundled interpreter." -ForegroundColor Yellow
    }
    Write-Host
}

Write-Host "Python runtime candidates:"
Get-ChildItem $DistDir -Recurse -File -Include "python*.dll" |
    ForEach-Object { Write-Host "  $($_.FullName.Substring($DistDir.Length + 1))" }
Write-Host

Write-Host "Qt DLLs:"
$qtDlls = Get-ChildItem $DistDir -Recurse -File -Filter "Qt6*.dll" |
    Sort-Object FullName
$qtDlls | ForEach-Object {
    Write-Host "  $($_.FullName.Substring($DistDir.Length + 1))"
}
Write-Host

Write-Host "Qt plugin DLLs:"
Get-ChildItem $DistDir -Recurse -File -Filter "*.dll" |
    Where-Object { $_.FullName -match "\\plugins\\" } |
    Sort-Object FullName |
    ForEach-Object {
        Write-Host "  $($_.FullName.Substring($DistDir.Length + 1))"
    }
Write-Host

Write-Host "FFmpeg-family DLLs outside project ffmpeg\bin:"
$ffmpegBin = (Join-Path $DistDir "ffmpeg\bin").TrimEnd("\")
$extraFfmpeg = Get-ChildItem $DistDir -Recurse -File |
    Where-Object {
        $_.Name -match "^(avcodec|avformat|avutil|avfilter|swresample|swscale|postproc).+\.dll$" -and
        -not $_.DirectoryName.StartsWith($ffmpegBin, [System.StringComparison]::OrdinalIgnoreCase)
    } |
    Sort-Object FullName

if ($extraFfmpeg) {
    $extraFfmpeg | ForEach-Object {
        Write-Host "  $($_.FullName.Substring($DistDir.Length + 1))" -ForegroundColor Yellow
    }
    Write-Host
    Write-Host "WARNING: FFmpeg-family libraries were found outside the project runtime." -ForegroundColor Yellow
    Write-Host "Treat them as a separate redistributed dependency and record license/source information."
} else {
    Write-Host "  none detected" -ForegroundColor Green
}
Write-Host

$buildInfo = Join-Path $DistDir "ffmpeg\bin\BUILD_INFO.txt"
if (Test-Path $buildInfo) {
    Write-Host "Project FFmpeg BUILD_INFO.txt:"
    Get-Content $buildInfo | ForEach-Object { Write-Host "  $_" }
    Write-Host
}

Write-Host "Third-party binary candidates requiring review:"
$thirdPartyPattern = "^(avcodec|avformat|avutil|avfilter|swresample|swscale|postproc|libcrypto|libssl|libgcc|libstdc\+\+|libwinpthread|openh264|zlib|libpng|jpeg|tiff|webp).+\.(dll|pyd)$"
$candidates = Get-ChildItem $DistDir -Recurse -File |
    Where-Object { $_.Name -match $thirdPartyPattern } |
    Sort-Object FullName
if ($candidates) {
    $candidates | ForEach-Object {
        Write-Host "  $($_.FullName.Substring($DistDir.Length + 1))" -ForegroundColor Yellow
    }
} else {
    Write-Host "  none detected by filename heuristic" -ForegroundColor Green
}
Write-Host
Write-Host "All DLL names (manual dependency inventory):"
Get-ChildItem $DistDir -Recurse -File -Filter "*.dll" |
    Sort-Object Name, FullName |
    ForEach-Object {
        Write-Host "  $($_.FullName.Substring($DistDir.Length + 1))"
    }

Write-Host
Write-Host "Audit complete."
Write-Host "Review unexpected DLLs/plugins before publishing the release."
