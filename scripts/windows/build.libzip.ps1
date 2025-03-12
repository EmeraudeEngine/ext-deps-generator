# Stop the script when a cmdlet or a native command fails
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

if ($args.Count -lt 2 -or [string]::IsNullOrEmpty($args[0]) -or [string]::IsNullOrEmpty($args[1])) {
	Write-Host "Bad call : BuildScript {x86_64|arm} {Release|Debug}`n"
	exit 1
}

$LIB_NAME = "libzip"
$PLATFORM = "windows." + $args[0]
$BUILD_TYPE = $args[1]

$SOURCE_DIR = "./repositories/$LIB_NAME"
$BUILD_DIR = "./builds/$PLATFORM-$BUILD_TYPE/$LIB_NAME"
$INSTALL_DIR = "./output/$PLATFORM-$BUILD_TYPE"

if ($BUILD_TYPE -eq "Debug") {
	$MSVC_RUNTIME = "MultiThreadedDebug"
} else {
	$MSVC_RUNTIME = "MultiThreaded"
}

Write-Host "`n======================== Configuring '$LIB_NAME' for '$PLATFORM-$BUILD_TYPE' ... ========================`n"

cmake -S $SOURCE_DIR -B $BUILD_DIR -G "Visual Studio 17 2022" -A x64 `
-DCMAKE_BUILD_TYPE="$BUILD_TYPE" `
-DCMAKE_INSTALL_PREFIX="$INSTALL_DIR" `
-DCMAKE_MSVC_RUNTIME_LIBRARY="$MSVC_RUNTIME" `
-DCMAKE_MSVC_RUNTIME_LIBRARY="$MSVC_RUNTIME" `
-DLIBS_ROOT="./output/${PLATFORM}-${BUILD_TYPE}" `
-DENABLE_COMMONCRYPTO=On `
-DENABLE_GNUTLS=Off `
-DENABLE_MBEDTLS=Off `
-DENABLE_OPENSSL=Off `
-DENABLE_WINDOWS_CRYPTO=Off `
-DENABLE_BZIP2=On `
-DENABLE_LZMA=Off `
-DENABLE_ZSTD=Off `
-DENABLE_FDOPEN=Off `
-DBUILD_TOOLS=On `
-DBUILD_REGRESS=Off `
-DBUILD_OSSFUZZ=Off `
-DBUILD_EXAMPLES=Off `
-DBUILD_DOC=Off `
-DBUILD_SHARED_LIBS=Off `
-DLIBZIP_DO_INSTALL=On `
-DSHARED_LIB_VERSIONNING=On 

# NOTE: ZSTD has been deactivated cause of MT and pthread failure

Write-Host "`n======================== Building ... ========================`n"

cmake --build $BUILD_DIR --config $BUILD_TYPE

Write-Host "`n======================== Installing ... ========================`n"

cmake --install $BUILD_DIR --config $BUILD_TYPE

Write-Host "`n======================== Success ! ========================`n"
