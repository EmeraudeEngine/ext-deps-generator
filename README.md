# Introduction

This repository aims to create a cross-platform archive of static libraries to use with a project easily.
This must be run on a clean machine to create the archive for a specific platform.
Currently, Linux (x86_64), macOS (arm64, x86_64) and Windows (x86_64) are handled.


# Updating dependencies

If you update a dependency that requires other dependencies like freetype, update them as well.

When a dependency is updated, do not forget to report in 'Available libraries' the changes (branch, commit, version, ...).


# Available libraries

## brotli 
[master, ed738e842d2fbdf2d6459e39267a633c4a9b2f5d]

- URL : https://github.com/google/brotli.git
- Version : 1.1.0
- Dependencies : None
- Usage : Lossless compression library (Huffman LZ77). Requested by Freetype.

## bzip2 
[master, 1ea1ac188ad4b9cb662e3f8314673c63df95a589]

- URL : https://github.com/libarchive/bzip2.git
- Version : 1.1.0
- Dependencies : None
- Usage : Compression library.

## clipper2 
[main, 6901921c4be75126d1de60bfd24bd86a61319fd0]

- URL : https://github.com/AngusJohnson/clipper2
- Version : 1.5.2
- Dependencies : None
- Usage : A polygon clipping and offsetting library.

## cpu_features 
[main, 27a978c3070c88914e057b56cb2f9c8575d2fae2]

- URL : https://github.com/google/cpu_features.git
- Version : 0.9.0
- Dependencies : None
- Usage : Fetch CPU extensions and capabilities.

## cryptopp-cmake 
[master, 00a151f8489daaa32434ab1f340e6750793ddf0c]

- URL : https://github.com/abdes/cryptopp-cmake
- Version : 0.8.9~
- Dependencies : None
- Usage : Common cryptographic library for C++.

## freetype 
[master, 42608f77f20749dd6ddc9e0536788eaad70ea4b5]

- URL : https://gitlab.freedesktop.org/freetype/freetype.git
- Version : 2.13.3
- Dependencies : brotli, bzip2, harbuzz, png, zlib
- Usage : Fonts files (.ttf, .tti, ...) library.

## harfbuzz 
[main, 3ef8709829a5884517ad91a97b32b9435b2f20d1]

- URL : https://github.com/harfbuzz/harfbuzz.git
- Version : 10.4.0
- Dependencies : None
- Usage : Vector font library. Requested by Freetype

## hwloc 
[v2.12, 023d11309beca9c68c7433e8d634f1999e25370c]

- URL : https://github.com/open-mpi/hwloc
- Version : 2.12~
- Dependencies : None
- Usage : Fetch system capabilities.
- Notes : Linux and macOS versions are using autotools instead of cmake.

## lib3mf 
[3dJan/LinuxConfigAndBuildFixes, d65f4195fbc8ea5fc9f1ede5b00e30165ee56a2d]

- URL : https://github.com/3MFConsortium/lib3mf.git
- Version : 2.4.1
- Dependencies : zlib, libzip
- Usage : 3D model format library.
- Notes : This library fails to compile as static.

## libjpeg-turbo 
[main, adbb328159b5558e846690c49f9458deccbb0f43]

- URL : https://github.com/libjpeg-turbo/libjpeg-turbo.git
- Version : 3.1.0~
- Dependencies : None
- Usage : Image format library.

## libpng 
[libpng16, 872555f4ba910252783af1507f9e7fe1653be252]

- URL : https://github.com/glennrp/libpng.git
- Version : 1.6.47
- Dependencies : zlib
- Usage : Image format library.

## libsamplerate 
[master, 15c392d47e71b9395a759544b3818a1235fe1a1d]

- URL : https://github.com/libsndfile/libsamplerate.git
- Version : 0.2.2~
- Dependencies : None
- Usage : Audio resampler library.

## libwebp 
[1.5.0, a4d7a715337ded4451fec90ff8ce79728e04126c]

