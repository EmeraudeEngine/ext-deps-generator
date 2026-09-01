---
id: validate-new-libs-windows-macos
title: Validate draco, onnxruntime and simdjson on Windows and macOS
status: open
priority: high
scope: libraries/{draco,onnxruntime,simdjson}.yaml, CMakeLists.txt
opened: 2026-08-31
tags: [new-libraries, cross-platform, release]
---

The libraries added for the next archive are configured and **validated on Linux only**
(Debian 13, gcc 14.2, glibc 2.41): Release and Debug both build, and `DependenciesTest`
passes. Nothing has run on Windows or macOS yet. (libigl was part of this batch but has
since been removed from the archive.) Points to watch, per library:

## draco
Lowest risk. On MSVC the target is `draco` (`draco.lib`) instead of `draco_static`, which the
test project already handles. Watch the CRT validation output.

## simdjson
Low risk on the build itself (a single translation unit, seconds), but two things to confirm:
- MSVC picks up the same four x86 kernels (fallback, westmere, haswell, icelake) — check the
  configure log, and that the archive still dispatches at runtime rather than being pinned to
  the build machine's CPU.
- `SIMDJSON_THREADS_ENABLED=1` is defined on the consumer side of every platform build; the
  macro changes `document_stream`'s layout, so a missing define is silent.

## onnxruntime
The real unknown, and the longest build (~10 min on 28 Linux cores; expect much more on a
laptop).
- **Windows**: the artifact is `onnxruntime.dll` + an import lib. CRT validation only sees the
  import lib and will report SKIP (no CRT directives) — that is expected, not a miss. The DLL
  follows `CMAKE_MSVC_RUNTIME_LIBRARY`, which the builder passes globally, so the MT and MD
  packages must both be produced and checked (`dumpbin /dependents onnxruntime.dll` should
  show `vcruntime140.dll` for MD and nothing for MT).
- **macOS**: `onnxruntime_BUILD_APPLE_FRAMEWORK` stays OFF (we want a plain dylib). The
  arm64 -> x86_64 cross build is the untested case; MLAS carries per-architecture assembly, so
  this is where a cross-compile problem would surface. `onnxruntime_CROSS_COMPILING` exists
  upstream if CMake's own detection is not enough.
- Both: the configure step downloads ~1 GiB from `cmake/deps.txt`. A machine behind a proxy or
  offline will fail there, not in the build.

## Also worth one look while the packages are open

The README entries for `zlib` and `zstd` warn that upstream builds the static *and* the
shared library ("beware when linking"). On Linux that is no longer true — neither build
generates a shared target, and `output/<config>/lib` holds no `.so` but onnxruntime's — but
the install rules differ on Windows and macOS, so check there that no unexpected
`.dll`/`.dylib` rides along, and drop the warnings from the README if they are stale
everywhere.

## Done when
Each platform has produced its Release and Debug packages with the three libraries in them,
and `DependenciesTest` passes on each. Record whatever surprises appear in the library YAML
headers and in README.md (they are the durable documentation), then delete this file.
