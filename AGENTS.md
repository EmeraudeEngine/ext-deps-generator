# AGENTS.md - AI Context File

## Project Purpose
Cross-platform build system for external C/C++ dependencies. Generates static libraries for Windows (MD/MT), Linux, and macOS.

## Architecture

```
build.py                    # Main entry point
builder/
  config.py                 # BuildConfig, Library, LibraryRegistry classes
  cmake_builder.py          # CMake build orchestration + PatchManager
  meson_builder.py          # Meson build orchestration + cross-compilation
  msys2_builder.py          # MSYS2 build orchestration (Windows, for libvpx)
  autotools_builder.py      # Autotools build orchestration (Linux/macOS) + PatchManager
  platforms/
    base.py                 # Abstract Platform class
    windows.py              # Windows-specific (MSVC flags, CRT validation)
    linux.py                # Linux-specific
    macos.py                # macOS-specific
libraries/*.yaml            # Library configurations
patches/                    # Git patches applied before build (see Patch System)
repositories/               # Git submodules (library sources)
output/                     # Built libraries (per-config subdirs)
builds/                     # Build intermediates
CMakeLists.txt              # Test project to validate all libs link correctly
```

## Prerequisites

### All Platforms
- Python 3.10+
- CMake 3.20+
- Git (for submodules and patch system)

