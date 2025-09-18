# Stop the script when a cmdlet or a native command fails
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

if ($args.Count -lt 3 -or [string]::IsNullOrEmpty($args[0]) -or [string]::IsNullOrEmpty($args[1]) -or [string]::IsNullOrEmpty($args[2])) {
	Write-Host "Bad call : BuildScript {x86_64|arm} {Release|Debug} {MD|MT}`n"
	exit 1
}

$LIB_NAME = "libzmq"
$PLATFORM = "windows." + $args[0]
$BUILD_TYPE = $args[1]
$RUNTIME_LIB = $args[2]

$SOURCE_DIR = "./repositories/$LIB_NAME"
$BUILD_DIR = "./builds/$PLATFORM-$BUILD_TYPE-$RUNTIME_LIB/$LIB_NAME"
$INSTALL_DIR = "./output/$PLATFORM-$BUILD_TYPE-$RUNTIME_LIB"

$MSVC_ARCH = if ($args[0] -eq "arm") { "arm" } else { "x64" }
$RUNTIME = "MultiThreaded"
if ($BUILD_TYPE -eq "Debug") { $RUNTIME += "Debug" }
if ($RUNTIME_LIB -eq "MD") { $RUNTIME += "DLL" }

$RUNTIME = "MultiThreaded"
if ($BUILD_TYPE -eq "Debug") {
	$RUNTIME += "Debug"
}
if ($RUNTIME_LIB -eq "MD") {
	$RUNTIME += "DLL"
}

if ($BUILD_TYPE -eq "Debug") {
	$CMAKE_OPTIONS = @{
		"CMAKE_MSVC_RUNTIME_LIBRARY" = "$RUNTIME"
		"CMAKE_C_FLAGS" = "/${RUNTIME_LIB}d /Od /Zi /D_DEBUG /EHsc"
		"CMAKE_C_FLAGS_DEBUG" = "/${RUNTIME_LIB}d /Od /Zi /D_DEBUG /EHsc"
		"CMAKE_CXX_FLAGS" = "/${RUNTIME_LIB}d /Od /Zi /D_DEBUG /EHsc"
		"CMAKE_CXX_FLAGS_DEBUG" = "/${RUNTIME_LIB}d /Od /Zi /D_DEBUG /EHsc"
	}
}
else {
	$CMAKE_OPTIONS = @{
		"CMAKE_MSVC_RUNTIME_LIBRARY" = "$RUNTIME"
		"CMAKE_C_FLAGS" = "/$RUNTIME_LIB /O2 /DNDEBUG /EHsc"
		"CMAKE_C_FLAGS_RELEASE" = "/$RUNTIME_LIB /O2 /DNDEBUG /EHsc"
		"CMAKE_CXX_FLAGS" = "/$RUNTIME_LIB /O2 /DNDEBUG /EHsc"
		"CMAKE_CXX_FLAGS_RELEASE" = "/$RUNTIME_LIB /O2 /DNDEBUG /EHsc"
	}
}

$CMAKE_OPTIONS += @{
	"CMAKE_INSTALL_PREFIX" = "$INSTALL_DIR"
	"CMAKE_PREFIX_PATH" = "$INSTALL_DIR"
	"ENABLE_ASAN" = "Off"
	"ENABLE_TSAN"  ="Off"
	"ENABLE_UBSAN" = "Off"
	"ENABLE_INTRINSICS" = "Off"
	"WITH_OPENPGM" = "Off"
	"WITH_NORM" = "Off"
	"WITH_VMCI" = "Off"
	"ENABLE_DRAFTS" = "Off"
	"ENABLE_WS" = "Off"
	"ENABLE_RADIX_TREE" = "Off"
	#"WITH_TLS" = "Off" # Unix only
	"WITH_NSS" = "Off"
	"WITH_LIBSODIUM" = "Off"
	"WITH_LIBSODIUM_STATIC" = "Off"
	"ENABLE_LIBSODIUM_RANDOMBYTES_CLOSE" = "Off"
	"ENABLE_CURVE" = "Off"
	"WITH_GSSAPI_KRB5" = "Off"
	"WITH_MILITANT" = "Off"
	"ENABLE_EVENTFD" = "Off"
	"ENABLE_ANALYSIS" = "Off"
	"LIBZMQ_PEDANTIC" = "On"
	"LIBZMQ_WERROR" = "Off"
	"WITH_DOCS" = "Off"
	"ENABLE_PRECOMPILED" = "On"
	"BUILD_SHARED" = "On"
	"BUILD_STATIC" = "On"
	#"WITH_PERF_TOOL" = "On" # Unix only
	"BUILD_TESTS" = "Off"
	"ENABLE_CPACK" = "On"
	"ENABLE_CLANG" = "On"
	"ENABLE_NO_EXPORT" = "Off"
}

$CMAKE_DEFS = @()
$CMAKE_OPTIONS.GetEnumerator() | ForEach-Object {
	$CMAKE_DEFS += "-D$($_.Name)=$($_.Value)"
}

Write-Host "`n======================== Configuring '$LIB_NAME' for '$PLATFORM-$BUILD_TYPE' ... ========================`n"

cmake -S $SOURCE_DIR -B $BUILD_DIR -G "Visual Studio 17 2022" -A $MSVC_ARCH $CMAKE_DEFS

Write-Host "`n======================== Building ... ========================`n"

cmake --build $BUILD_DIR --config $BUILD_TYPE

# This lib install .dll from MSVC
Write-Host "`n======================== Installing ... ========================`n"

cmake --install $BUILD_DIR --config $BUILD_TYPE

$pdbSourceDir = "$BUILD_DIR/lib/$BUILD_TYPE"
$pdbDestinationDir = "$INSTALL_DIR/lib"

if ($BUILD_TYPE -eq "Debug") {
	if ( Test-Path $pdbSourceDir ) {
		Get-ChildItem -Path $pdbSourceDir -Filter *.pdb | ForEach-Object {
			Write-Host "Copying $($_.Name) to $pdbDestinationDir"
			Copy-Item -Path $_.FullName -Destination $pdbDestinationDir
		}
	} else {
		Write-Host "PDB source directory not found: $pdbSourceDir. Skipping PDB copy." -ForegroundColor Yellow
	}
}

Write-Host "`n======================== Success ! ========================`n"
