#
# Helper script to build and run the dependencies test (Windows)
#
# Usage:
#   .\run_test.ps1 -RuntimeLib MD
#   .\run_test.ps1 -RuntimeLib MT -BuildType Debug
#   .\run_test.ps1 -Clean -RuntimeLib MD
#

param(
    [switch]$Clean,
    [Parameter(Mandatory=$true)]
    [ValidateSet("MD", "MT")]
    [string]$RuntimeLib,
    [ValidateSet("Release", "Debug")]
    [string]$BuildType = "Release"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BuildDir = Join-Path $ScriptDir "build_test"

# Clean if requested
if ($Clean -and (Test-Path $BuildDir)) {
    Write-Host "Cleaning build directory..."
    Remove-Item -Recurse -Force $BuildDir
}

# Configure
Write-Host ""
Write-Host "========================================"
Write-Host "  Configuring..."
Write-Host "========================================"

cmake -B $BuildDir -S $ScriptDir -DRUNTIME_LIB=$RuntimeLib -DCMAKE_BUILD_TYPE=$BuildType

# Build
Write-Host ""
Write-Host "========================================"
Write-Host "  Building..."
Write-Host "========================================"

cmake --build $BuildDir --config $BuildType

# Run
Write-Host ""
Write-Host "========================================"
Write-Host "  Running test..."
Write-Host "========================================"

$ExePath = Join-Path $BuildDir $BuildType "DependenciesTest.exe"
if (-not (Test-Path $ExePath)) {
    $ExePath = Join-Path $BuildDir "DependenciesTest.exe"
}

& $ExePath
