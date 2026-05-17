# TODO

## v011 — Archive hardening

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
