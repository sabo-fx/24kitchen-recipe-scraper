[CmdletBinding()]
param(
    [string]$UrlListPath,
    [string]$OutputDirectory,
    [string]$AssetsDirectory,
    [string]$PythonPath,
    [switch]$KeepTemp
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) { (Get-Location).Path } else { $PSScriptRoot }

if ([string]::IsNullOrWhiteSpace($UrlListPath)) {
    $UrlListPath = Join-Path $scriptRoot "recipe-urls.txt"
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $scriptRoot "reports"
}
if ([string]::IsNullOrWhiteSpace($AssetsDirectory)) {
    $AssetsDirectory = Join-Path $OutputDirectory "24kitchen-assets"
}

function Resolve-PythonPath {
    param(
        [string]$PreferredPath
    )

    if (-not [string]::IsNullOrWhiteSpace($PreferredPath)) {
        if (-not (Test-Path -LiteralPath $PreferredPath)) {
            throw "Python executable not found: $PreferredPath"
        }
        return (Resolve-Path -LiteralPath $PreferredPath).Path
    }

    $candidates = @(
        (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCommand) {
        return $pythonCommand.Source
    }

    throw "No usable Python runtime found. Pass -PythonPath explicitly."
}

$resolvedPython = Resolve-PythonPath -PreferredPath $PythonPath
$resolvedUrlListPath = Resolve-Path -LiteralPath $UrlListPath -ErrorAction Stop
$resolvedOutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$resolvedAssetsDirectory = [System.IO.Path]::GetFullPath($AssetsDirectory)
$batchScriptPath = Join-Path $scriptRoot "data\build_recipe_pdfs.py"
$logoPath = Join-Path $resolvedAssetsDirectory "logo.png"

if (-not (Test-Path -LiteralPath $batchScriptPath)) {
    throw "Batch script not found: $batchScriptPath"
}

New-Item -ItemType Directory -Force -Path $resolvedOutputDirectory | Out-Null
New-Item -ItemType Directory -Force -Path $resolvedAssetsDirectory | Out-Null

$arguments = @(
    $batchScriptPath,
    "--url-list", $resolvedUrlListPath,
    "--output-dir", $resolvedOutputDirectory,
    "--assets-dir", $resolvedAssetsDirectory,
    "--logo-path", $logoPath
)

if ($KeepTemp) {
    $arguments += "--keep-temp"
}

& $resolvedPython $arguments

if ($LASTEXITCODE -ne 0) {
    throw "Recipe PDF batch failed with exit code $LASTEXITCODE."
}
