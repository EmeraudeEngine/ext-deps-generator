---
id: strip-build-machine-paths
title: Keep the build machine's paths out of the prebuilt archives
status: in-progress
priority: unranked
scope: builder (compile flags of every library build), next archive version
opened: 2026-09-23
tags: [release, reproducibility, cross-platform]
---

# Keep the build machine's paths out of the prebuilt archives

## Why

The static libraries of the archives bake the absolute paths of the machine that built them
(`__FILE__`, `assert()`) into every application that links them. Measured on app_system
(LycheeSlicer, 2026-09-23), once its own sources were remapped:

- Linux: `/mnt/bunker/studio/dev/ln-isle/ext-deps-generator/repositories/...` — ~85 strings in
  each executable, ~440 in `libEmeraude.so` (libressl ~200, opus, mpg123, tinyusdz, libjpeg-turbo,
  hwloc, lame, libtiff, libzmq).
- macOS: `/Users/<user>/dev/ln-isle/ext-deps-generator/repositories/...`, same libraries.
- Windows: `C:\Users\<user>\dev\ln-isle\ext-deps-generator\{repositories,builds}\...`, libzmq ~77 per
  executable, libressl/mpg123/tinyusdz/opus ~355 in `Emeraude.dll`.

Also baked in: `builds/<suffix>/cryptopp-cmake/cryptopp/*_simd.cpp` (the build directory, not the
repository), and hwloc's configured run-state directory
`output/linux.x86_64-Release-glibc2.41/var/run/hwloc/` (a real runtime lookup path).

The owner's requirement is that no shipped binary names the builder's environment. app_system
fixed its side (`cmake/StripBuildMachinePaths.cmake`, and `deploy/package.py`
`verify_no_build_machine_paths()`, which only *warns* on these archive paths until this is done).

## What remains

The builder side is done (`BuildConfig.path_remap_flags`, `AGENTS.md § Build-machine paths`) and
every configuration of the three OSes was rebuilt with it for **v018** (2026-10-10): 0 source
path (`<root>/repositories`) in any archive of any configuration — Release, and Debug outside
DWARF / CodeView — except the libvpx gaps below. Validated: GCC `-fmacro-prefix-map`, MSVC
`/d1trimfile:` on CMake and Meson (no unknown-option warning), the macOS arm64 → x86_64 cross
file.

- Bump emeraude-base to v018, then let app_system's `verify_no_build_machine_paths()` turn its
  warning on these archive paths into an error.
- libvpx on Windows: the MSYS2 builder drives libvpx's own Visual Studio projects and does not
  receive the flags (`vpxmd.lib` ~4.7k source paths in Release-MD).
- libvpx: its configure line (`--prefix=<root>/output/...`) is still compiled in; only matters if
  a consumer ever embeds libvpx.

## ⚠️ Traps

- **A raw root count over a Windows `.lib` is dominated by harmless metadata** (~7000 hits per
  configuration): every archive member is named after its object's absolute path
  (`builds\<cfg>\<lib>\<target>.dir\Release\*.obj`), and Debug objects carry the compiler command
  line (`-I<root>\…`, seen in harfbuzz) in their CodeView build info. Neither reaches a linked
  `.exe`. Scan for `<root>\repositories` / `<root>/repositories` instead — that is what
  `__FILE__` / `assert()` produce.
- libressl also compiles `OPENSSLDIR` in (`C:/Windows/libressl/ssl` on Windows) — absolute but not
  machine-specific; leave it unless the owner decides otherwise.
