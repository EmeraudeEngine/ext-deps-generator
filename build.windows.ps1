# Stop the script when a cmdlet or a native command fails
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

if ($args.Count -lt 1) {
    $ARCH = "x86_64"
} else {
    $ARCH = $args[0]
}

if ($args.Count -lt 2) {
    $BUILD_TYPE = "Release"
} else {
    $BUILD_TYPE = $args[1]
}

if ($args.Count -lt 3) {
    $RUNTIME_LIB = "MD"
} else {
    $RUNTIME_LIB = $args[2]
}

if ($ARCH -ne "x86_64" -and $ARCH -ne "arm64") {
    Write-Host "ARCH argument should be 'x86_64' or 'arm64' ! '$ARCH' unavailable."
    exit 1
}

if ($BUILD_TYPE -ne "Release" -and $BUILD_TYPE -ne "Debug") {
    Write-Host "BUILD_TYPE argument should be 'Release' or 'Debug' ! '$BUILD_TYPE' unavailable."
    exit 1
}

if ($RUNTIME_LIB -ne "MD" -and $RUNTIME_LIB -ne "MT") {
    Write-Host "RUNTIME_LIB argument should be 'MD' or 'MT' ! '$BUILD_TYPE' unavailable."
    exit 1
}

Write-Host "ARCH: $ARCH"
Write-Host "BUILD_TYPE: $BUILD_TYPE"
Write-Host "RUNTIME_LIB: $RUNTIME_LIB"

Write-Host "\n======================== Building dependencies for 'windows.$ARCH-$BUILD_TYPE-$RUNTIME_LIB' ... ========================\n"

& ./scripts/windows/build.zlib.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.bzip2.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.xz.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.pthread-win32.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.zstd.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.brotli.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.harfbuzz.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.libjpeg-turbo.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.cpu_features.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.hwloc.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.openal-soft.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.libsamplerate.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.libzmq.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.libwebp.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.cryptopp-cmake.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.clipper2.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}

# Below are the projects that require the above to be compiled.

& ./scripts/windows/build.taglib.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.cppzmq.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.libpng.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.libzip.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.lib3mf.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}
& ./scripts/windows/build.freetype.ps1 ${ARCH} ${BUILD_TYPE} ${RUNTIME_LIB}

Write-Host "\n======================== Finished ! ========================\n"
