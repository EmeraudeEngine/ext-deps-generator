########################################################################
# Dependencies Inclusion Test
#
# This CMakeLists.txt will automatically build the dependencies using
# build.py before building the test executable.
#
# Usage:
#   # macOS (SDK version required)
#   cmake -B build_test -DMACOS_SDK=12.0
#
#   # Windows (runtime library required)
#   cmake -B build_test -DRUNTIME_LIB=MD
#
#   # Linux (no extra options needed)
#   cmake -B build_test
#
#   # Then build
#   cmake --build build_test
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
    set(DETECTED_PLATFORM "mac")
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

if(WIN32)
    set(LIBS_CONFIG "${DETECTED_PLATFORM}.${DETECTED_ARCH}-${CMAKE_BUILD_TYPE}-${RUNTIME_LIB}")
else()
    set(LIBS_CONFIG "${DETECTED_PLATFORM}.${DETECTED_ARCH}-${CMAKE_BUILD_TYPE}")
endif()
set(LIBS_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/output/${LIBS_CONFIG}")

message(STATUS "Libraries config: ${LIBS_CONFIG}")
message(STATUS "Libraries root: ${LIBS_ROOT}")

########################################################################
# Build dependencies with Python script
########################################################################

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Build the command arguments
set(BUILD_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/build.py")
set(BUILD_ARGS
    "--arch" "${DETECTED_ARCH}"
    "--build-type" "${CMAKE_BUILD_TYPE}"
)

if(APPLE)
    list(APPEND BUILD_ARGS "--macos-sdk" "${MACOS_SDK}")
endif()

if(WIN32)
    list(APPEND BUILD_ARGS "--runtime-lib" "${RUNTIME_LIB}")
endif()

# Create a stamp file per configuration to track if dependencies were built
set(DEPS_STAMP "${CMAKE_CURRENT_BINARY_DIR}/deps_built_${LIBS_CONFIG}.stamp")

# Also check if output directory exists (in case stamp is stale)
add_custom_command(
    OUTPUT "${DEPS_STAMP}"
    COMMAND ${Python3_EXECUTABLE} ${BUILD_SCRIPT} ${BUILD_ARGS}
    COMMAND ${CMAKE_COMMAND} -E touch "${DEPS_STAMP}"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    COMMENT "Building dependencies for ${LIBS_CONFIG}..."
    VERBATIM
)

add_custom_target(BuildDependencies
    DEPENDS "${DEPS_STAMP}"
)

# Force rebuild if output directory doesn't exist
if(NOT EXISTS "${LIBS_ROOT}/lib")
    file(REMOVE "${DEPS_STAMP}")
endif()

########################################################################
# Executable
########################################################################

add_executable(${PROJECT_NAME} "${CMAKE_CURRENT_SOURCE_DIR}/src/main.cpp")

# Make sure dependencies are built first
add_dependencies(${PROJECT_NAME} BuildDependencies)

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

target_include_directories(${PROJECT_NAME} PRIVATE
    "${LIBS_ROOT}/include"
    "${LIBS_ROOT}/include/freetype2"
    "${LIBS_ROOT}/include/libpng16"
)

########################################################################
# Compile definitions for static libraries
########################################################################

if(WIN32)
    target_compile_definitions(${PROJECT_NAME} PRIVATE
        LZMA_API_STATIC     # xz/lzma static linking
        AL_LIBTYPE_STATIC   # OpenAL static linking
        ZMQ_STATIC          # ZeroMQ static linking
        TAGLIB_STATIC       # TagLib static linking
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
    else()
        set(FREETYPE_LIB "freetype")
        set(PNG_LIB "libpng16_static")
        set(JPEG_LIB "jpeg-static")
        set(TURBOJPEG_LIB "turbojpeg-static")
        set(ZLIB_LIB "zlibstatic")
        set(ZSTD_LIB "zstd_static")
    endif()
    set(WEBP_LIB "libwebp")
    set(SHARPYUV_LIB "libsharpyuv")
    set(OPENAL_LIB "OpenAL32")
    if(CMAKE_BUILD_TYPE STREQUAL "Debug")
        set(ZMQ_LIB "libzmq-v143-mt-sgd-4_3_6")
    else()
        set(ZMQ_LIB "libzmq-v143-mt-s-4_3_6")
    endif()
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
    set(WEBP_LIB "webp")
    set(SHARPYUV_LIB "sharpyuv")
    set(OPENAL_LIB "openal")
    set(ZLIB_LIB "z")
    set(ZSTD_LIB "zstd")
    set(ZMQ_LIB "zmq")
endif()

# Use library names only - CMake won't validate existence at configure time
target_link_libraries(${PROJECT_NAME} PRIVATE
    # Fonts (freetype depends on harfbuzz, png, brotli, bzip2, zlib)
    ${FREETYPE_LIB} harfbuzz
    # Images (png depends on zlib)
    ${PNG_LIB} ${JPEG_LIB} ${TURBOJPEG_LIB} ${WEBP_LIB} ${SHARPYUV_LIB}
    # Archive (zip depends on zlib, bzip2, lzma, zstd)
    zip
    # Audio
    ${OPENAL_LIB} samplerate tag
    # Compression (dependencies of above)
    brotlienc brotlidec brotlicommon ${ZSTD_LIB} lzma bz2_static ${ZLIB_LIB}
    # System
    cpu_features hwloc
    # Crypto
    cryptopp
    # Geometry
    Clipper2
    # Networking
    ${ZMQ_LIB}
)

########################################################################
# Platform-specific system libraries
########################################################################

if(APPLE)
    find_library(FRAMEWORK_COREFOUNDATION CoreFoundation REQUIRED)
    find_library(FRAMEWORK_COREAUDIO CoreAudio REQUIRED)
    find_library(FRAMEWORK_AUDIOTOOLBOX AudioToolbox REQUIRED)
    find_library(FRAMEWORK_AUDIOUNIT AudioUnit REQUIRED)
    find_library(FRAMEWORK_IOKIT IOKit REQUIRED)

    target_link_libraries(${PROJECT_NAME} PRIVATE
        ${FRAMEWORK_COREFOUNDATION}
        ${FRAMEWORK_COREAUDIO}
        ${FRAMEWORK_AUDIOTOOLBOX}
        ${FRAMEWORK_AUDIOUNIT}
        ${FRAMEWORK_IOKIT}
    )

elseif(WIN32)
    target_link_libraries(${PROJECT_NAME} PRIVATE
        # Networking
        ws2_32
        iphlpapi
        # Audio
        winmm
        # COM/OLE
        ole32
        shell32
        # Harfbuzz dependencies (Uniscribe, DirectWrite, GDI)
        usp10       # Uniscribe
        dwrite      # DirectWrite
        rpcrt4      # UuidCreate
        gdi32       # GDI
    )

else()
    find_package(Threads REQUIRED)

    target_link_libraries(${PROJECT_NAME} PRIVATE
        Threads::Threads
        ${CMAKE_DL_LIBS}
        m
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
