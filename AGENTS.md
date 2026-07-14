# AGENTS.md - AI Context File

## Project Purpose
Cross-platform build system for external C/C++ dependencies. Generates static libraries for Windows (MD/MT), Linux, and macOS.

## Architecture

```
build.py                    # Main entry point (static libs from the YAML registry)
build_cef.py                # SEPARATE path: CEF from source (see § CEF below)
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
repositories/               # Git submodules (library sources) — EXCEPTION: libressl is a
                            # vendored release tarball, not a submodule (see Vendored Sources)
output/                     # Built libraries (per-config subdirs)
builds/                     # Build intermediates
CMakeLists.txt              # Test project to validate all libs link correctly
```

## Prerequisites

### All Platforms
- Python 3.10+
- CMake 3.26+ (some libraries — e.g. openal-soft — use the `$<BUILD_LOCAL_INTERFACE:...>` generator expression introduced in 3.26)
- Git (for submodules and patch system)

### Windows
- Visual Studio 2022 (MSVC v143 toolchain)
- MSYS2 (required for building libvpx — provides bash/make for its configure script)
  - Install from https://www.msys2.org/
  - Run `pacman -S make diffutils` inside MSYS2 to install required tools (libvpx's `configure` needs `diff`)
  - NASM recommended for x86_64 assembly optimizations (`pacman -S nasm` or install via Windows PATH)
  - The MSYS2 `bash.exe` and `make` must be accessible (used to run libvpx's configure/make targeting MSVC)
  - Set `MSYS2_PATH` environment variable if MSYS2 is not installed at `C:\msys64`
- Python packages: `pip install -r requirements.txt` inside the project venv (installs PyYAML, Meson, Ninja — these have no convenient system installer on Windows)

### macOS
- Xcode Command Line Tools
- Meson and Ninja (e.g., `brew install meson ninja`)
- PyYAML (e.g., `pip install PyYAML` in the project venv)

### Linux
- GCC or Clang toolchain
- CMake 3.26+. Ubuntu 22.04's system package is 3.22 and is **too old** — install a newer one either via `pip install cmake` in the project venv (matches the macOS/Windows flow) or via Kitware's APT repo at https://apt.kitware.com/
- Meson and Ninja (e.g., `apt install meson ninja-build`, or `pip install -r requirements.txt` in the project venv)
- PyYAML (e.g., `apt install python3-yaml`, or `pip install PyYAML` in the project venv)

## Key Concepts

### Build Configuration String
Unified grammar: `{os}.{arch}-{build_type}[-{os_tag}]`, where `{os_tag}` encodes
whatever else changes the ABI of the produced static libraries (so
ABI-incompatible builds never overwrite each other in the same folder):

- Linux: `{os}.{arch}-{build_type}-glibc{ver}` (e.g., `linux.x86_64-Release-glibc2.35`)
- macOS: `{os}.{arch}-{build_type}-sdk{ver}` (e.g., `macos.arm64-Release-sdk12.0`)
- Windows: `{os}.{arch}-{build_type}-{runtime}` (e.g., `windows.x86_64-Release-MD`)

The `{os}` prefix is always `linux`/`macos`/`windows` (matches `platform_name`).
Implemented in `BuildConfig.build_suffix` (`builder/config.py`).

**Linux libc tag** (`detect_libc_tag()`): reflects the **build host's** glibc,
which is the *floor* — static `.a` archives embed versioned libc symbol refs
(e.g. `memcpy@GLIBC_2.14`), and the highest one determines the oldest distro the
final binary can run on. The tag reflects this floor; it does **not** lower it.
For true "runs on every distro" compatibility, ALSO build against an old glibc
(a manylinux container or a sysroot) — the tag then records that lower floor.
Other portability factors to control at the toolchain level: `_GLIBCXX_USE_CXX11_ABI`
(libstdc++ dual ABI), a conservative CPU baseline (no `-march=native`), and
`-fPIC` (already set in `linux.py`).

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

### Path tokens in `cmake_options` values

String values inside `cmake_options` (top-level or platform-specific) are run through
a simple token substitution by `CMakeBuilder` before being passed as `-DKEY=value`:

| Token | Resolves to |
|-------|-------------|
| `${INSTALL_PREFIX}` | The install/output directory for the current build configuration (`output/<config>`) |
| `${ROOT_DIR}` | The ext-deps-generator root directory |
| `${SOURCE_DIR}` | The library's source directory (after `source_dir` resolution) |
| `${BUILD_DIR}` | The library's build intermediate directory (`builds/<config>/<lib>`) |

Use this when a library expects a path that depends on the build layout — e.g. `spirv-tools`
needs `SPIRV-Headers_SOURCE_DIR=${INSTALL_PREFIX}` so it picks up the headers from the
previously installed `spirv-headers` package without re-adding it as a CMake subdirectory.

### Windows CRT Validation
After each library build, `dumpbin /directives` validates .lib files:
- MT: only `LIBCMT`
- MTd: only `LIBCMTD`
- MD: only `MSVCRT`
- MDd: only `MSVCRTD`

Build fails immediately if wrong CRT detected.

### Post-build assertions
A library YAML can declare post-install checks that abort the build when the
artifact is structurally valid but functionally broken (e.g. OpenAL-soft
compiled with no real Linux audio backend because the matching `-dev`
packages were missing). Implemented in `Library.verify_post_build()`
(`builder/config.py`) and currently invoked from `cmake_builder.py`.

Schema:
```yaml
platforms:
  linux:
    post_build_assertions:
      - kind: require_any_define
        file: config.h                   # relative to the build dir
        defines: [HAVE_ALSA, HAVE_PULSEAUDIO, HAVE_PIPEWIRE, HAVE_JACK]
        message: |
          Remediation message printed when the assertion fails.
```

Single kind for now (`require_any_define`); extend `verify_post_build()` when
a new kind is genuinely needed. Opt-in: libraries without the section behave
as before. The check is CMake-only at the moment — wire it into the other
builders the same way if a non-CMake library ever needs it.

### Vendored Sources (exception to the submodule convention)
All library sources are git submodules, with **one deliberate exception: `repositories/libressl/`
holds the committed contents of an upstream release tarball** (owner-ruled 2026-07-04). Reason:
the `libressl/portable` git repository is not self-contained — its crypto/ssl/tls directories
hold only build files, the real sources are pulled from the OpenBSD tree by `update.sh` at
build time (build-time network access, weak reproducibility). The self-contained form of a
LibreSSL release is the tarball.

Rules for a vendored library:
- The version, source URL, and tarball SHA256 are recorded in the library's YAML header
  (`libraries/libressl.yaml`), along with the upgrade procedure.
- `check_releases.py` does NOT see vendored libraries (it enumerates `.gitmodules`) — release
  freshness must be checked manually (https://www.libressl.org/releases.html).
- Do not add further vendored deps without weighing the submodule alternative first; this is
  an exception, not a precedent.

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

### `/check-releases`
Runs `check_releases.py` to compare each submodule's pinned commit against upstream release tags. Read-only: reports which libraries have a newer stable tag, which are on a branch with a tag suggestion, and which have no tags upstream. Does not modify anything.

## CEF (separate build path — `build_cef.py`)

CEF is **deliberately NOT** in the `libraries/*.yaml` registry. The registry
handles small static libs from git submodules (cmake/autotools/meson/msys2),
ordered by a dependency graph and linked together by `DependenciesTest`. CEF is
a full Chromium checkout (~100 GB, hours) driven by `depot_tools` +
`automate-git.py` + GN, producing a *binary distribution* (shared libcef +
`libcef_dll_wrapper` static lib + resources + headers), versioned by a CEF
branch number. Putting a `cef.yaml` in `libraries/` would break the registry
(the loader would order/link it like a static lib). So it lives in its own
standalone script.

**Why build CEF ourselves** — two goals, each requiring a from-source build:
1. **H.264 / proprietary codecs**: official builds ship `proprietary_codecs=false`.
2. **No V8 sandbox**: app_system's zero-copy ArrayBuffer bridge is incompatible
   with the V8 sandbox (external backing stores must live inside the sandbox
   cage). The sandbox is default-ON upstream but still disable-able at build time
   — which requires **also** disabling pointer compression (three flags kept
   together in `BASE_GN_DEFINES`).

**Staying current**: bump `DEFAULT_CEF_BRANCH` in `build_cef.py` every 2-3 months
to the current stable CEF branch, re-run per platform, publish the archive. The
GN args never change across versions — only the branch does. This works as long
as `v8_enable_sandbox=false` survives upstream (unsupported config → guard the
zero-copy in CI after each bump).

**Linux glibc floor (why CEF has NO glibc tag, unlike the static libs)**: CEF is
built with `use_sysroot=true` (`BASE_GN_DEFINES` in `build_cef.py`), so it links
against Chromium's bundled Debian sysroot — currently **Bullseye → glibc 2.31** —
*regardless of the build host's glibc*. The produced `libcef.so` therefore runs
on any distro with glibc ≥ 2.31, exactly like the official Spotify CDN builds
(which use the same infrastructure). This is the deliberate difference from the
static libs built by `build.py`: those link against the **host** glibc, so their
output folder carries a `-glibc<ver>` tag (see § Build Configuration String),
whereas CEF's folder keeps the plain Spotify token (`linux64`, no glibc tag)
because its floor is fixed by the sysroot, not by the machine.
Caveat: the sysroot pins the floor of `libcef.so` and Chromium's own code only.
`libcef_dll_wrapper` (the static C++ lib you compile and link engine-side) and
your own code still follow the host toolchain — that is the link to watch if the
final app must run on a distro older than the build host.

```bash
python build_cef.py                     # host platform, Release, x86_64
python build_cef.py --branch 7827       # target a specific CEF branch (bump to stay current)
python build_cef.py --arch arm64 --macos-sdk 12.0
python build_cef.py --distrib minimal   # ship-ready, smaller
python build_cef.py --archive           # also zip the dist folder for publishing
python build_cef.py --dry-run           # print plan (env, GN_DEFINES, command), build nothing
python build_cef.py --force-build       # compile an already-synced tree (see note below)
python build_cef.py --clean             # remove output/*.cef.* folders (NOT the Chromium checkout)
```

- **`--force-build` (resuming an interrupted run)**: automate-git.py only builds
  when the source hashes changed or the `out/` dir is absent. If a run dies during
  the multi-hour sync (e.g. a transient `chromium.googlesource.com` fetch timeout),
  the *next* run finds the checkout complete-and-unchanged, so it **no-ops the build
  AND the distribution, yet returns success** — build_cef.py then fails with
  "no CEF binary distribution found under …/cef/binary_distrib". That is not a build
  failure: the compile simply never ran. Re-run with `--force-build` to compile the
  already-synced tree (building implies `--force-distrib` upstream). Use `--force-clean`
  only to wipe and re-fetch the whole tree from scratch.
- **Linux build target is `cefsimple`, not `cefclient`**: automate-git.py defaults
  to building the `cefclient` sample, but on Linux its sources
  (`cefclient_sources_linux` in `cef_paths2.gypi`) unconditionally `#include
  <gtk/gtk.h>`, while CEF's `BUILD.gn` sets `cef_use_gtk = !use_sysroot`. Because we
  always build with `use_sysroot=true`, the GTK include/link config is never added
  and cefclient fails with `'gtk/gtk.h' file not found`. `build_cef.py` therefore
  passes `--build-target=cefsimple` on Linux (X11-only, no GTK); libcef + the wrapper
  — all the binary distribution actually needs — are still built as dependencies.
  Override with `--build-target` if you truly need cefclient (then you must make GTK3
  resolvable, e.g. `cef_use_gtk=true` + GTK `.pc` files reachable by the sysroot
  pkg-config). Windows/macOS keep automate-git.py's `cefclient` default.
- **Cannot cross-compile** Chromium (except macOS x86_64/arm64 on Apple Silicon):
  run on a native machine per target OS.
- **Checkout location**: `--download-dir` > `$CEF_DOWNLOAD_DIR` >
  `<repo>/../cef-chromium` (the ~100 GB Chromium checkout + depot_tools +
  automate-git.py). The default is a **sibling of the repo, outside it**: this
  keeps it invisible to git (no `.gitignore` entry needed) and to IDEs that would
  otherwise try to index the giant tree (CLion), and it is naturally out of reach
  of `build.py --clean` (which only touches paths inside the repo). `build.py`
  still imports `CEF_CHECKOUT_DIRNAME` to preserve any *legacy* in-repo checkout
  under `builds/`. Point `--download-dir` at a bigger disk if needed.
- **Multi-OS checkouts on one external SSD (chosen scheme: one partition per OS)**:
  since Chromium can't be cross-compiled, each OS needs its own ~100 GB checkout.
  To avoid dedicating that space on every machine, the checkouts live on a shared
  external SSD **partitioned in three** — ext4 (Linux), APFS (macOS), NTFS
  (Windows) — one native checkout per partition, with `CEF_DOWNLOAD_DIR` (or
  `--download-dir`) pointed at the current OS's partition on each machine.
  **Do NOT try a single checkout shared by all three OSes**, even though gclient's
  `target_os = ['linux', 'mac', 'win']` can fetch all three OSes' deps (and
  automate-git.py would preserve a hand-edited `.gclient` — it only writes it when
  absent or with `--force-config`). Three things break it:
  1. *Filesystem*: no FS is natively writable by all three OSes AND checkout-safe.
     exFAT has no symlinks/exec bits (hooks and git break on Linux/macOS); NTFS is
     read-only on macOS without paid drivers; Chromium's Windows docs require NTFS
     (git packfiles > 4 GB rule out FAT). ext4/APFS are single-OS.
  2. *Host-specific toolchains overwrite each other*: hooks download host-OS
     binaries into fixed paths (e.g. clang under `src/third_party/llvm-build`,
     ~2 GB) — every OS switch re-downloads and clobbers them.
  3. *`out/` collides*: automate-git.py names the build dir `out/Release_GN_x64`
     on every OS, so object files from different OSes would mix — full rebuild per
     switch at best, poisoned artifacts at worst.
  To save re-downloading when seeding a new partition: `tar` an existing checkout's
  download dir (tar preserves symlinks/modes in transit), untar it on the new
  partition, delete `chromium/src/out/`, then run `build_cef.py` normally — git
  fetches only deltas and `runhooks` swaps in the host-OS binaries. Practical
  notes: budget ~150-200 GB per partition (checkout + build); prefer an NVMe
  USB4/Thunderbolt enclosure (the link step is I/O-heavy).
- **Output — matches the Spotify CDN exactly**: the produced distribution is
  copied into `output/` keeping its verbatim official name
  `cef_binary_<version>_<token>[_<flavor>]/` (e.g.
  `output/cef_binary_149.0.6+g…+chromium-149.0.7827.201_linux64/`). The platform
  `<token>` is the Spotify one — `linux64`, `linuxarm64`, `windows64`,
  `windowsarm64`, `macosx64`, `macosarm64`. **Why identical to Spotify**: the
  app_system consumer keeps working unchanged — only its CEF **download base URL**
  flips from the Spotify CDN to our GitHub release (a single `-DCEF_DOWNLOAD_BASE_URL=…`
  configure flag in `cmake/InstallCEF.cmake`, + a `CEF_PACKAGE_VERSION` bump); the
  archive name is the same.
  The folder is laid out like an extracted Spotify archive: `Release/` and/or
  `Debug/` subdirs (only the build type(s) built; same-branch runs **merge**, so
  a Debug run keeps an existing Release/ and vice-versa) plus the shared dirs
  (`include`, `Resources`, `libcef_dll`, `cmake`, `*.txt`). Add `--archive` to
  also produce `output/cef_binary_<version>_<token>.tar.bz2` (the Spotify archive
  format) for upload as a GitHub release asset.

## Common Issues

1. **CRT mismatch**: Library built with wrong runtime. Check YAML `runtime_MT`/`runtime_MD` options.
2. **Missing Windows system libs**: Add to CMakeLists.txt (e.g., `usp10`, `dwrite`, `rpcrt4` for harfbuzz).
3. **Static linking defines**: Add compile definitions like `LZMA_API_STATIC`, `ZMQ_STATIC`, `AL_LIBTYPE_STATIC`.
4. **Library name mismatch**: Windows .lib names differ from Unix (e.g., `libpng16_static.lib` vs `png16`).
5. **C++ ABI mismatch**: Library forces old C++ standard but headers use newer features (e.g., `std::string_view`). Use `CMAKE_CXX_STANDARD` in YAML + patch if library overrides it.
6. **macOS cross-compilation**: When building x86_64 from ARM host, ensure `CMAKE_SYSTEM_PROCESSOR` is set (handled by `macos.py`). For autotools libraries, macOS `ar` creates broken fat archives from cross-arch objects — use `libtool -static` instead (fix via patch system). Libraries with custom cross-compile handling can define `cross_compile_targets` in YAML to use `--target` instead of `--build`/`--host`.
