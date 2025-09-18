# Stop the script when a cmdlet or a native command fails
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

if ($args.Count -lt 3 -or [string]::IsNullOrEmpty($args[0]) -or [string]::IsNullOrEmpty($args[1]) -or [string]::IsNullOrEmpty($args[2])) {
	Write-Host "Bad call : BuildScript {x86_64|arm} {Release|Debug} {MD|MT}`n"
	exit 1
}

$LIB_NAME = "openal-soft"
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
		"CMAKE_C_FLAGS" = "/${RUNTIME_LIB}d /Od /Zi /D_DEBUG"
		"CMAKE_C_FLAGS_DEBUG" = "/${RUNTIME_LIB}d /Od /Zi /D_DEBUG"
		"CMAKE_CXX_FLAGS" = "/${RUNTIME_LIB}d /Od /Zi /D_DEBUG"
		"CMAKE_CXX_FLAGS_DEBUG" = "/${RUNTIME_LIB}d /Od /Zi /D_DEBUG"
	}
}
else {
	$CMAKE_OPTIONS = @{
		"CMAKE_MSVC_RUNTIME_LIBRARY" = "$RUNTIME"
		"CMAKE_C_FLAGS" = "/$RUNTIME_LIB /O2 /DNDEBUG"
		"CMAKE_C_FLAGS_RELEASE" = "/$RUNTIME_LIB /O2 /DNDEBUG"
		"CMAKE_CXX_FLAGS" = "/$RUNTIME_LIB /O2 /DNDEBUG"
		"CMAKE_CXX_FLAGS_RELEASE" = "/$RUNTIME_LIB /O2 /DNDEBUG"
	}
}

