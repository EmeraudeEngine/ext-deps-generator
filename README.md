# Introduction

This repository aims to create a cross-platform archive of static libraries to use with a project easily.
This must be run on a clean machine to create the archive for a specific platform.
Currently, Linux (x86_64), macOS (arm64, x86_64) and Windows (x86_64) are handled.


# Updating dependencies

If you update a dependency that requires other dependencies like freetype, update them as well.

When a dependency is updated, remember to report in 'Available libraries' the changes (branch, commit, version, ...).


# Available libraries

## brotli 
[master, ed738e842d2fbdf2d6459e39267a633c4a9b2f5d]

- URL: https://github.com/google/brotli.git
- Version: 1.1.0
- Dependencies: None
- Usage: Lossless compression library (Huffman LZ77). Requested by Freetype.

## bzip2 
[master, 1ea1ac188ad4b9cb662e3f8314673c63df95a589]

- URL: https://github.com/libarchive/bzip2.git
- Version: 1.1.0
- Dependencies: None
- Usage: Compression library.

## clipper2 
[main, ef88ee97c0e759792e43a2b2d8072def6c9244e8]

- URL: https://github.com/AngusJohnson/clipper2
- Version: 1.5.4
- Dependencies: None
- Usage: A polygon clipping and offsetting library.

## cpu_features 
[main, d3b2440fcfc25fe8e6d0d4a85f06d68e98312f5b]

- URL: https://github.com/google/cpu_features.git
- Version: 0.10.1
- Dependencies: None
- Usage: Fetch CPU extensions and capabilities.

## cryptopp-cmake 
[master, 866aceb8b13b6427a3c4541288ff412ad54f11ea]

- URL: https://github.com/abdes/cryptopp-cmake
- Version: 0.8.9~
- Dependencies: None
- Usage: Common cryptographic library for C++.

## freetype 
[master, 42608f77f20749dd6ddc9e0536788eaad70ea4b5]

- URL: https://gitlab.freedesktop.org/freetype/freetype.git
- Version: 2.13.3
- Dependencies: brotli, bzip2, harbuzz, png, zlib
- Usage: Fonts files (.ttf, .tti, ...) library.

## harfbuzz 
[main, bf8929fbfb623703cf1522b372cab80002c17c95]

- URL: https://github.com/harfbuzz/harfbuzz.git
- Version: 11.5.0
- Dependencies: None
- Usage: Vector font library. Requested by Freetype

## hwloc 
[v2.12, befdbc5c39419fb18c07f9782c261f202e023afd]

- URL: https://github.com/open-mpi/hwloc
- Version: 2.12
- Dependencies: None
- Usage: Fetch system capabilities.
- Notes: Linux and macOS versions are using autotools instead of cmake.

## lib3mf 
[3dJan/LinuxConfigAndBuildFixes, 4969189d2039600897fc7a162b0712414a445fe2]

- URL: https://github.com/3MFConsortium/lib3mf.git
- Version: 2.4.1
- Dependencies: zlib, libzip
- Usage: 3D model format library.
- Notes: This library fails to compile as static.

## libjpeg-turbo 
[main, 4e151a4ad91001b3aa8c2ece2205c15f487ce320]

- URL: https://github.com/libjpeg-turbo/libjpeg-turbo.git
- Version: 3.1.2
- Dependencies: NASM compiler (optional, but slower lib)
- Usage: Image format library.

## libpng 
[libpng16, 2b978915d82377df13fcbb1fb56660195ded868a]

- URL: https://github.com/glennrp/libpng.git
- Version: 1.6.50
- Dependencies: zlib
- Usage: Image format library.

## libsamplerate 
[master, 2ccde9568cca73c7b32c97fefca2e418c16ae5e3]

- URL: https://github.com/libsndfile/libsamplerate.git
- Version: 0.2.2~
- Dependencies: FFTW3 library (optional, but slower lib)
- Usage: Audio resampler library.

## libwebp 
[1.6.0, 991170bbab3e6afc74666d124f3f1dc7be942cd0]

- URL: https://github.com/webmproject/libwebp.git
- Version: 1.6.0
- Dependencies: None
- Usage: Image format library.

## libzip 
[main, 6f8a0cdd24a0dc6cce9dac4a7679da784ab124ea]

- URL: https://github.com/nih-at/libzip.git
- Version: 1.11.14
- Dependencies: zlib bzip2 xz zstd
- Usage: Compressed archive management library.
- Notes: On Windows, you need to add "PATHS LIBS_ROOT" inside find_package() functions in the CMakeLists.txt before compiling.
- Warning: On Windows, zstd support has been disabled.

## libzmq (ZeroMQ) 
[master, 7a7bfa10e6b0e99210ed9397369b59f9e69cef8e]

