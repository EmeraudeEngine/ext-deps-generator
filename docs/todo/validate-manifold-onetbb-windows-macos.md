---
id: validate-manifold-onetbb-windows-macos
title: Validate manifold and oneTBB on Windows and macOS
status: open
priority: high
scope: libraries/{manifold,onetbb}.yaml, patches/manifold.patch, CMakeLists.txt
opened: 2026-09-10
tags: [new-libraries, cross-platform, release, v016]
---

# Validate manifold and oneTBB on Windows and macOS

The two libraries added for the **v016** archive are configured and **validated on Linux
only** (Debian 13, gcc 14.2, glibc 2.41, CMake 3.31): Release and Debug both build, both
compile at `-std=c++20`, and `DependenciesTest` passes at 48/48 in each. Nothing has run on
Windows or macOS yet.

## Why they are here

`manifold` is the deliverable (robust mesh booleans / CSG); `onetbb` is in the archive only
because manifold's `MANIFOLD_PAR` backend needs it. `clipper2` was already present and now has
a second consumer. Full rationale in the two YAML headers and in README.md.

## What remains

Per platform (Windows MD + MT, macOS arm64 + x86_64), Release **and** Debug:

```bash
# Windows
python build.py --library manifold --runtime-lib MD --build-type Release
python build.py --library manifold --runtime-lib MD --build-type Debug
python build.py --library manifold --runtime-lib MT --build-type Release
python build.py --library manifold --runtime-lib MT --build-type Debug
cmake -B builds/tests -DRUNTIME_LIB=MD && cmake --build builds/tests

# macOS
python build.py --library manifold --macos-sdk 12.0 --build-type Release
python build.py --library manifold --macos-sdk 12.0 --build-type Debug
cmake -B builds/tests -DMACOS_SDK=12.0 && cmake --build builds/tests
```

`--library manifold` pulls `clipper2` and `onetbb` in as dependencies, in that order.

## ⚠️ Traps

### oneTBB, Windows

- **The archive basename carries a version AND a debug postfix**: `tbb12.lib` in Release,
  `tbb12_debug.lib` in Debug (`OUTPUT_NAME tbb${TBB_BINARY_VERSION}` is Windows-only,
  `CMAKE_DEBUG_POSTFIX _debug` is not). The test project's CMakeLists already handles the four
  combinations — confirm the produced names actually match, because a bump of
  `TBB_BINARY_VERSION` on a future version upgrade would silently break the link.
- **`/GL` must not appear.** `TBB_ENABLE_IPO` is forced OFF in the YAML precisely for MSVC; if
  the CRT validation ever reports the LTCG rejection on `tbb12.lib`, something re-enabled it.
- **`tbb.rc`**: oneTBB adds a Windows resource file to a project declared `LANGUAGES CXX`.
  Upstream CI builds this way, so it is expected to work; if CMake complains about the RC
  language, that is the cause and the fix is a patch adding `RC` to `project()`.
- CRT: TBB honours `CMAKE_MSVC_RUNTIME_LIBRARY` through policy CMP0091, which it sets NEW
  itself, so the builder's global flag should be enough. Watch the directive scan for all four
  packages.

### oneTBB, macOS

- The x86_64-from-arm64 cross build is the untested case. `src/tbb/CMakeLists.txt` gates its
  x86 code (the RTM mutexes) on `CMAKE_SYSTEM_PROCESSOR` **and** `CMAKE_OSX_ARCHITECTURES`,
  both of which `builder/platforms/macos.py` sets — so this should be fine, but it is the one
  place where an arch mix-up would land. `validate_architecture()` will catch a wrong-arch
  archive.
- oneTBB defines `CMAKE_CXX_OSX_DEPLOYMENT_TARGET_FLAG` itself when it is not already set;
  check the deployment target the builder passes actually reaches the compile line.

### manifold, both platforms

- **The patch is load-bearing.** `patches/manifold.patch` is what makes `CMAKE_CXX_STANDARD=20`
  work at all. It carries `# target-commit: 0edd9d54…`, so a submodule bump will fail the build
  rather than silently compiling at C++17 — that is the intent. Verify the standard actually
  reached the compiler:
  `grep -o '\-std=[a-z+0-9]*' builds/<config>/manifold/build.ninja | sort -u`
  (on Windows the generator is Visual Studio, so read it from the `.vcxproj`
  `LanguageStandard` instead, or from `compile_commands.json`).
- **`MANIFOLD_DOWNLOADS=OFF` turns a `find_package` miss into a configure-time FATAL_ERROR.**
  If manifold fails to configure with "TBB not found, and dependency downloading disabled" or
  the same for Clipper2, the cause is that `find_package` did not resolve out of
  `output/<config>` — most likely the config-package directory casing
  (`lib/cmake/clipper2` for a package named `Clipper2`) behaving differently on a
  case-insensitive filesystem, or the build order not putting onetbb/clipper2 first. Do **not**
  "fix" it by allowing downloads: that would link a second Clipper2 and a foreign TBB into the
  archive.
- Confirm in the manifold build's `CMakeCache.txt` that `TBB_DIR` and `Clipper2_DIR` point
  inside `output/<config>/lib/cmake/`, as they do on Linux.
- MSVC: manifold adds `/bigobj` to its own flags because some translation units exceed the
  section limit. If a compile fails with C1128 anyway, that flag did not survive.

## Also worth one look while the packages are open

`clipper2` installs `libClipper2Z.a` / `Clipper2Z.lib` alongside `libClipper2.a` even though
`CLIPPER2_USINGZ` is false — the install rule is unconditional upstream. Pre-existing, not
introduced here, and harmless (nothing links it), but if the package size matters it is a
candidate for a patch.

## Done when

Each platform has produced its Release and Debug packages containing `manifold` and `onetbb`,
`DependenciesTest` passes on each, and the manifold/oneTBB lines of its output show the
expected versions (3.5.3 / 2023.1.0) with a plausible default concurrency. Record whatever
surprises appear in the two library YAML headers and in README.md — they are the durable
documentation — then delete this file.