### Windows
- Visual Studio 2022 (MSVC v143 toolchain)
- MSYS2 (required for building libvpx — provides bash/make for its configure script)
  - Install from https://www.msys2.org/
  - Run `pacman -S make` inside MSYS2 to install make
  - NASM recommended for x86_64 assembly optimizations (`pacman -S nasm` or install via Windows PATH)
  - The MSYS2 `bash.exe` and `make` must be accessible (used to run libvpx's configure/make targeting MSVC)
  - Set `MSYS2_PATH` environment variable if MSYS2 is not installed at `C:\msys64`

### macOS
- Xcode Command Line Tools
- Ninja build system
- Meson (if building meson-based libraries like harfbuzz)

### Linux
- GCC or Clang toolchain
- Ninja build system
- Meson (if building meson-based libraries like harfbuzz)

## Key Concepts

### Build Configuration String
- Linux/macOS: `{platform}.{arch}-{build_type}` (e.g., `linux.x86_64-Release`)
- Windows: `{platform}.{arch}-{build_type}-{runtime}` (e.g., `windows.x86_64-Release-MD`)

### YAML Library Config
```yaml
name: libname
source_dir: repositories/libname      # Can be overridden per-platform
build_system: cmake                   # or autotools, meson, or msys2
languages: [c, cxx]
depends_on: [zlib, brotli]
cmake_options:
  OPTION: value
meson_options:
  feature_option: disabled     # Meson feature options: enabled/disabled/auto
  bool_option: true            # Meson boolean options: true/false
platforms:
  windows:
    source_dir: path/to/windows/cmake  # Platform-specific source
    build_system: cmake                # Platform-specific build system
    cmake_options: {}
    meson_options: {}
    extra_c_flags: "-DFOO"             # Appended to C flags
    runtime_MT:                        # MT-specific options
      OPTION: value
    runtime_MD:                        # MD-specific options
      OPTION: value
disabled_platforms: [windows]          # Skip on these platforms
```

### Windows CRT Validation
After each library build, `dumpbin /directives` validates .lib files:
- MT: only `LIBCMT`
- MTd: only `LIBCMTD`
- MD: only `MSVCRT`
- MDd: only `MSVCRTD`

Build fails immediately if wrong CRT detected.

### Patch System
Some libraries need modifications to build correctly (e.g., forced C++ standard, macOS cross-compilation fixes). Instead of forking, use the patch system.

**Prefer patches over builder changes**: when fixing a library-specific build issue, a small patch on the library's build files (CMakeLists.txt, Makefile, configure, etc.) is almost always cheaper than adding complex workarounds in the builder scripts. If the fix targets one library's build system, patch it. Reserve builder changes for generic cross-cutting concerns.

1. Create `patches/{libname}.patch` (standard git diff format)
2. The `PatchManager` automatically applies it before configure (CMake, Meson, and autotools)
3. A `.patch_applied` marker in the source dir prevents re-applying
4. Submodules stay clean (patches are applied at build time)

**Examples**:
- `patches/jsoncpp.patch`: allows overriding `CMAKE_CXX_STANDARD` (jsoncpp forces C++11, but headers expose `std::string_view` requiring C++17+).
- `patches/libvpx.patch`: replaces `ar` with `libtool -static` on macOS. macOS `ar` creates fat Mach-O archives from cross-arch objects that it cannot update, breaking cross-compilation from ARM to x86_64.

**Creating a patch**:
```bash
cd repositories/libname
# Make changes
git diff > ../../patches/libname.patch
git checkout .  # Revert changes
```

### MSYS2 Builder (Windows)
For libraries like libvpx that use their own configure/make system (not CMake, not standard autotools), the `msys2` build system runs the configure script via MSYS2 bash targeting MSVC:
- Configure uses `--target=x86_64-win64-vs17` to generate `.vcxproj` files
- `make` invokes `msbuild.exe` internally (requires Windows PATH to be preserved)
- `--enable-static-msvcrt` is passed for MT runtime builds
- Post-install flattens `lib/x64/` subdirectories to `lib/` for consistency
- CRT validation runs after install

### Meson Builder
For libraries that use Meson as their build system (e.g., harfbuzz). The builder:
- Runs `meson setup` with `--default-library=static` and `--buildtype=release|debug`
- Options from `meson_options` in YAML are passed as `-Doption=value`
- Uses Meson values directly: features use `enabled`/`disabled`/`auto`, booleans use `true`/`false`
- For macOS cross-compilation (ARM host -> x86_64 target), generates a Meson cross-file with `[host_machine]` and `[built-in options]` sections
- Runs `meson compile` and `meson install`
- Post-install validation (CRT on Windows, architecture on macOS) runs after install

## CLI Usage
```bash
python build.py                              # Build all
python build.py --runtime-lib MT             # Windows MT runtime
python build.py --build-type Debug           # Debug build
python build.py --library zlib               # Single lib + deps
python build.py --library zlib --no-deps     # Single lib only
python build.py --clean                      # Clean all builds/output
python build.py --list                       # List libraries
```

## Test Project (CMakeLists.txt)
Builds all dependencies then links a test executable. Requires:
- Windows: `-DRUNTIME_LIB=MD|MT`
- macOS: `-DMACOS_SDK=12.0`

## Claude Commands

### `/build-library <name>`
Builds a library for both macOS architectures (ARM64 + x86_64) in Release mode with `--no-deps`. Useful for quick validation after modifying a library config or patch.

## Common Issues

1. **CRT mismatch**: Library built with wrong runtime. Check YAML `runtime_MT`/`runtime_MD` options.
2. **Missing Windows system libs**: Add to CMakeLists.txt (e.g., `usp10`, `dwrite`, `rpcrt4` for harfbuzz).
3. **Static linking defines**: Add compile definitions like `LZMA_API_STATIC`, `ZMQ_STATIC`, `AL_LIBTYPE_STATIC`.
4. **Library name mismatch**: Windows .lib names differ from Unix (e.g., `libpng16_static.lib` vs `png16`).
5. **C++ ABI mismatch**: Library forces old C++ standard but headers use newer features (e.g., `std::string_view`). Use `CMAKE_CXX_STANDARD` in YAML + patch if library overrides it.
6. **macOS cross-compilation**: When building x86_64 from ARM host, ensure `CMAKE_SYSTEM_PROCESSOR` is set (handled by `macos.py`). For autotools libraries, macOS `ar` creates broken fat archives from cross-arch objects — use `libtool -static` instead (fix via patch system). Libraries with custom cross-compile handling can define `cross_compile_targets` in YAML to use `--target` instead of `--build`/`--host`.
