---
id: audit-cascade-against-build-policy
title: Audit the existing libraries against the build policy (static, C++20, no exceptions, no RTTI)
status: open
priority: medium
scope: libraries/*.yaml, AGENTS.md § Build policy
opened: 2026-08-31
tags: [build-policy, abi, archive]
---

The build policy was written on 2026-08-31 (AGENTS.md § Build policy) and applied to the four
libraries added for the next archive. **The other ~43 libraries of the cascade have never been
checked against it**, and several were configured long before the rule existed.

## Where the four new ones stand

| | static | C++20 | exceptions off | RTTI off |
|---|---|---|---|---|
| draco | yes | yes (`CMAKE_CXX_STANDARD`) | no switch upstream | no switch upstream |
| libigl | yes | yes (`CMAKE_CXX_STANDARD`) | no switch upstream | no switch upstream |
| simdjson | yes | yes (`SIMDJSON_CXX_STANDARD`) | yes (`SIMDJSON_EXCEPTIONS=OFF`) | no switch upstream |
| onnxruntime | **no — shared, documented exception** | yes (upstream forces 20) | no (needs a minimal build) | yes |

## What to check on the rest

- **Standard**: a library that sets no `CMAKE_CXX_STANDARD` inherits the *host compiler's*
  default — gnu++17 on gcc 14 today, something else on the next toolchain. That is the silent
  half of the problem: the archive's API can change with the build machine. `grep -L
  CMAKE_CXX_STANDARD libraries/*.yaml` is the starting list; the C-only libraries (zlib,
  bzip2, xz, libpng, libjpeg-turbo…) are out of scope.
- **Exceptions**: the switches that exist upstream, found by grepping the submodules'
  top-level CMakeLists — `glslang` has `ENABLE_EXCEPTIONS`, `SPIRV-Tools` has
  `ENABLE_EXCEPTIONS_ON_MSVC` (ON by default), `tinyusdz` already sets
  `TINYUSDZ_CXX_EXCEPTIONS=false`. Each one turned off needs its consumer-side macro
  documented, and a rebuild + `DependenciesTest` run to prove nothing depended on it.
- **RTTI**: expect few switches and accept that. Worth checking only where a library exposes
  polymorphic types in its headers.
- **Static**: the README entries for `zlib` and `zstd` both warn that upstream builds the
  static *and* the shared library ("beware when linking"). On Linux today nothing but
  onnxruntime lands as a `.so` in `output/<config>/lib`, so either the warnings are stale or
  the shared copies are built and not installed — worth settling, and re-checking on Windows
  and macOS where the install rules differ.

## Done when

Each library either conforms or carries, in its YAML header and its README entry, the reason
it cannot — with the upstream limitation or the measurement that settles it. Record the
findings there, then delete this file.
