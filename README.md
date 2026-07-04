# Introduction

This repository aims to create a cross-platform archive of static libraries to use with a project easily.
This must be run on a clean machine to create the archive for a specific platform.
Currently, Linux (x86_64), macOS (arm64, x86_64) and Windows (x86_64) are handled.


# Updating dependencies

If you update a dependency that requires other dependencies like freetype, update them as well.

When a dependency is updated, remember to report in 'Available libraries' the changes (branch, commit, version, ...).

## Updating LibreSSL (vendored)

LibreSSL is the **one exception** to the "every dependency is a git submodule" rule: its
sources are a committed release tarball under `repositories/libressl/` (see the "Vendored
Sources" section in `AGENTS.md` for why). `check_releases.py` cannot see it, so releases must
be checked manually. To move to a new version:

```sh
# 1. Check for a newer stable at https://www.libressl.org/releases.html
#    (x.y.2 is the first STABLE of a branch; x.y.0/x.y.1 are dev snapshots).

# 2. Download the tarball and the mirror's signed checksum list, then VERIFY.
VER=4.3.2   # <-- set the target version
cd /tmp
curl -sSLO "https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/libressl-${VER}.tar.gz"
curl -sSLO "https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/SHA256"
grep "libressl-${VER}.tar.gz" SHA256
sha256sum "libressl-${VER}.tar.gz"     # <-- the two hashes MUST match

# 3. Replace the vendored sources (from the ext-deps-generator repo root).
rm -rf repositories/libressl
mkdir  repositories/libressl
tar -xzf "/tmp/libressl-${VER}.tar.gz" -C repositories/libressl --strip-components=1

# 4. Update the version + SHA256 in libraries/libressl.yaml AND the "## libressl"
#    entry in this README, then rebuild + run the link-test to confirm.
```


# Available libraries

## brotli 
[v1.2.0, 028fb5a23661f123017c060daa546b55cf4bde29]

- URL: https://github.com/google/brotli.git
- Version: 1.2.0
- Dependencies: None
- Usage: Lossless compression library (Huffman LZ77). Requested by Freetype.

## bc7enc_rdo
[master, dbe416d28a5530b4e8cc45b14bf034dc6b96bbde]

- URL: https://github.com/richgel999/bc7enc_rdo.git
- Version: master (no upstream releases)
- Dependencies: None
- Usage: BC7 texture block encoder/decoder. Required by engines doing GPU-side compressed texture upload.
- Notes: Upstream targets a standalone `bc7enc` executable with RDO tooling. The patch replaces the CMakeLists with a minimal static-library build exposing only the core encoder/decoder (`bc7enc.cpp` + `bc7decomp.cpp`); the RDO optimizer and lodepng/utils helpers are not needed downstream and are excluded.

## bzip2 
[master, 1ea1ac188ad4b9cb662e3f8314673c63df95a589]

- URL: https://github.com/libarchive/bzip2.git
- Version: 1.1.0
- Dependencies: None
- Usage: Compression library.

## clipper2 
[Clipper2_2.0.1, 21ebba05db8894f0c7217ad35ea518080f324946]

- URL: https://github.com/AngusJohnson/clipper2
- Version: 2.0.1
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

## fastgltf
[v0.9.x, 0d1b67a28c4950ea2deb796702006dcbe31e02b3]

- URL: https://github.com/spnda/fastgltf.git
- Version: 0.9.0
- Dependencies: None
- Usage: GLTF 2.0 file parser.

## flac
[1.5.0, 1507800de4b70e21be71f38caa0d9079d0bc6e45]

- URL: https://github.com/xiph/flac.git
- Version: 1.5.0
- Dependencies: libogg
- Usage: Free Lossless Audio Codec. Required by libsndfile.

## freetype 
[VER-2-14-3, 0a0221a1347e2f1e07c395263540026e9a0aa7c7]

- URL: https://gitlab.freedesktop.org/freetype/freetype.git
- Version: 2.14.3
- Dependencies: brotli, bzip2, harbuzz, png, zlib
- Usage: Fonts files (.ttf, .tti, ...) library.

## glslang
[16.3.0, 275822a6261ee689aadb1da5f09a0ec2f058685c]

- URL: https://github.com/KhronosGroup/glslang.git
- Version: 16.3.0
- Dependencies: spirv-tools (which itself depends on spirv-headers)
- Usage: GLSL/HLSL front-end and SPIR-V code generator. Required to compile GLSL shaders to SPIR-V at runtime in Vulkan engines.
- Notes: Built with `ALLOW_EXTERNAL_SPIRV_TOOLS=ON` and `BUILD_EXTERNAL=OFF` so the SPIR-V optimizer is consumed from the standalone spirv-tools package via `find_package` instead of glslang's bundled `update_glslang_sources.py` fetch. Commits of spirv-tools and spirv-headers are aligned with glslang's `known_good.json` to stay ABI-compatible.

## harfbuzz 
[14.2.0, b0ffab42d473eb380ad0fcf42730e0f1868cbc97]

- URL: https://github.com/harfbuzz/harfbuzz.git
- Version: 14.2.0
- Dependencies: None
- Usage: Vector font library. Requested by Freetype

## hwloc 
[v2.13, f3dc66ab3d6a523170e0c6703b0d6550a2fc830d]

- URL: https://github.com/open-mpi/hwloc
- Version: 2.13
- Dependencies: None
- Usage: Fetch system capabilities.
- Notes: Linux and macOS versions are using autotools instead of cmake.

## jsoncpp
[master, d4d072177213b117fb81d4cfda140de090616161]

- URL: https://github.com/open-source-parsers/jsoncpp.git
- Version: 1.9.7~
- Dependencies: None
- Usage: JSON parser.

## lame
[master, 1f5cc9487284d5950343aa5d4f70de433468070a]

- URL: https://github.com/lameproject/lame.git
- Version: 3.100
- Dependencies: None
- Usage: MP3 encoder. Required by libsndfile for MP3 write support.
- Notes: No official git upstream (lame is on SourceForge in SVN). This mirror has no release tags, so we pin to a master SHA. libsndfile needs LAME 3.100+ (uses `lame_encode_buffer_interleaved_int`). Disabled on Windows: only old VS 2008 project files are provided.

## lib3mf 
[release/2.5.0, bbbbffb79e197903b874470e5f83609b1d6272ae]

- URL: https://github.com/3MFConsortium/lib3mf.git
- Version: 2.5.0
- Dependencies: zlib, libzip
- Usage: 3D model format library.
- Notes: This library fails to compile as static.

## libjpeg-turbo 
[3.1.4.1, 9217719d3a58633923b096af4c1d50d304768a64]

- URL: https://github.com/libjpeg-turbo/libjpeg-turbo.git
- Version: 3.1.4.1
- Dependencies: NASM compiler (optional, but slower lib)
- Usage: Image format library.

## libogg
[v1.3.6, be05b13e98b048f0b5a0f5fa8ce514d56db5f822]

- URL: https://github.com/xiph/ogg.git
- Version: 1.3.6
- Dependencies: None
- Usage: Ogg container format. Required by libvorbis, flac, and libsndfile.

## libpng 
[v1.6.58, 3061454d980de7d53608f594194cfac722721d2a]

- URL: https://github.com/glennrp/libpng.git
- Version: 1.6.58
- Dependencies: zlib
- Usage: Image format library.

## libressl
[VENDORED — release tarball, NOT a git submodule]

- Source: https://ftp.openbsd.org/pub/OpenBSD/LibreSSL/libressl-4.3.2.tar.gz
- Version: 4.3.2 (first stable of the 4.3 branch; LibreSSL convention: x.y.0/x.y.1 are
  development snapshots, x.y.2 is the first stable of a branch)
- SHA256: edf01aee24c65d69e6a9efcb9d44bcda682ff9d4f3bbbd95e794e1dfa90847b5
- Dependencies: None
- Usage: TLS/crypto provider (libtls + libssl + libcrypto). Consumed by emeraude-base's
  HTTPS client through `asio::ssl` (OpenSSL-compatible API). Chosen over OpenSSL because
  LibreSSL-portable builds with CMake, whereas OpenSSL's perl `Configure` would require a
  bespoke builder plus perl/nasm build deps in this CMake-centric generator.
- **Notes — THE ONE VENDORED DEPENDENCY.** Unlike every other library here, LibreSSL is
  NOT a git submodule: its full release sources are committed under `repositories/libressl/`.
  The `libressl/portable` git repo is not self-contained (crypto/ssl/tls hold only build
  files; the real sources are pulled from OpenBSD by `update.sh` at build time), so the
  reproducible form is the release tarball. See "Updating LibreSSL (vendored)" above and the
  "Vendored Sources" section in `AGENTS.md`. `check_releases.py` does NOT track it (it only
  sees `.gitmodules`) — check for new releases manually at https://www.libressl.org/releases.html

## libsamplerate 
[master, 2ccde9568cca73c7b32c97fefca2e418c16ae5e3]

- URL: https://github.com/libsndfile/libsamplerate.git
- Version: 0.2.2~
- Dependencies: FFTW3 library (optional, but slower lib)
- Usage: Audio resampler library.

## libsndfile
[1.2.2, 72f6af15e8f85157bd622ed45b979025828b7001]

- URL: https://github.com/libsndfile/libsndfile.git
- Version: 1.2.2
- Dependencies: libogg, libvorbis, flac, opus, mpg123, lame (lame disabled on Windows)
- Usage: Audio file I/O library (WAV, FLAC, Ogg/Vorbis, Opus, MP3, etc.).
- Notes: MP3 write support requires lame, so it is disabled on Windows.

## libvorbis
[v1.3.7, 0657aee69dec8508a0011f47f3b69d7538e9d262]

- URL: https://github.com/xiph/vorbis.git
- Version: 1.3.7
- Dependencies: libogg
- Usage: Vorbis audio codec. Required by libsndfile.

## libvpx
[v1.16.0, 1024874c5919305883187e2953de8fcb4c3d7fa6]

- URL: https://github.com/webmproject/libvpx.git
- Version: 1.16.0
- Dependencies: None
- Usage: VP8/VP9 video codec library.
- Notes: Linux and macOS only (configure script requires Cygwin/MSYS2 on Windows).

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
[master, b946c18f676760387276cd095bbdd8c0e18c09bf]

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

## lunasvg
[master, 09c2bd26efa29583236c82c1cab7e7977a26eb1f]

- URL: https://github.com/sammycage/lunasvg
- Version: 3.5.0~
- Dependencies: None
- Usage: Image format library.

## mpg123
[master, b18fd7c648aad2420cd49bbb948c91d53b4164b3]

- URL: https://github.com/madebr/mpg123.git
- Version: 1.33.6-dev
- Dependencies: None
- Usage: MP3 decoder. Required by libsndfile for MP3 read support.
- Notes: Upstream is SourceForge SVN, this is a community git mirror with no release tags, so we pin to a master SHA. Built via the CMake port in `ports/cmake/`.

## opus
[v1.6.1, 22244de5a79bd1d6d623c32e72bf1954b56235be]

- URL: https://github.com/xiph/opus.git
- Version: 1.6.1
- Dependencies: None
- Usage: Opus audio codec. Required by libsndfile.

## openal-soft 
[master, b2c48f7718ef3fcf67921a8b6534c4914e328970]

- URL: https://github.com/kcat/openal-soft.git
- Version: 1.25.2
- Notes: This version is stable on all platforms. Beware when updating.
- Dependencies: None
- Usage: Audio API.

## reproc
[v14.2.7, 06034a7fca1ec46eddb4997f7764db89380c5216]

- URL: https://github.com/DaanDeMeyer/reproc.git
- Version: 14.2.7
- Dependencies: None
- Usage: Cross-platform process control library (C `reproc` + C++ `reproc++`). Both static libraries are built and installed.

## spirv-headers
[vulkan-sdk-1.4.350.0~, 1a22b167081842915a1c78a0b5b5a353a23284aa]

- URL: https://github.com/KhronosGroup/SPIRV-Headers.git
- Version: 1.5.5
- Dependencies: None
- Usage: SPIR-V header files (enums, opcodes). Consumed by spirv-tools.
- Notes: Commit pinned to glslang 16.3.0's `known_good.json` to keep the SPIR-V toolchain coherent.

## spirv-tools
[v2026.2.rc2~, 2ec8457ab33d539b6f1fecc998360c0b8b05ed4f]

- URL: https://github.com/KhronosGroup/SPIRV-Tools.git
- Version: 2026.2.rc2
- Dependencies: spirv-headers
- Usage: SPIR-V parsing, validation, optimization and linking. Consumed by glslang's SPIR-V optimizer (`SPIRV-Tools-opt`).
- Notes: Built with `SPIRV_TOOLS_BUILD_STATIC=ON` and `SPIRV-Headers_SOURCE_DIR=${INSTALL_PREFIX}` so the headers from the previously installed `spirv-headers` package are reused (no `add_subdirectory` of headers). Commit pinned to glslang 16.3.0's `known_good.json`.

## taglib 
[v2.3, 1b94b93762636ebe5733180c3e825be4621e4c7f]

- URL: https://github.com/taglib/taglib.git
- Version: 2.3
- Dependencies: zlib
- Usage: Audio meta-data library.

## ufbx
[main, 5c3494fb9a0f1b2e9fb5fb90ddf83ea6b676ebbb]

- URL: https://github.com/ufbx/ufbx.git
- Version: 0.21.5
- Dependencies: None (links libm on Unix)
- Usage: Single-translation-unit FBX 7.x parser. Used for skeletal mesh/animation import.
- Notes: Upstream is header + single `.c`, no CMakeLists.txt. The patch adds a minimal one that builds a static library and installs `ufbx.h` under `include/ufbx/`.

## xz (LZMA) 
[v5.8, 4b73f2ec19a99ef465282fbce633e8deb33691b3]

- URL: https://github.com/tukaani-project/xz.git
- Version: 5.8.3
- Dependencies: None
- Usage: Compression library.

## zlib 
[v1.3.2, da607da739fa6047df13e66a2af6b8bec7c2a498]

- URL: https://github.com/madler/zlib.git
- Version: 1.3.2
- Dependencies: None
- Usage: Compression library.
- Notes: This version builds the static and the shared libraries, beware when linking. An upcoming release will fix this with cmake options.

## pthread-win32
[master, 334dd243487013a7faa3a9b96afa5264fcfb09ba]

- URL: https://github.com/GerHobbelt/pthread-win32.git
- Version: 4.1.0.9
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

- OCCT (Open Cascade) (https://github.com/Open-Cascade-SAS/OCCT.git)


# Requirements and build process

The repository uses a unified Python build system (`build.py`) that works on all platforms.
The `builds/` directory will contain the compilation files.
The `output/` directory will contain the final library files to ship.

## Prerequisites

Every platform needs the same core toolchain: **Python 3.10+**, **CMake 3.25.1+**,
**Ninja**, **Meson**, **Autotools** (autoconf, automake, libtool), and **NASM**
(for libjpeg-turbo / libvpx assembly optimizations). What differs is the
compiler and how you install everything.

### Linux (Debian/Ubuntu)

GCC 12+ is required. For other distributions, install the equivalent packages.

```bash
sudo apt install build-essential python3 python3-pip python3-venv cmake meson ninja-build autoconf automake libtool nasm
```

A few libraries probe for system development headers and silently disable
optional features if they are missing. The most consequential case is
**openal-soft**: with no audio backend `-dev` packages installed, CMake drops
ALSA / PulseAudio / PipeWire / JACK detection and produces a `libopenal.a`
that links but cannot open any device at runtime. The build now refuses to
finish in that state (see [Post-build assertions](#post-build-assertions)),
so install the audio dev headers before running `build.py`:

```bash
sudo apt install libasound2-dev libpulse-dev libpipewire-0.3-dev libjack-jackd2-dev
```

### macOS

Xcode Command Line Tools with macOS SDK 12.0+ is required.

```bash
# Install Homebrew if not already installed (see https://brew.sh)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install python3 cmake meson ninja autoconf automake libtool nasm
```

### Windows

Install each tool separately (no single package manager):

- **Visual Studio 2022** with the MSVC v143 toolchain
- **Python 3.10+** — https://www.python.org/downloads/ (check *Add Python to PATH*)
- **CMake 3.25.1+** — https://cmake.org/download/
- **Ninja** and **Meson** — via `pip install ninja meson` (after Python is installed)
- **NASM** — https://www.nasm.us/pub/nasm/releasebuilds/?C=M;O=D
- **MSYS2** (required to build libvpx) — https://www.msys2.org/
  - After install, run `pacman -S make diffutils` inside MSYS2
  - Set the `MSYS2_PATH` env var if MSYS2 is not at `C:\msys64`

Autotools is not needed on Windows: the libraries that use it (hwloc, libvpx)
fall back to alternate build paths there.

## Python virtual environment

Same steps on every platform — only the activation command changes:

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Build commands

### List available libraries

```bash
python build.py --list --macos-sdk 12.0   # macOS
python build.py --list                     # Linux/Windows
```

### Build all libraries

```bash
# Linux
python3 build.py --arch x86_64 --build-type Release
python3 build.py --arch x86_64 --build-type Debug

# macOS (Apple Silicon)
python3 build.py --macos-sdk 12.0 --arch arm64 --build-type Release
python3 build.py --macos-sdk 12.0 --arch arm64 --build-type Debug

# macOS (Intel)
python3 build.py --macos-sdk 12.0 --arch x86_64 --build-type Release
python3 build.py --macos-sdk 12.0 --arch x86_64 --build-type Debug

# Windows (DLL runtime)
python build.py --arch x86_64 --build-type Release --runtime-lib MD
python build.py --arch x86_64 --build-type Debug --runtime-lib MD

# Windows (Static runtime)
python build.py --arch x86_64 --build-type Release --runtime-lib MT
python build.py --arch x86_64 --build-type Debug --runtime-lib MT
```

### Build a single library (with dependencies)

```bash
python build.py --macos-sdk 12.0 --library freetype
```

### Build a single library (without dependencies)

```bash
python build.py --macos-sdk 12.0 --library freetype --no-deps
```

### Dry run (show what would be built)

```bash
python build.py --macos-sdk 12.0 --dry-run
```

## Command-line options

| Option | Description | Default |
|--------|-------------|---------|
| `--arch` | Target architecture (`x86_64`, `arm64`) | `x86_64` |
| `--build-type` | Build type (`Release`, `Debug`) | `Release` |
| `--macos-sdk` | macOS deployment target (required on macOS) | - |
| `--runtime-lib` | Windows runtime library (`MD`, `MT`) | `MD` |
| `--library` | Build only this library | - |
| `--no-deps` | Don't build dependencies | `false` |
| `--list` | List available libraries | - |
| `--dry-run` | Show build plan without building | - |

## Post-build assertions

Some libraries can produce an artifact that links cleanly but is broken at
runtime when an optional dependency was missing on the build host. The
canonical example is OpenAL-soft: `ALSOFT_REQUIRE_*=Off` lets CMake disable
ALSA / PulseAudio / PipeWire / JACK when their dev headers are absent, and
the resulting `libopenal.a` then fails `alcOpenDevice()` with
`ALC_INVALID_VALUE` on every modern Linux box.

To catch these silent dropouts at build time rather than at runtime, a
library YAML can declare assertions that run after the install step:

```yaml
platforms:
  linux:
    post_build_assertions:
      - kind: require_any_define
        file: config.h                   # relative to the build dir
        defines: [HAVE_ALSA, HAVE_PULSEAUDIO, HAVE_PIPEWIRE, HAVE_JACK]
        message: |
          Human-readable remediation, printed when the assertion fails.
```

Failing assertions abort the build with the message embedded in the YAML.
The check is opt-in — libraries without a `post_build_assertions` section
behave as before. Currently wired into the CMake builder
(`builder/cmake_builder.py`); see `builder/config.py::Library.verify_post_build`
for the implementation. Extending to other builders is a 5-line copy if a
non-CMake library ever needs the same guard.

## Windows runtime library notes

Libraries for Windows are separated between:
- **MD/MDd**: Dynamic runtime (`MultiThreadedDLL`, `MultiThreadedDebugDLL`)
- **MT/MTd**: Static runtime (`MultiThreaded`, `MultiThreadedDebug`)

To verify `.lib` files, open "Developer Command Prompt" and run:

```powershell
Get-ChildItem -Recurse -Filter *.lib | ForEach-Object { $file = $_; dumpbin /directives $file.FullName 2>&1 | Select-String 'LIBCMTD?|MSVCRTD?' | ForEach-Object { $_.Matches.Value } | ForEach-Object { [PSCustomObject]@{ CRT = $_; Fichier = $file.Name } } } | Group-Object -Property CRT
```

Expected results:
- **MT** builds: only `LIBCMT`
- **MTd** builds: only `LIBCMTD`
- **MD** builds: only `MSVCRT`
- **MDd** builds: only `MSVCRTD`

## Release assets creation

Quick recap and reminder to release assets on GitHub. Here is an example for separated uploads for the assets v011.

*Notes* : Use --cobbler to overwrite.

```
# Create the release
gh release create v011 --repo EmeraudeEngine/ext-deps-generator --title "External dependencies v011" --notes "Precompiled binaries for Emeraude-Engine"

# Linux Debian
gh release upload v011 --repo EmeraudeEngine/ext-deps-generator linux-Debian.x86_64-Release-011.zip
gh release upload v011 --repo EmeraudeEngine/ext-deps-generator linux-Debian.x86_64-Debug-011.zip

# Linux Mint
gh release upload v011 --repo EmeraudeEngine/ext-deps-generator linux-Linuxmint.x86_64-Release-011.zip
gh release upload v011 --repo EmeraudeEngine/ext-deps-generator linux-Linuxmint.x86_64-Debug-011.zip

# Linux Ubuntu
gh release upload v011 --repo EmeraudeEngine/ext-deps-generator linux-Ubuntu.x86_64-Release-011.zip
gh release upload v011 --repo EmeraudeEngine/ext-deps-generator linux-Ubuntu.x86_64-Debug-011.zip

# Apple macOS
gh release upload v011 --repo EmeraudeEngine/ext-deps-generator mac.arm64-Release-011.zip
gh release upload v011 --repo EmeraudeEngine/ext-deps-generator mac.arm64-Debug-011.zip
gh release upload v011 --repo EmeraudeEngine/ext-deps-generator mac.x86_64-Release-011.zip
gh release upload v011 --repo EmeraudeEngine/ext-deps-generator mac.x86_64-Debug-011.zip

# Microsoft Windows
gh release upload v010 --repo EmeraudeEngine/ext-deps-generator windows.x86_64-Release-MD-011.zip
gh release upload v010 --repo EmeraudeEngine/ext-deps-generator windows.x86_64-Debug-MD-011.zip
gh release upload v010 --repo EmeraudeEngine/ext-deps-generator windows.x86_64-Release-MT-011.zip
gh release upload v010 --repo EmeraudeEngine/ext-deps-generator windows.x86_64-Debug-MT-011.zip
```

## TODO list

## Archive hardening

### 1. SHA256 integrity check on archive download

**Why:** Currently `InstallExternalDependencies.cmake` (engine side) downloads the
archive via `file(DOWNLOAD)` with no integrity verification. Nothing protects
against transit corruption, GitHub Release tampering, or a hijacked CDN.

**What:**
- `build.py` (or release pipeline) emits a `SHA256SUMS.txt` next to each archive
  when uploading to GitHub Releases (one line per platform/runtime variant).
- Engine's `InstallExternalDependencies.cmake` is updated to pass
  `EXPECTED_HASH SHA256=<hash>` to `file(DOWNLOAD)`. The hash table can be
  inlined in the cmake script (one entry per `EXTERNAL_DEPENDENCIES_FILENAME`).
- Failure → hard FATAL_ERROR with the expected vs actual hash diff.

**Cost:** ~5 lines CMake on engine side, 1 line per archive on the release
script side. Trivial maintenance burden.

### 2. Smoke-test suite per dependency

**Why:** The lame/FLAC/mpg123/shlwapi cascade (May 2026) wasn't detected at
ext-deps-generator build time — only when the engine itself linked. Every
library install was "successful" but the produced binaries had missing
symbols (lame `init_xrpow_core_sse`) or missing transitive deps (mpg123 →
shlwapi). A minimal "can I link a hello-world against this lib" check would
have caught all four bugs.

**What:**
- Add a `smoke_tests/<libname>.c` per library: tiny program that calls 1-2
  public APIs (e.g. `FLAC__stream_decoder_new` + `delete`, `lame_init` +
  `lame_close`, `sf_open` + `sf_close`).
- After `cmake --install`, the builder compiles + links + runs the smoke test
  against the installed library, against the **same toolchain/runtime** as
  the build itself. Failure aborts the build.
- For Windows static libs, the smoke test runs through the same MT/MD config
  so the runtime mismatch is caught here too.

**Cost:** ~10-30 lines C per library (40 libs ≈ 600 LOC), plus harness in
`builder/`. Higher upfront cost but pays off every time a lib's source layout
changes or a new platform comes online.

**Stretch:** the smoke tests double as compilation examples for downstream
users — they document the canonical `find_package` / link invocation per lib.
