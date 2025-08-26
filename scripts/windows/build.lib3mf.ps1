# Stop the script when a cmdlet or a native command fails
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

if ($args.Count -lt 3 -or [string]::IsNullOrEmpty($args[0]) -or [string]::IsNullOrEmpty($args[1]) -or [string]::IsNullOrEmpty($args[2])) {
	Write-Host "Bad call : BuildScript {x86_64|arm} {Release|Debug} {MD|MT}`n"
	exit 1
}

$LIB_NAME = "lib3mf"
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
-DCMAKE_PREFIX_PATH="$INSTALL_DIR"

Write-Host "`n======================== Building ... ========================`n"

cmake --build $BUILD_DIR --config $BUILD_TYPE

Write-Host "`n======================== Installing ... ========================`n"

cmake --install $BUILD_DIR --config $BUILD_TYPE

Write-Host "`n======================== Success ! ========================`n"