- URL : https://github.com/webmproject/libwebp.git
- Version : 1.5.0
- Dependencies : None
- Usage : Image format library.

## libzip 
[main, f30f5290de485348442d168cd7b2eb714d1f20f9]

- URL : https://github.com/nih-at/libzip.git
- Version : 1.11.13
- Dependencies : zlib bzip2 xz zstd
- Usage : Compressed archive management library.
- Notes : On Windows, you need to add "PATHS LIBS_ROOT" inside find_package() functions in the CMakeLists.txt before compiling.
- Warning : On Windows, zstd support has been disabled.


## libzmq (ZeroMQ) 
[master, aaf88cdfd8286a81e569ac9d3e106df22a77a412]

- URL : https://github.com/zeromq/libzmq.git
- Version : 4.3.6
- Dependencies : None
- Usage : Common IPC library.

## cppzmq 
[master, 21c83ca0c3d8c11d81aa13aca2a565607a25920b]

- URL : https://github.com/zeromq/cppzmq.git
- Version : 4.10~
- Dependencies : libzmq
- Usage : C++ wrapper for libzmq.
- Notes : There is no compilation here, this is just some headers for libzmq.

## openal-soft 
[master, dc7d7054a5b4f3bec1dc23a42fd616a0847af948]

- URL : https://github.com/kcat/openal-soft.git
- Version : 1.24.3
- Dependencies : None
- Usage : Audio API.

## taglib 
[master, e3de03501ff66221d1f1f971022b248d5b38ba06]

- URL : https://github.com/taglib/taglib.git
- Version : 2.0.2
- Dependencies : zlib
- Usage : Audio meta-data library.

## xz (LZMA) 
[v5.6, ac50df0d89ce73f30430b8174e578071cbb4e056]

- URL : https://github.com/tukaani-project/xz.git
- Version : 5.6.4
- Dependencies : None
- Usage : Compression library.

## zlib 
[master, 51b7f2abdade71cd9bb0e7a373ef2610ec6f9daf]

- URL : https://github.com/madler/zlib.git
- Version : 1.3.1
- Dependencies : None
- Usage : Compression library.
- Notes : This version build the static and the shared libraries, beware when linking. An upcoming release will fix this with cmake options.

## zstd (Zstandard)
[release, f8745da6ff1ad1e7bab384bd1f9d742439278e99]

- URL : https://github.com/facebook/zstd.git
- Version : 1.5.7
- Dependencies : None
- Usage : Compression library.
- Notes : This version build the static and the shared libraries, beware when linking.
- Warning : On Windows, this lib is disabled.
- 
# Upcoming libraries

- libsvg (https://github.com/ravhed/libsvg.git)
- OCCT (Open Cascade) (https://github.com/Open-Cascade-SAS/OCCT.git)


# Requirements and build process

There is three main scripts at the repository to fire all compilations.
"builds" directory will contain the compilation files.
"output" directory will contain the final library files to ship.

All platforms needs at least CMake 3.25.1, Python 3+, ninja build and autotools.

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

Compilations needs a proper XCode installed for macOS SDK 12.0

To install brew (https://brew.sh/)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

To install autotools
```bash
brew install samurai autoconf automake libtool
```

For macOS based on 'Apple Silicon CPU' :
```bash
./build.mac.sh 12.0 arm64 Release
./build.mac.sh 12.0 arm64 Debug

```

For macOS based on 'Intel CPU' :
```bash
./build.mac.sh 12.0 x86_64 Release
./build.mac.sh 12.0 x86_64 Debug

```

NOTE: The minimum SDK is set to 12.0 here, but can be changed.

## Windows

Compilations needs a Visual Studio 2022 and NASM from :
https://www.nasm.us/pub/nasm/releasebuilds/?C=M;O=D

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
./build.windows.ps1 x86_64 Release
./build.windows.ps1 x86_64 Debug

```
