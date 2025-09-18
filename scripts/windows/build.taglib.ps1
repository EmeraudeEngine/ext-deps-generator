# Stop the script when a cmdlet or a native command fails
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

if ($args.Count -lt 3 -or [string]::IsNullOrEmpty($args[0]) -or [string]::IsNullOrEmpty($args[1]) -or [string]::IsNullOrEmpty($args[2])) {
	Write-Host "Bad call : BuildScript {x86_64|arm} {Release|Debug} {MD|MT}`n"
	exit 1
}

$LIB_NAME = "taglib"
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
	"UTF8_TESTS" = "Off"
	"UTF8_INSTALL" = "Off"
	"UTF8_SAMPLES" = "Off"
	"BUILD_SHARED_LIBS" = "Off"
	"BUILD_FRAMEWORK" = "Off" # Apple only
	"ENABLE_STATIC_RUNTIME" = if ($RUNTIME_LIB -eq "MT") { "On" } else { "Off" }
	"ENABLE_CCACHE" = "Off"
	"VISIBILITY_HIDDEN" = "Off"
	"BUILD_EXAMPLES" = "Off"
	"BUILD_BINDINGS" = "Off"
	"NO_ITUNES_HACKS" = "Off"
	"PLATFORM_WINRT" = "Off"
	"WITH_APE" = "On"
	"WITH_ASF" = "On"
	"WITH_DSF" = "On"
	"WITH_MOD" = "On"
	"WITH_MP4" = "On"
	"WITH_RIFF" = "On"
	"WITH_SHORTEN" = "On"
	"WITH_TRUEAUDIO" = "On"
	"WITH_VORBIS" = "On"
	"WITH_ZLIB" = "On"
	"TRACE_IN_RELEASE" = "Off"
	"BUILD_TESTING" = "Off"
}

$CMAKE_DEFS = @()
$CMAKE_OPTIONS.GetEnumerator() | ForEach-Object {
	$CMAKE_DEFS += "-D$($_.Name)=$($_.Value)"
}

Write-Host "`n======================== Configuring '$LIB_NAME' for '$PLATFORM-$BUILD_TYPE' ... ========================`n"

cmake -S $SOURCE_DIR -B $BUILD_DIR -G "Visual Studio 17 2022" -A $MSVC_ARCH $CMAKE_DEFS

Write-Host "`n======================== Building ... ========================`n"

cmake --build $BUILD_DIR --config $BUILD_TYPE

Write-Host "`n======================== Installing ... ========================`n"

cmake --install $BUILD_DIR --config $BUILD_TYPE

$pdbSourceDir = "$BUILD_DIR/taglib/$BUILD_TYPE"
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
