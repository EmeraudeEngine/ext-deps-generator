# AGENTS.md - AI Context File

## Project Purpose
Cross-platform build system for external C/C++ dependencies. Generates static libraries for Windows (MD/MT), Linux, and macOS.

## Architecture

```
build.py                    # Main entry point
builder/
  config.py                 # BuildConfig, Library, LibraryRegistry classes
  cmake_builder.py          # CMake build orchestration
  autotools_builder.py      # Autotools build orchestration (Linux/macOS)
  platforms/
    base.py                 # Abstract Platform class
    windows.py              # Windows-specific (MSVC flags, CRT validation)
    linux.py                # Linux-specific
    macos.py                # macOS-specific
libraries/*.yaml            # Library configurations
repositories/               # Git submodules (library sources)
output/                     # Built libraries (per-config subdirs)
builds/                     # Build intermediates
CMakeLists.txt              # Test project to validate all libs link correctly
```

## Key Concepts

### Build Configuration String
- Linux/macOS: `{platform}.{arch}-{build_type}` (e.g., `linux.x86_64-Release`)
- Windows: `{platform}.{arch}-{build_type}-{runtime}` (e.g., `windows.x86_64-Release-MD`)

### YAML Library Config
```yaml
name: libname
source_dir: repositories/libname      # Can be overridden per-platform
build_system: cmake                   # or autotools
languages: [c, cxx]
depends_on: [zlib, brotli]
cmake_options:
  OPTION: value
platforms:
  windows:
    source_dir: path/to/windows/cmake  # Platform-specific source
    build_system: cmake                # Platform-specific build system
    cmake_options: {}
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

## Common Issues

1. **CRT mismatch**: Library built with wrong runtime. Check YAML `runtime_MT`/`runtime_MD` options.
2. **Missing Windows system libs**: Add to CMakeLists.txt (e.g., `usp10`, `dwrite`, `rpcrt4` for harfbuzz).
3. **Static linking defines**: Add compile definitions like `LZMA_API_STATIC`, `ZMQ_STATIC`, `AL_LIBTYPE_STATIC`.
4. **Library name mismatch**: Windows .lib names differ from Unix (e.g., `libpng16_static.lib` vs `png16`).
