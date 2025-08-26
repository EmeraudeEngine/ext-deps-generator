# Stop the script when a cmdlet or a native command fails
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

if ($args.Count -lt 3 -or [string]::IsNullOrEmpty($args[0]) -or [string]::IsNullOrEmpty($args[1]) -or [string]::IsNullOrEmpty($args[2])) {
	Write-Host "Bad call : BuildScript {x86_64|arm} {Release|Debug} {MD|MT}`n"
	exit 1
}

$LIB_NAME = "libjpeg-turbo"
$PLATFORM = "windows." + $args[0]
$BUILD_TYPE = $args[1]
$RUNTIME_LIB = $args[2]

$SOURCE_DIR = "./repositories/$LIB_NAME"
$BUILD_DIR = "./builds/$PLATFORM-$BUILD_TYPE-$RUNTIME_LIB/$LIB_NAME"
$INSTALL_DIR = "./output/$PLATFORM-$BUILD_TYPE-$RUNTIME_LIB"

if ( $RUNTIME_LIB -eq "MT" ) {
	if ($BUILD_TYPE -eq "Debug") {
		$MSVC_RUNTIME = "MultiThreadedDebug"
	} else {
		$MSVC_RUNTIME = "MultiThreaded"
	}
} else {
	if ($BUILD_TYPE -eq "Debug") {
		$MSVC_RUNTIME = "MultiThreadedDebugDLL"
	} else {
		$MSVC_RUNTIME = "MultiThreadedDLL"
	}
}

Write-Host "`n======================== Configuring '$LIB_NAME' for '$PLATFORM-$BUILD_TYPE' ... ========================`n"

cmake -S $SOURCE_DIR -B $BUILD_DIR -G "Visual Studio 17 2022" -A x64 `
-DCMAKE_BUILD_TYPE="$BUILD_TYPE" `
-DCMAKE_INSTALL_PREFIX="$INSTALL_DIR" `
-DCMAKE_MSVC_RUNTIME_LIBRARY="$MSVC_RUNTIME" `
-DCMAKE_C_FLAGS_RELEASE="/$RUNTIME_LIB" `
-DCMAKE_C_FLAGS_DEBUG="/$RUNTIME_LIBd" `
-DCMAKE_CXX_FLAGS_RELEASE="/$RUNTIME_LIB" `
-DCMAKE_CXX_FLAGS_DEBUG="/$RUNTIME_LIBd" `
-DCMAKE_PREFIX_PATH="$INSTALL_DIR" `
-DCMAKE_ASM_NASM_COMPILER="C:\Program Files\NASM\nasm.exe" `
-DENABLE_SHARED=Off `
-DENABLE_STATIC=On `
-DREQUIRE_SIMD=Off `
-DWITH_ARITH_DEC=On `
-DWITH_ARITH_ENC=On `
-DWITH_JAVA=Off `
-DWITH_JPEG7=Off `
-DWITH_JPEG8=Off `
-DWITH_SIMD=On `
-DWITH_TURBOJPEG=On `
-DWITH_FUZZ=Off

Write-Host "`n======================== Building ... ========================`n"

cmake --build $BUILD_DIR --config $BUILD_TYPE

Write-Host "`n======================== Installing ... ========================`n"

cmake --install $BUILD_DIR --config $BUILD_TYPE

$pdbSourceDir = "$BUILD_DIR/$BUILD_TYPE"
$pdbDestinationDir = "$INSTALL_DIR/lib"

if ( Test-Path $pdbSourceDir ) {
	Get-ChildItem -Path $pdbSourceDir -Filter *.pdb | ForEach-Object {
		Write-Host "Copying $($_.Name) to $pdbDestinationDir"
		Copy-Item -Path $_.FullName -Destination $pdbDestinationDir
	}
} else {
	Write-Host "PDB source directory not found: $pdbSourceDir. Skipping PDB copy." -ForegroundColor Yellow
}

Write-Host "`n======================== Success ! ========================`n"