- URL: https://github.com/zeromq/libzmq.git
- Version: 4.3.6~
- Dependencies: None
- Usage: Common IPC library.

## cppzmq 
[master, 3bcbd9dad2f57180aacd4b4aea292a74f0de7ef4]

- URL: https://github.com/zeromq/cppzmq.git
- Version: 4.11.0
- Dependencies: libzmq
- Usage: C++ wrapper for libzmq.
- Notes: There is no compilation here, this is just some headers for libzmq.

## openal-soft 
[master, dc7d7054a5b4f3bec1dc23a42fd616a0847af948]

- URL: https://github.com/kcat/openal-soft.git
- Version: 1.24.3
- Dependencies: None
- Usage: Audio API.

## taglib 
[master, 7d86716194777e0294453bfdc9dd170bd033e1f4]

- URL: https://github.com/taglib/taglib.git
- Version: 2.1.1
- Dependencies: zlib
- Usage: Audio meta-data library.

## xz (LZMA) 
[v5.8, 7c12726c51b2b7d77329dd72a29ecb1ec262b918]

- URL: https://github.com/tukaani-project/xz.git
- Version: 5.8.1
- Dependencies: None
- Usage: Compression library.

## zlib 
[master, 51b7f2abdade71cd9bb0e7a373ef2610ec6f9daf]

- URL: https://github.com/madler/zlib.git
- Version: 1.3.1
- Dependencies: None
- Usage: Compression library.
- Notes: This version builds the static and the shared libraries, beware when linking. An upcoming release will fix this with cmake options.

## pthread-win32
[master, 3309f4d6e7538f349ae450347b02132ecb0606a7]

- URL: https://github.com/GerHobbelt/pthread-win32.git
- Version: 3.0.3.1
- Dependencies: None
- Usage: Thread library.
- Notes: Only for Windows.

## zstd (Zstandard)
[release, f8745da6ff1ad1e7bab384bd1f9d742439278e99]

- URL: https://github.com/facebook/zstd.git
- Version: 1.5.7
- Dependencies: pthread-win32 on Windows
- Usage: Compression library.
- Notes: This version builds the static and the shared libraries, beware when linking.

# Upcoming libraries

- libsvg (https://github.com/ravhed/libsvg.git)
- OCCT (Open Cascade) (https://github.com/Open-Cascade-SAS/OCCT.git)


# Requirements and build process

There are three main scripts at the repository to fire all compilations.
The "builds" directory will contain the compilation files.
The "output" directory will contain the final library files to ship.

All platforms need at least CMake 3.25.1, Python 3+, ninja build and autotools.

## Linux

Compilations needs GCC 12+.

To install autotools
```bash
sudo apt install autoconf automake libtool
```

```bash
./build.linux.sh x86_64 Release
./build.linux.sh x86_64 Debug

```

## macOS

Compilations need a proper XCode installed for macOS SDK 12.0

To install brew (https://brew.sh/)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

To install autotools
```bash
brew install samurai autoconf automake libtool
```

For macOS based on 'Apple Silicon CPU':
```bash
./build.mac.sh 12.0 arm64 Release
./build.mac.sh 12.0 arm64 Debug

```

For macOS based on 'Intel CPU':
```bash
./build.mac.sh 12.0 x86_64 Release
./build.mac.sh 12.0 x86_64 Debug

```

NOTE: The minimum SDK is set to 12.0 here but can be changed.

## Windows

Compilations need a Visual Studio 2022 and NASM from:
https://www.nasm.us/pub/nasm/releasebuilds/?C=M;O=D

NOTE: Libraries for Windows are separated between the static "MultiThreaded, MultiThreadedDebug" (\MT, \MTd) and 
the dynamic "MultiThreadedDLL, MultiThreadedDebugDLL" (\MD, \MDd) runtime. (And yes! That was painful...)

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
./build.windows.ps1 x86_64 Release MD
./build.windows.ps1 x86_64 Debug MD
./build.windows.ps1 x86_64 Release MT
./build.windows.ps1 x86_64 Debug MT

```

To check .lib files: Open "Developer Command Prompt" and go to a "lib/" directory and type:

```bash
powershell
Get-ChildItem -Recurse -Filter *.lib | ForEach-Object { $file = $_; dumpbin /directives $file.FullName 2>&1 | Select-String 'LIBCMTD?|MSVCRTD?' | ForEach-Object { $_.Matches.Value } | ForEach-Object { [PSCustomObject]@{ CRT = $_; Fichier = $file.Name } } } | Group-Object -Property CRT

```

All "MT" must only print "LIBCMT"
All "MTd must only print "LIBCMTD"
All "MD" must only print "MSVCRT"
All "MDd" must only print "MSVCRTD"