$CMAKE_OPTIONS += @{
	"CMAKE_INSTALL_PREFIX" = "$INSTALL_DIR"
	"CMAKE_PREFIX_PATH" = "$INSTALL_DIR"
	"LIBTYPE" = "STATIC"
	"ALSOFT_DLOPEN" = "On"
	"ALSOFT_WERROR" = "Off"
	"ALSOFT_UTILS" = "Off"
	"ALSOFT_NO_CONFIG_UTIL" = "On"
	"ALSOFT_EXAMPLES" = "Off"
	"ALSOFT_TESTS" = "Off"
	"ALSOFT_INSTALL" = "On"
	"ALSOFT_INSTALL_CONFIG" = "On"
	"ALSOFT_INSTALL_HRTF_DATA" = "On"
	"ALSOFT_INSTALL_AMBDEC_PRESETS" = "On"
	"ALSOFT_INSTALL_EXAMPLES" = "Off"
	"ALSOFT_INSTALL_UTILS" = "Off"
	"ALSOFT_UPDATE_BUILD_VERSION" = "Off"
	"ALSOFT_EAX" = "On"
	"ALSOFT_SEARCH_INSTALL_DATADIR" = "Off"
	"FORCE_STATIC_VCRT" = if ($RUNTIME_LIB -eq "MT") { "On" } else { "Off" }
	"ALSOFT_BUILD_ROUTER" = "Off" # EXPERIMENTAL
	#"ALSOFT_OSX_FRAMEWORK" = "Off" # Apple only
	#"ALSOFT_STATIC_LIBGCC" = "Off" # Linux Only
	"ALSOFT_STATIC_STDCXX" = "On"
	"ALSOFT_STATIC_WINPTHREAD" = "On"
	"ALSOFT_CPUEXT_SSE" = "On"
	"ALSOFT_REQUIRE_SSE" = "Off"
	"ALSOFT_CPUEXT_SSE2" = "On"
	"ALSOFT_REQUIRE_SSE2" = "Off"
	"ALSOFT_CPUEXT_SSE3" = "On"
	"ALSOFT_REQUIRE_SSE3" = "Off"
	"ALSOFT_CPUEXT_SSE4_1" = "On"
	"ALSOFT_REQUIRE_SSE4_1" = "Off"
	"ALSOFT_CPUEXT_NEON" = "On"
	"ALSOFT_REQUIRE_NEON" = "Off"
	"ALSOFT_ENABLE_SSE2_CODEGEN" = "On"
	"ALSOFT_RTKIT" = "On"
	"ALSOFT_REQUIRE_RTKIT" = "Off"
	"ALSOFT_BACKEND_PIPEWIRE" = "On"
	"ALSOFT_REQUIRE_PIPEWIRE" = "Off"
	"ALSOFT_BACKEND_PULSEAUDIO" = "On"
	"ALSOFT_REQUIRE_PULSEAUDIO" = "Off"
	#"ALSOFT_BACKEND_ALSA" = "On" # Unix only
	#"ALSOFT_REQUIRE_ALSA" = "Off" # Unix only
	#"ALSOFT_BACKEND_OSS" = "On" # Unix only
	#"ALSOFT_REQUIRE_OSS" = "Off" # Unix only
	#"ALSOFT_BACKEND_SOLARIS" = "On" # Solaris only
	#"ALSOFT_REQUIRE_SOLARIS" = "Off" # Solaris only
	#"ALSOFT_BACKEND_SNDIO" = "On" # BSD only
	#"ALSOFT_REQUIRE_SNDIO" = "Off" # BSD only
	"ALSOFT_BACKEND_WINMM" = "On"
	"ALSOFT_REQUIRE_WINMM" = "Off"
	"ALSOFT_BACKEND_DSOUND" = "On"
	"ALSOFT_REQUIRE_DSOUND" = "Off"
	"ALSOFT_BACKEND_WASAPI" = "On"
	"ALSOFT_REQUIRE_WASAPI" = "Off"
	"ALSOFT_BACKEND_OTHERIO" = "Off"
	"ALSOFT_REQUIRE_OTHERIO" = "Off"
	"ALSOFT_BACKEND_JACK" = "On"
	"ALSOFT_REQUIRE_JACK" = "Off"
	"ALSOFT_BACKEND_COREAUDIO" = "Off"
	"ALSOFT_REQUIRE_COREAUDIO" = "Off"
	"ALSOFT_BACKEND_OBOE" = "Off"
	"ALSOFT_REQUIRE_OBOE" = "Off"
	"ALSOFT_BACKEND_OPENSL" = "Off"
	"ALSOFT_REQUIRE_OPENSL" = "Off"
	"ALSOFT_BACKEND_PORTAUDIO" = "On"
	"ALSOFT_REQUIRE_PORTAUDIO" = "Off"
	"ALSOFT_BACKEND_SDL3" = "Off"
	"ALSOFT_REQUIRE_SDL3" = "Off"
	"ALSOFT_BACKEND_SDL2" = "Off"
	"ALSOFT_REQUIRE_SDL2" = "Off"
	"ALSOFT_BACKEND_WAVE" = "On"
	"ALSOFT_EMBED_HRTF_DATA" = "On"
	"ALSOFT_NO_UID_DEFS" = "Off"
}

$CMAKE_DEFS = @()
$CMAKE_OPTIONS.GetEnumerator() | ForEach-Object {
	$CMAKE_DEFS += "-D$($_.Name)=$($_.Value)"
}

Write-Host "`n======================== Configuring '$LIB_NAME' for '$PLATFORM-$BUILD_TYPE' ... ========================`n"

# Debug is ignored by CMake with OpenAL-Soft.
cmake -S $SOURCE_DIR -B $BUILD_DIR -G "Visual Studio 17 2022" -A $MSVC_ARCH $CMAKE_DEFS

Write-Host "`n======================== Building ... ========================`n"

cmake --build $BUILD_DIR --config $BUILD_TYPE

Write-Host "`n======================== Installing ... ========================`n"

cmake --install $BUILD_DIR --config $BUILD_TYPE

$pdbSourceDir = "$BUILD_DIR/$BUILD_TYPE"
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
