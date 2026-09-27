param(
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = ".\release-sources"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $OutputDir | Out-Null
$OutputDir = (Resolve-Path $OutputDir).Path

$files = @(
    @{
        Name = "qtbase-everywhere-src-6.11.2.tar.xz"
        Url = "https://mirror.accum.se/mirror/qt.io/qtproject/archive/qt/6.11/6.11.2/submodules/qtbase-everywhere-src-6.11.2.tar.xz"
        ExpectedSha256 = "5b2e00eccaf5a4d8c14134ffa0ea8dfd0a35ae1ffc7f8d87fa4305a1ed23cf22"
    },
    @{
        Name = "qtmultimedia-everywhere-src-6.11.2.tar.xz"
        Url = "https://mirror.accum.se/mirror/qt.io/qtproject/archive/qt/6.11/6.11.2/submodules/qtmultimedia-everywhere-src-6.11.2.tar.xz"
        ExpectedSha256 = $null
    },
    @{
        Name = "pyside-setup-everywhere-src-6.11.2.tar.xz"
        Url = "https://mirror.accum.se/mirror/qt.io/qtproject/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/pyside-setup-everywhere-src-6.11.2.tar.xz"
        ExpectedSha256 = "cba47efbaad1bedd529725cbc14e21f156c7a19366f07b3edfbb076ffd7afdf8"
    }
)

foreach ($item in $files) {
    $dest = Join-Path $OutputDir $item.Name
    Write-Host "Downloading $($item.Name)..."
    Invoke-WebRequest -Uri $item.Url -OutFile $dest

    $hash = (Get-FileHash $dest -Algorithm SHA256).Hash.ToLower()
    Write-Host "  SHA256: $hash"

    if ($item.ExpectedSha256) {
        if ($hash -ne $item.ExpectedSha256) {
            throw "SHA256 mismatch for $($item.Name)"
        }
        Write-Host "  Verified." -ForegroundColor Green
    } else {
        Write-Host "  NOTE: record this SHA256 in THIRD_PARTY_VERSIONS.md before release." -ForegroundColor Yellow
    }
}

Write-Host
Write-Host "Source archives ready in:"
Write-Host "  $OutputDir"