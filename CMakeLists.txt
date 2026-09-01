########################################################################
# Dependencies Inclusion Test
#
# This CMakeLists.txt verifies that the external libraries have already
# been built (output/<config>/lib must exist) and compiles a test
# executable that links against all of them. It does NOT invoke build.py;
# build the libraries first with one of:
#   python build.py --runtime-lib MT|MD --build-type Release|Debug   (Windows)
#   python build.py --build-type Release|Debug                       (Linux)
#   python build.py --macos-sdk <ver> --build-type Release|Debug     (macOS)
#
# Usage:
#   # macOS (SDK version required)
#   cmake -B builds/tests -DMACOS_SDK=12.0
#
#   # Windows (runtime library required)
#   cmake -B builds/tests -DRUNTIME_LIB=MD
#
#   # Linux (no extra options needed)
#   cmake -B builds/tests
#
#   # Then build
#   cmake --build builds/tests
########################################################################

cmake_minimum_required(VERSION 3.20)
cmake_policy(VERSION 3.20)

project(DependenciesTest VERSION 1.0.0 DESCRIPTION "Dependencies inclusion test")

set(CMAKE_VERBOSE_MAKEFILE ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set_property(GLOBAL PROPERTY USE_FOLDERS ON)

########################################################################
# Platform detection and validation
########################################################################

# Detect platform
if(APPLE)
    set(DETECTED_PLATFORM "macos")
    if(CMAKE_OSX_ARCHITECTURES STREQUAL "arm64" OR CMAKE_SYSTEM_PROCESSOR STREQUAL "arm64")
        set(DETECTED_ARCH "arm64")
    else()
        set(DETECTED_ARCH "x86_64")
    endif()
elseif(WIN32)
    set(DETECTED_PLATFORM "windows")
    set(DETECTED_ARCH "x86_64")
else()
    set(DETECTED_PLATFORM "linux")
    set(DETECTED_ARCH "x86_64")
endif()

# Detect build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Release")
endif()

message(STATUS "Platform: ${DETECTED_PLATFORM}")
message(STATUS "Architecture: ${DETECTED_ARCH}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")

########################################################################
# Platform-specific required options
########################################################################

# macOS: require SDK version
if(APPLE)
    if(NOT DEFINED MACOS_SDK)
        message(FATAL_ERROR
            "macOS SDK version is required.\n"
            "Please specify it with: cmake -DMACOS_SDK=12.0 ..\n"
            "Available SDKs can be listed with: xcodebuild -showsdks")
    endif()
    message(STATUS "macOS SDK: ${MACOS_SDK}")
endif()

# Windows: require runtime library
if(WIN32)
    if(NOT DEFINED RUNTIME_LIB)
        message(FATAL_ERROR
            "Windows runtime library is required.\n"
            "Please specify it with: cmake -DRUNTIME_LIB=MD ..\n"
            "Options:\n"
            "  MD  - Dynamic runtime (MultiThreadedDLL)\n"
            "  MT  - Static runtime (MultiThreaded)")
    endif()
    if(NOT RUNTIME_LIB STREQUAL "MD" AND NOT RUNTIME_LIB STREQUAL "MT")
        message(FATAL_ERROR "RUNTIME_LIB must be either MD or MT")
    endif()
    message(STATUS "Runtime library: ${RUNTIME_LIB}")
endif()

########################################################################
# Build configuration string
########################################################################

# build.py passes the authoritative folder name via -DLIBS_CONFIG — it is the
# single source of truth (BuildConfig.build_suffix in builder/config.py). When
# this file is configured by hand (cmake -B builds/tests), we must re-derive the
# exact same name here, including the OS-specific ABI tag.
if(NOT DEFINED LIBS_CONFIG)
    if(WIN32)
        set(LIBS_CONFIG "${DETECTED_PLATFORM}.${DETECTED_ARCH}-${CMAKE_BUILD_TYPE}-${RUNTIME_LIB}")
    elseif(APPLE)
        set(LIBS_CONFIG "${DETECTED_PLATFORM}.${DETECTED_ARCH}-${CMAKE_BUILD_TYPE}-sdk${MACOS_SDK}")
    else()
        # Linux: mirror detect_libc_tag() — tag with the host glibc floor so this
        # matches the directory build.py installed into.
        set(_libc_tag "")
        execute_process(
            COMMAND getconf GNU_LIBC_VERSION
            OUTPUT_VARIABLE _libc_raw
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET)
        # _libc_raw looks like "glibc 2.41"; normalise "gnu" -> "glibc".
        if(_libc_raw MATCHES "([A-Za-z]+)[ \t]+([0-9][0-9.]*)")
            string(TOLOWER "${CMAKE_MATCH_1}" _libc_name)
            if(_libc_name STREQUAL "gnu")
                set(_libc_name "glibc")
            endif()
            set(_libc_tag "-${_libc_name}${CMAKE_MATCH_2}")
        endif()
        set(LIBS_CONFIG "${DETECTED_PLATFORM}.${DETECTED_ARCH}-${CMAKE_BUILD_TYPE}${_libc_tag}")
    endif()
endif()
set(LIBS_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/output/${LIBS_CONFIG}")

message(STATUS "Libraries config: ${LIBS_CONFIG}")
message(STATUS "Libraries root: ${LIBS_ROOT}")

########################################################################
# Verify dependencies are present
########################################################################

# The test executable consumes pre-built libraries from output/<config>/lib.
# Building them is the job of build.py; this CMakeLists never invokes it.
if(NOT IS_DIRECTORY "${LIBS_ROOT}/lib")
    if(WIN32)
        set(_build_hint "python build.py --runtime-lib ${RUNTIME_LIB} --build-type ${CMAKE_BUILD_TYPE}")
    elseif(APPLE)
        set(_build_hint "python build.py --macos-sdk ${MACOS_SDK} --build-type ${CMAKE_BUILD_TYPE}")
    else()
        set(_build_hint "python build.py --build-type ${CMAKE_BUILD_TYPE}")
    endif()
    message(FATAL_ERROR
        "External libraries not found for config '${LIBS_CONFIG}'.\n"
        "Expected: ${LIBS_ROOT}/lib\n"
        "Build them first with:\n"
        "  ${_build_hint}")
endif()

########################################################################
# Executable
########################################################################

add_executable(${PROJECT_NAME} "${CMAKE_CURRENT_SOURCE_DIR}/src/main.cpp")

set_target_properties(${PROJECT_NAME} PROPERTIES
    C_STANDARD 17
    C_STANDARD_REQUIRED ON
    CXX_STANDARD 20
    CXX_STANDARD_REQUIRED ON
)

# Windows: Set MSVC runtime library to match dependencies
if(WIN32)
    if(RUNTIME_LIB STREQUAL "MT")
        set_property(TARGET ${PROJECT_NAME} PROPERTY
            MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
    else()
        set_property(TARGET ${PROJECT_NAME} PROPERTY
            MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
    endif()
endif()

########################################################################
# Include directories
########################################################################

# NOTE: order matters. "${LIBS_ROOT}/include" MUST come first: tinyusdz vendors its own
# zstd.h under external/, and the cascade's real zstd.h has to win.
target_include_directories(${PROJECT_NAME} PRIVATE
    "${LIBS_ROOT}/include"
    "${LIBS_ROOT}/include/freetype2"
    "${LIBS_ROOT}/include/libpng16"
    # tinyusdz headers include one another by paths relative to the ROOT of its source
    # tree ("nonstd/optional.hpp", "core/path.hh", "value-types.hh"), which the patch
    # preserves on install. Reaching tinyusdz.hh through "${LIBS_ROOT}/include" alone is
    # therefore not enough — both dirs below must be on the include path (they mirror the
    # $<INSTALL_INTERFACE:...> entries exported by patches/tinyusdz.patch).
    "${LIBS_ROOT}/include/tinyusdz"
    "${LIBS_ROOT}/include/tinyusdz/external"
)

########################################################################
# Compile definitions for static libraries
########################################################################

# Static linking definitions (required for all platforms)
target_compile_definitions(${PROJECT_NAME} PRIVATE
    LUNASVG_BUILD_STATIC  # LunaSVG static linking
    PLUTOVG_BUILD_STATIC  # PlutoVG static linking
    # simdjson: this one is an ABI matter. It adds four data members to `document_stream`
    # (worker thread, its parser, its error, the use_thread flag). The archive is compiled
    # with SIMDJSON_ENABLE_THREADS=ON, so a consumer that omits the macro sees a SMALLER
    # class than the code it links against — a silent layout mismatch, not a link error.
    # Upstream propagates it as a PUBLIC definition on the simdjson target; the raw archive
    # carries nothing, so it must be set here (and in the engine).
    SIMDJSON_THREADS_ENABLED=1
    # simdjson: the archive is built without the exception-throwing interface, because the
    # engine consuming it compiles without exceptions. This is an API selection, not a
    # detail — `simdjson_result<T>` no longer converts implicitly to `T`, so every access
    # goes through `.get(out) != simdjson::SUCCESS`. Same PUBLIC-definition story as above;
    # unlike THREADS_ENABLED, forgetting it fails at compile time rather than silently.
    SIMDJSON_EXCEPTIONS=0
)

if(WIN32)
    target_compile_definitions(${PROJECT_NAME} PRIVATE
        NOMINMAX            # Prevent windows.h from defining min/max macros
        LZMA_API_STATIC     # xz/lzma static linking
        AL_LIBTYPE_STATIC   # OpenAL static linking
        ZMQ_STATIC          # ZeroMQ static linking
        TAGLIB_STATIC       # TagLib static linking
        FLAC__NO_DLL        # FLAC static linking (avoid __declspec(dllimport))
        KHRONOS_STATIC      # libktx static linking (avoid __declspec(dllimport))
    )
endif()

########################################################################
# Link directories (allows CMake to configure before libs exist)
########################################################################

target_link_directories(${PROJECT_NAME} PRIVATE "${LIBS_ROOT}/lib")

########################################################################
# Link libraries (order matters for static linking!)
########################################################################

# Library names vary by platform and debug/release
if(WIN32)
    # Windows library names
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        set(FREETYPE_LIB "freetyped")
        set(PNG_LIB "libpng16_staticd")
        set(JPEG_LIB "jpeg-static")
        set(TURBOJPEG_LIB "turbojpeg-static")
        set(ZLIB_LIB "zlibstaticd")
        set(ZSTD_LIB "zstd_static")
        # libtiff appends "d" on Windows only (cmake/WindowsSupport.cmake)
        set(TIFF_LIB "tiffd")
        set(TIFFXX_LIB "tiffxxd")
    else()
        set(FREETYPE_LIB "freetype")
        set(PNG_LIB "libpng16_static")
        set(JPEG_LIB "jpeg-static")
        set(TURBOJPEG_LIB "turbojpeg-static")
        set(ZLIB_LIB "zlibstatic")
        set(ZSTD_LIB "zstd_static")
        set(TIFF_LIB "tiff")
        set(TIFFXX_LIB "tiffxx")
    endif()
    set(WEBP_LIB "libwebp")
    set(SHARPYUV_LIB "libsharpyuv")
    set(OPENAL_LIB "OpenAL32")
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        set(ZMQ_LIB "libzmq-v143-mt-sgd-4_3_6")
    else()
        set(ZMQ_LIB "libzmq-v143-mt-s-4_3_6")
    endif()
    # libvpx: the configure script bakes the CRT into the basename and appends "d"
    # for the Debug configuration — vpx{mt|md}[d].lib (AGENTS.md § MSYS2 Builder).
    # A Debug package contains ONLY the "d" variant (the Release-CRT twin that
    # `make install` ships unconditionally is purged by the msys2 builder).
    if(RUNTIME_LIB STREQUAL "MT")
        set(VPX_LIB "vpxmt")
    else()
        set(VPX_LIB "vpxmd")
    endif()
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        set(VPX_LIB "${VPX_LIB}d")
    endif()
    # Audio codec libs (best-effort Windows defaults; adjust if upstream produces
    # different basenames on MSVC).
    set(OGG_LIB "ogg")
    set(VORBIS_LIB "vorbis")
    set(VORBISENC_LIB "vorbisenc")
    set(VORBISFILE_LIB "vorbisfile")
    set(OPUS_LIB "opus")
    set(FLAC_LIB "FLAC")
    # mpg123's cmake port forces `PREFIX lib` on the target since b41e9d9 (the v015
    # submodule bump), so the MSVC artifact is libmpg123.lib, not mpg123.lib.
    set(MPG123_LIB "libmpg123")
    set(LAME_LIB "mp3lame")
    set(SNDFILE_LIB "sndfile")
    # Shader / SPIR-V (SPIRV-Tools-* keep their basenames in Debug)
    set(SPIRV_TOOLS_LIB "SPIRV-Tools")
    set(SPIRV_TOOLS_OPT_LIB "SPIRV-Tools-opt")
    # glslang ships as multiple static libs that must all be linked together.
    # The glslang build appends a "d" suffix in Debug; SPIRV-Tools does not.
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        set(GLSLANG_LIBS glslangd MachineIndependentd GenericCodeGend OSDependentd SPIRVd glslang-default-resource-limitsd)
    else()
        set(GLSLANG_LIBS glslang MachineIndependent GenericCodeGen OSDependent SPIRV glslang-default-resource-limits)
    endif()
    # Process control
    set(REPROC_LIB "reproc")
    set(REPROC_CPP_LIB "reproc++")
    # Other
    set(UFBX_LIB "ufbx")
    set(BC7ENC_LIB "bc7enc_rdo")
    # ktx / meshoptimizer / tinyusdz keep their basenames in Debug (no "d" postfix)
    set(KTX_LIB "ktx")
    set(MESHOPT_LIB "meshoptimizer")
    set(TINYUSDZ_LIB "tinyusdz_static")
    # draco: same basename on every platform and in Debug. On MSVC draco
    # builds the target "draco" (draco.lib); elsewhere it is "draco_static" with
    # OUTPUT_NAME draco, so the archive is libdraco.a either way.
    set(DRACO_LIB "draco")
    # onnxruntime is a SHARED library (see libraries/onnxruntime.yaml): onnxruntime.dll
    # plus its import lib here, libonnxruntime.so elsewhere. Same short name either way.
    set(ONNXRUNTIME_LIB "onnxruntime")
    set(SIMDJSON_LIB "simdjson")
    # lib3mf (static): static archive name matches the CMake target name.
    set(LIB3MF_LIB "lib3mf")
    # pthread-win32: static build; pthreadVC3 is the C/setjmp flavor (VCE3/VSE3
    # are the C++ EH and SEH variants, also installed but not linked here).
    set(PTHREADWIN32_LIB "pthreadVC3")
else()
    # Unix library names
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        set(FREETYPE_LIB "freetyped")
        set(PNG_LIB "png16d")
    else()
        set(FREETYPE_LIB "freetype")
        set(PNG_LIB "png16")
    endif()
    set(JPEG_LIB "jpeg")
    set(TURBOJPEG_LIB "turbojpeg")
    # libtiff's "d" debug postfix is Windows-only
    set(TIFF_LIB "tiff")
    set(TIFFXX_LIB "tiffxx")
    set(WEBP_LIB "webp")
    set(SHARPYUV_LIB "sharpyuv")
    set(OPENAL_LIB "openal")
    set(ZLIB_LIB "z")
    set(ZSTD_LIB "zstd")
    set(ZMQ_LIB "zmq")
    set(VPX_LIB "vpx")
    # Audio codec libs
    set(OGG_LIB "ogg")
    set(VORBIS_LIB "vorbis")
    set(VORBISENC_LIB "vorbisenc")
    set(VORBISFILE_LIB "vorbisfile")
    set(OPUS_LIB "opus")
    set(FLAC_LIB "FLAC")
    set(MPG123_LIB "mpg123")
    set(LAME_LIB "mp3lame")
    set(SNDFILE_LIB "sndfile")
    # Shader / SPIR-V
    set(SPIRV_TOOLS_LIB "SPIRV-Tools")
    set(SPIRV_TOOLS_OPT_LIB "SPIRV-Tools-opt")
    set(GLSLANG_LIBS glslang MachineIndependent GenericCodeGen OSDependent SPIRV glslang-default-resource-limits)
    # Process control
    set(REPROC_LIB "reproc")
    set(REPROC_CPP_LIB "reproc++")
    # Other
    set(UFBX_LIB "ufbx")
    set(BC7ENC_LIB "bc7enc_rdo")
    set(KTX_LIB "ktx")
    set(MESHOPT_LIB "meshoptimizer")
    set(TINYUSDZ_LIB "tinyusdz_static")
    set(DRACO_LIB "draco")
    set(ONNXRUNTIME_LIB "onnxruntime")
    set(SIMDJSON_LIB "simdjson")
    # lib3mf sets PREFIX "" on its target, so the archive is "lib3mf.a"
    # (not "liblib3mf.a"). Use a full path to bypass the `-l` short-name search,
    # which would otherwise look for "liblib3mf.{a,so,dylib}".
    set(LIB3MF_LIB "${LIBS_ROOT}/lib/lib3mf.a")
endif()

# libktx's static build also installs the astc-encoder archive it vendors, whose
# basename encodes the SIMD ISA it was compiled for (astcenc-avx2-static on x86_64,
# astcenc-neon-static on arm64) — locate it by glob instead of hardcoding the ISA.
# EXCEPT on Apple: there upstream merges the astcenc objects INTO libktx.a itself
# and its install() is gated `NOT APPLE` (KTX-Software CMakeLists.txt:1340), so no
# separate archive exists and none is needed — libktx.a is self-contained
# (verified: nm shows every astcenc_* reference resolved within the archive).
if(APPLE)
    set(ASTCENC_LIB "")
elseif(WIN32)
    file(GLOB ASTCENC_LIB "${LIBS_ROOT}/lib/astcenc-*-static.lib")
else()
    file(GLOB ASTCENC_LIB "${LIBS_ROOT}/lib/libastcenc-*-static.a")
endif()
if(NOT APPLE AND NOT ASTCENC_LIB)
    message(FATAL_ERROR
        "astc-encoder archive not found in ${LIBS_ROOT}/lib "
        "(installed alongside libktx; see libraries/ktx.yaml)")
endif()

# Use library names only - CMake won't validate existence at configure time.
# Order matters for static linking: consumers before providers.
target_link_libraries(${PROJECT_NAME} PRIVATE
    # Shader / SPIR-V (glslang consumes SPIRV-Tools-opt internally)
    ${GLSLANG_LIBS}
    ${SPIRV_TOOLS_OPT_LIB} ${SPIRV_TOOLS_LIB}
    # SVG rendering (lunasvg depends on plutovg)
    lunasvg plutovg
    # Fonts (freetype depends on harfbuzz, png, brotli, bzip2, zlib)
    ${FREETYPE_LIB} harfbuzz
    # Images (png depends on zlib; tiff depends on jpeg, zlib, lzma, zstd, so it —
    # and its C++ stream wrapper tiffxx — must precede them all)
    ${PNG_LIB} ${TIFFXX_LIB} ${TIFF_LIB} ${JPEG_LIB} ${TURBOJPEG_LIB} ${WEBP_LIB} ${SHARPYUV_LIB}
    # Video
    ${VPX_LIB}
    # 3D model formats (lib3mf depends on libzip -> zlib/bzip2/lzma/zstd, so it
    # must precede zip and the compression libs in static link order)
    ${LIB3MF_LIB}
    # Archive (zip depends on zlib, bzip2, lzma, zstd)
    zip
    # Audio I/O (libsndfile depends on flac, vorbis, opus, mpg123, lame, ogg)
    ${SNDFILE_LIB}
    ${OPENAL_LIB} samplerate tag
    # Audio codecs (flac/vorbis depend on ogg)
    ${FLAC_LIB} ${VORBISFILE_LIB} ${VORBISENC_LIB} ${VORBIS_LIB} ${OGG_LIB}
    ${OPUS_LIB} ${MPG123_LIB} ${LAME_LIB}
    # Texture containers (libktx VENDORS an unprefixed zstd — see libraries/ktx.yaml.
    # It must come BEFORE the cascade's zstd: on single-pass Unix linkers libktx's own
    # zstd object is always pulled in to satisfy its internal ZSTD_* references, so
    # every other ZSTD_* reference must resolve from that same archive or the two
    # copies collide with multiple-definition errors.)
    ${KTX_LIB} ${ASTCENC_LIB}
    # Compression (dependencies of above)
    brotlienc brotlidec brotlicommon ${ZSTD_LIB} lzma bz2_static ${ZLIB_LIB}
    # System
    cpu_features hwloc
    # Crypto
    cryptopp
    # TLS (LibreSSL: consumers before providers — tls -> ssl -> crypto;
    # static archive basenames are identical on Unix and MSVC)
    tls ssl crypto
    # Geometry
    Clipper2
    # Networking
    ${ZMQ_LIB}
    # Process control
    ${REPROC_CPP_LIB} ${REPROC_LIB}
    # Data formats
    fastgltf jsoncpp ${SIMDJSON_LIB} ${UFBX_LIB} ${MESHOPT_LIB} ${DRACO_LIB} ${TINYUSDZ_LIB}
    # Texture compression
    ${BC7ENC_LIB}
    # Machine-learning inference (shared library, self-contained: its abseil / onnx /
    # protobuf / re2 / flatbuffers dependencies are linked inside it and export nothing)
    ${ONNXRUNTIME_LIB}
)

# pthread-win32 is Windows-only
if(WIN32)
    target_link_libraries(${PROJECT_NAME} PRIVATE ${PTHREADWIN32_LIB})
endif()

########################################################################
# Platform-specific system libraries
########################################################################

if(APPLE)
    find_library(FRAMEWORK_COREFOUNDATION CoreFoundation REQUIRED)
    find_library(FRAMEWORK_COREAUDIO CoreAudio REQUIRED)
    find_library(FRAMEWORK_AUDIOTOOLBOX AudioToolbox REQUIRED)
    find_library(FRAMEWORK_AUDIOUNIT AudioUnit REQUIRED)
    find_library(FRAMEWORK_IOKIT IOKit REQUIRED)
    find_library(FRAMEWORK_COREGRAPHICS CoreGraphics REQUIRED)
    find_library(FRAMEWORK_CORETEXT CoreText REQUIRED)
    # Foundation: lib3mf with USE_PLATFORM_UUID uses CFUUID via Foundation.
    find_library(FRAMEWORK_FOUNDATION Foundation REQUIRED)

    target_link_libraries(${PROJECT_NAME} PRIVATE
        ${FRAMEWORK_COREFOUNDATION}
        ${FRAMEWORK_COREAUDIO}
        ${FRAMEWORK_AUDIOTOOLBOX}
        ${FRAMEWORK_AUDIOUNIT}
        ${FRAMEWORK_IOKIT}
        ${FRAMEWORK_COREGRAPHICS}
        ${FRAMEWORK_CORETEXT}
        ${FRAMEWORK_FOUNDATION}
    )

elseif(WIN32)
    target_link_libraries(${PROJECT_NAME} PRIVATE
        # Networking
        ws2_32
        iphlpapi
        # Audio
        winmm
        avrt        # OpenAL WASAPI: Av*MmThreadCharacteristics*
        # COM/OLE
        ole32
        shell32
        # Path helpers (mpg123 compat.obj: PathCombineW / PathIsRelativeW / PathIsUNCW)
        shlwapi
        # Harfbuzz dependencies (Uniscribe, DirectWrite, GDI)
        usp10       # Uniscribe
        dwrite      # DirectWrite
        rpcrt4      # UuidCreate
        gdi32       # GDI
        uuid        # lib3mf: IID_*/CLSID_* (Windows SDK)
        # LibreSSL (libcrypto getentropy: BCryptGenRandom; cert store hooks: Crypt*)
        bcrypt
        crypt32
    )

else()
    find_package(Threads REQUIRED)

    target_link_libraries(${PROJECT_NAME} PRIVATE
        Threads::Threads
        ${CMAKE_DL_LIBS}
        m
        uuid        # lib3mf: libuuid (USE_PLATFORM_UUID)
    )
endif()

########################################################################
# Summary
########################################################################

message(STATUS "")
message(STATUS "========================================")
message(STATUS "  Configuration summary")
message(STATUS "========================================")
message(STATUS "  Platform:     ${DETECTED_PLATFORM}")
message(STATUS "  Architecture: ${DETECTED_ARCH}")
message(STATUS "  Build type:   ${CMAKE_BUILD_TYPE}")
if(APPLE)
    message(STATUS "  macOS SDK:    ${MACOS_SDK}")
endif()
if(WIN32)
    message(STATUS "  Runtime lib:  ${RUNTIME_LIB}")
endif()
message(STATUS "  Libs config:  ${LIBS_CONFIG}")
message(STATUS "========================================")
message(STATUS "")
